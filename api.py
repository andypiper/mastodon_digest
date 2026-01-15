from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from mastodon.errors import MastodonAPIError, MastodonNotFoundError

from models import ScoredPost

if TYPE_CHECKING:
    from mastodon import Mastodon


def _should_filter_user(user_acct: str, user_bio: str, has_noindex: bool, mastodon_acct: str) -> bool:
    """
    Returns True if the user should be filtered out (excluded from digest).
    
    Optimized for short-circuit evaluation - fastest checks first.
    """
    if user_acct == mastodon_acct:
        return True  # Filter out own posts
    
    if has_noindex:
        return True  # Filter out users with noindex API flag
    
    # Only perform string operations if necessary
    user_bio_lower = user_bio.lower()
    if "#noindex" in user_bio_lower or "#nobot" in user_bio_lower:
        return True
    
    return False


TIMELINE_SOURCES = {
    "home": {
        "method": "timeline",
        "filters_context": "home",
        "kwargs": {},
    },
    "local": {
        "method": "timeline_public",
        "filters_context": "public",
        "kwargs": {"local": True},
    },
    "federated": {
        "method": "timeline_public",
        "filters_context": "public",
        "kwargs": {"local": False},
    },
}


def fetch_posts_and_boosts(
    hours: int,
    mastodon_client: Mastodon,
    *,
    use_async_fetch: bool = False,
    timeline_type: str = "home",
) -> tuple[list[ScoredPost], list[ScoredPost]]:
    """
    Fetches posts from the home timeline that the account hasn't interacted with,
    applying enhanced filtering to respect user privacy preferences.

    Filters out:
    - Posts the user has already interacted with (reblogged, favourited, bookmarked)
    - The user's own posts
    - Posts from accounts with API-level noindex flag set
    - Posts from accounts with #noindex in their bio
    - Posts from accounts with #nobot in their bio
    """

    TIMELINE_LIMIT = 1000

    # Get authenticated user info from API
    try:
        mastodon_acct = mastodon_client.me()['acct'].strip().lower()
        print(f"Authenticated as: @{mastodon_acct}")
    except Exception as e:
        print(f"Error getting current user: {e}")
        return [], []

    # First, try to get filters; prefer v2 to avoid deprecated endpoint warnings
    filters = None
    filters_version = None
    try:
        filters = mastodon_client.filters_v2()
        filters_version = "v2"
    except MastodonNotFoundError:
        try:
            filters = mastodon_client.filters()
            filters_version = "v1"
        except MastodonAPIError as error:
            print(f"Warning: unable to load filters (v1): {error}")
            filters = None
    except MastodonAPIError as error:
        print(f"Warning: unable to load filters (v2): {error}")
        filters = None

    # Set our start query
    start = datetime.now(timezone.utc) - timedelta(hours=hours)

    posts = []
    boosts = []
    seen_post_urls = set()
    total_posts_seen = 0

    source = TIMELINE_SOURCES.get(timeline_type, TIMELINE_SOURCES["home"])
    filters_context = source["filters_context"]
    timeline_method = getattr(mastodon_client, source["method"])
    base_timeline_kwargs = {"limit": 40, "min_id": start, **source["kwargs"]}

    def handle_page(response_page) -> None:
        nonlocal total_posts_seen

        if filters_version == "v1" and filters:
            filtered_response = mastodon_client.filters_apply(response_page, filters, filters_context)
        else:
            filtered_response = response_page

        for post in filtered_response:
            if total_posts_seen >= TIMELINE_LIMIT:
                break

            if post.get("filtered"):
                continue
            if post["visibility"] != "public":
                continue

            total_posts_seen += 1

            boost = False
            if post["reblog"] is not None:
                post = post["reblog"]
                boost = True

            scored_post = ScoredPost(post)

            if scored_post.url not in seen_post_urls:
                if (
                    scored_post.info["reblogged"]
                    or scored_post.info["favourited"]
                    or scored_post.info["bookmarked"]
                ):
                    continue

                user_acct = scored_post.info["account"]["acct"].strip().lower()
                user_bio = scored_post.info["account"]["note"]
                has_noindex = scored_post.info["account"].get("noindex", False)

                if not _should_filter_user(user_acct, user_bio, has_noindex, mastodon_acct):
                    if boost:
                        boosts.append(scored_post)
                    else:
                        posts.append(scored_post)
                    seen_post_urls.add(scored_post.url)

    async def async_fetch_loop() -> None:
        nonlocal total_posts_seen

        response = await asyncio.to_thread(timeline_method, **base_timeline_kwargs)
        while response and total_posts_seen < TIMELINE_LIMIT:
            next_task = None
            if total_posts_seen < TIMELINE_LIMIT:
                next_task = asyncio.create_task(
                    asyncio.to_thread(mastodon_client.fetch_previous, response)
                )

            handle_page(response)

            if total_posts_seen >= TIMELINE_LIMIT:
                if next_task:
                    next_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await next_task
                break

            if next_task:
                with suppress(asyncio.CancelledError):
                    response = await next_task
            else:
                response = None

    if use_async_fetch:
        asyncio.run(async_fetch_loop())
    else:
        response = timeline_method(**base_timeline_kwargs)
        while response and total_posts_seen < TIMELINE_LIMIT:
            handle_page(response)
            if total_posts_seen >= TIMELINE_LIMIT:
                break
            response = mastodon_client.fetch_previous(response)

    return posts, boosts
