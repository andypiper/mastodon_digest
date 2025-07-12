from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from models import ScoredPost

if TYPE_CHECKING:
    from mastodon import Mastodon


def fetch_posts_and_boosts(
    hours: int, mastodon_client: Mastodon
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

    # First, get our filters
    filters = mastodon_client.filters()

    # Set our start query
    start = datetime.now(timezone.utc) - timedelta(hours=hours)

    posts = []
    boosts = []
    seen_post_urls = set()
    total_posts_seen = 0

    # Iterate over our home timeline until we run out of posts or we hit the limit
    response = mastodon_client.timeline(min_id=start)
    while response and total_posts_seen < TIMELINE_LIMIT:

        # Apply our server-side filters
        if filters:
            filtered_response = mastodon_client.filters_apply(response, filters, "home")
        else:
            filtered_response = response

        for post in filtered_response:
            if post["visibility"] != "public":
                continue

            total_posts_seen += 1

            boost = False
            if post["reblog"] is not None:
                post = post["reblog"]  # look at the boosted post
                boost = True

            scored_post = ScoredPost(post)  # wrap the post data as a ScoredPost

            if scored_post.url not in seen_post_urls:
                # Enhanced filtering with both API and bio hashtag checking
                user_bio = scored_post.info["account"]["note"].lower()
                user_acct = scored_post.info["account"]["acct"].strip().lower()

                # Check noindex API attribute (v4.0.0+)
                has_noindex = scored_post.info["account"].get("noindex", False)

                if (
                    not scored_post.info["reblogged"]
                    and not scored_post.info["favourited"]
                    and not scored_post.info["bookmarked"]
                    and user_acct != mastodon_acct
                    and not has_noindex
                    and "#noindex" not in user_bio
                    and "#nobot" not in user_bio
                ):
                    # Append to either the boosts list or the posts lists
                    if boost:
                        boosts.append(scored_post)
                    else:
                        posts.append(scored_post)
                    seen_post_urls.add(scored_post.url)

        response = mastodon_client.fetch_previous(
            response
        )  # fetch the previous (because of reverse chron) page of results

    return posts, boosts
