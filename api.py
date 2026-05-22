from __future__ import annotations

import asyncio
import time
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import requests
from mastodon.errors import MastodonAPIError, MastodonNetworkError, MastodonNotFoundError

from models import ScoredPost

if TYPE_CHECKING:
    from mastodon import Mastodon


def _retry_mastodon_call(
    func,
    *args,
    retries: int = 3,
    base_delay: float = 2.0,
    **kwargs,
):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return func(*args, **kwargs)
        except (
            MastodonNetworkError,
            requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectionError,
        ) as error:
            last_error = error
            if attempt == retries:
                break
            delay = base_delay * attempt
            print(
                f"Warning: Mastodon request failed ({attempt}/{retries}): {error}. "
                f"Retrying in {delay:.1f}s..."
            )
            time.sleep(delay)
    raise last_error


def _should_filter_user(
    user_acct: str, user_bio: str, has_noindex: bool, mastodon_acct: str
) -> bool:
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
    languages: set[str] | None = None,
    exclude_polls: bool = False,
    require_media: bool = False,
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
        mastodon_acct = _retry_mastodon_call(mastodon_client.me)["acct"].strip().lower()
        print(f"Authenticated as: @{mastodon_acct}")
    except (
        MastodonAPIError,
        MastodonNetworkError,
        requests.exceptions.RequestException,
    ) as e:
        print(f"Error getting current user: {e}")
        return [], []

    # First, try to get filters; prefer v2 to avoid deprecated endpoint warnings
    filters = None
    filters_version = None
    try:
        filters = _retry_mastodon_call(mastodon_client.filters_v2)
        filters_version = "v2"
    except MastodonNotFoundError:
        try:
            filters = _retry_mastodon_call(mastodon_client.filters)
            filters_version = "v1"
        except (
            MastodonAPIError,
            MastodonNetworkError,
            requests.exceptions.RequestException,
        ) as error:
            print(f"Warning: unable to load filters (v1): {error}")
            filters = None
    except (
        MastodonAPIError,
        MastodonNetworkError,
        requests.exceptions.RequestException,
    ) as error:
        print(f"Warning: unable to load filters (v2): {error}")
        filters = None

    # Set our start query
    start = datetime.now(timezone.utc) - timedelta(hours=hours)

    posts = []
    boosts = []
    seen_post_urls = set()
    total_posts_seen = 0
    window_exhausted = False

    source = TIMELINE_SOURCES.get(timeline_type, TIMELINE_SOURCES["home"])
    filters_context = source["filters_context"]
    timeline_method = getattr(mastodon_client, source["method"])
    base_timeline_kwargs = {"limit": 80, "min_id": start, **source["kwargs"]}

    def handle_page(response_page) -> None:
        nonlocal total_posts_seen, window_exhausted

        if filters_version == "v1" and filters:
            filtered_response = mastodon_client.filters_apply(
                response_page, filters, filters_context
            )
        else:
            filtered_response = response_page

        for timeline_status in filtered_response:
            if total_posts_seen >= TIMELINE_LIMIT:
                break

            created = timeline_status.get("created_at")
            if created is not None and hasattr(created, "tzinfo") and created < start:
                window_exhausted = True
                return

            if timeline_status.get("filtered"):
                continue
            if timeline_status["visibility"] != "public":
                continue

            post = timeline_status
            boost = False
            if timeline_status.get("reblog") is not None:
                post = timeline_status["reblog"]
                boost = True

            if languages:
                post_language = (post.get("language") or "").lower()
                if post_language not in languages:
                    continue
            if exclude_polls and post.get("poll") is not None:
                continue
            if require_media and not post.get("media_attachments"):
                continue

            total_posts_seen += 1

            scored_post = ScoredPost(post)

            if scored_post.url not in seen_post_urls:
                if (
                    scored_post.info["reblogged"]
                    or scored_post.info["favourited"]
                    or scored_post.info["bookmarked"]
                ):
                    continue

                user_acct = scored_post.info["account"]["acct"].strip().lower()
                user_bio = scored_post.info["account"].get("note") or ""
                has_noindex = scored_post.info["account"].get("noindex", False)

                if not _should_filter_user(
                    user_acct, user_bio, has_noindex, mastodon_acct
                ):
                    if boost:
                        boosts.append(scored_post)
                    else:
                        posts.append(scored_post)
                    seen_post_urls.add(scored_post.url)

    async def async_fetch_loop() -> None:
        nonlocal total_posts_seen, window_exhausted

        try:
            response = await asyncio.to_thread(
                _retry_mastodon_call, timeline_method, **base_timeline_kwargs
            )
        except (
            MastodonAPIError,
            MastodonNetworkError,
            requests.exceptions.RequestException,
        ) as error:
            print(f"Warning: unable to fetch timeline: {error}")
            return

        while response and total_posts_seen < TIMELINE_LIMIT and not window_exhausted:
            next_task = None
            if total_posts_seen < TIMELINE_LIMIT and not window_exhausted:
                next_task = asyncio.create_task(
                    asyncio.to_thread(
                        _retry_mastodon_call, mastodon_client.fetch_previous, response
                    )
                )

            handle_page(response)

            if total_posts_seen >= TIMELINE_LIMIT or window_exhausted:
                if next_task:
                    next_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await next_task
                break

            if next_task:
                try:
                    with suppress(asyncio.CancelledError):
                        response = await next_task
                except (
                    MastodonAPIError,
                    MastodonNetworkError,
                    requests.exceptions.RequestException,
                ) as error:
                    print(f"Warning: unable to fetch next timeline page: {error}")
                    break
            else:
                response = None

    if use_async_fetch:
        asyncio.run(async_fetch_loop())
    else:
        try:
            response = _retry_mastodon_call(timeline_method, **base_timeline_kwargs)
        except (
            MastodonAPIError,
            MastodonNetworkError,
            requests.exceptions.RequestException,
        ) as error:
            print(f"Warning: unable to fetch timeline: {error}")
            return posts, boosts

        while response and total_posts_seen < TIMELINE_LIMIT and not window_exhausted:
            handle_page(response)
            if total_posts_seen >= TIMELINE_LIMIT or window_exhausted:
                break
            try:
                response = _retry_mastodon_call(mastodon_client.fetch_previous, response)
            except (
                MastodonAPIError,
                MastodonNetworkError,
                requests.exceptions.RequestException,
            ) as error:
                print(f"Warning: unable to fetch next timeline page: {error}")
                break

    return posts, boosts
