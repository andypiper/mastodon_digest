from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from models import ScoredPost


def _create_enhanced_mock_post(
    post_id: str,
    username: str,
    display_name: str,
    content: str,
    reblogs: int = 5,
    favourites: int = 10,
    replies: int = 3,
    followers: int = 100,
    user_note: str = "",
    noindex: bool = False,
    media_type: str | None = None,
    hours_ago: int = 2,
) -> dict[str, Any]:
    created_at = datetime.now(timezone.utc) - timedelta(hours=hours_ago)

    media_attachments: list[dict[str, Any]] = []
    if media_type == "image":
        media_attachments = [{
            "type": "image",
            "url": f"https://picsum.photos/400/300?random={post_id}",
            "preview_url": f"https://picsum.photos/200/150?random={post_id}",
            "description": "Sample image description for accessibility"
        }]
    elif media_type == "video":
        media_attachments = [{
            "type": "video",
            "url": "https://sample-videos.com/video123/mp4/480/big_buck_bunny_480p_5mb.mp4",
            "preview_url": "https://i.imgur.com/8Km9tLL.jpg",
            "description": "Sample video content"
        }]

    return {
        "id": post_id,
        "url": f"https://mastodon.social/@{username}/{post_id}",
        "content": content,
        "created_at": created_at,
        "reblogs_count": reblogs,
        "favourites_count": favourites,
        "replies_count": replies,
        "reblogged": False,
        "favourited": False,
        "bookmarked": False,
        "visibility": "public",
        "reblog": None,
        "media_attachments": media_attachments,
        "account": {
            "id": f"user_{username}",
            "username": username,
            "acct": username,
            "display_name": display_name,
            "url": f"https://mastodon.social/@{username}",
            "avatar": f"https://i.pravatar.cc/48?u={username}",
            "followers_count": followers,
            "emojis": [],
            "note": user_note,
            "noindex": noindex
        }
    }


def generate_demo_posts() -> tuple[list[ScoredPost], list[ScoredPost]]:
    """Return representative mock posts/boosts for demo rendering."""
    mock_posts_data = [
        _create_enhanced_mock_post(
            "1001", "alice_dev", "Alice Cooper 👩‍💻",
            "<p>Just deployed a new feature using <a href='#' class='hashtag'>#Python</a> and <a href='#' class='hashtag'>#FastAPI</a>! 🚀</p>",
            reblogs=25, favourites=45, replies=12, followers=250,
            user_note="<p>Senior Software Engineer at TechCorp.</p>",
            media_type="image",
            hours_ago=1
        ),
        _create_enhanced_mock_post(
            "1002", "bob_photo", "Bob Wilson 📸",
            "<p>Captured this amazing sunset today. Nature never ceases to amaze me! 🌅</p>",
            reblogs=18, favourites=32, replies=8, followers=450,
            user_note="<p>Professional landscape photographer.</p>",
            media_type="image",
            hours_ago=3
        ),
        _create_enhanced_mock_post(
            "1003", "charlie_code", "Charlie Brown 🎯",
            "<p>Working on an interesting #Rust project implementing a distributed cache.</p>",
            reblogs=15, favourites=35, replies=18, followers=180,
            hours_ago=4
        ),
        _create_enhanced_mock_post(
            "1004", "diana_remote", "Diana Prince ☕",
            "<p>Coffee shop coding session in progress ☕</p>",
            reblogs=22, favourites=41, replies=15, followers=320,
            hours_ago=2
        ),
        _create_enhanced_mock_post(
            "1005", "eve_design", "Eve Smith 🎨",
            "<p>Just finished designing a new accessibility-focused component system! ♿</p>",
            reblogs=30, favourites=55, replies=22, followers=600,
            media_type="video",
            hours_ago=5
        ),
        _create_enhanced_mock_post(
            "1006", "frank_ai", "Frank Miller 🤖",
            "<p>Mind-blowing conference talk about the intersection of AI and ethics! 🧠</p>",
            reblogs=45, favourites=78, replies=31, followers=890,
            hours_ago=6
        ),
    ]

    mock_boosts_data = [
        _create_enhanced_mock_post(
            "2001", "grace_data", "Grace Hopper 📊",
            "<p>\"Legacy code is not just old code. It's code that continues to provide value.\"</p>",
            reblogs=67, favourites=123, replies=28, followers=1200,
            hours_ago=8
        ),
        _create_enhanced_mock_post(
            "2002", "henry_open", "Henry Ford 🔓",
            "<p>Amazing open source project alert! 🎉</p>",
            reblogs=41, favourites=89, replies=19, followers=540,
            hours_ago=7
        ),
        _create_enhanced_mock_post(
            "2003", "iris_security", "Iris Chen 🔐",
            "<p>PSA: Please update your dependencies! 🚨</p>",
            reblogs=156, favourites=89, replies=45, followers=2100,
            hours_ago=1
        ),
    ]

    posts = [ScoredPost(data) for data in mock_posts_data]
    boosts = [ScoredPost(data) for data in mock_boosts_data]
    return posts, boosts
