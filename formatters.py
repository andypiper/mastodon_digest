from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import nh3
from markupsafe import Markup, escape as markup_escape

if TYPE_CHECKING:
    from models import ScoredPost


_MEDIA_VIDEO_TYPES = {"video", "gifv", "audio"}
_ALLOWED_SCHEMES = frozenset({"http", "https"})


def _safe_url(url: str | None) -> str:
    if not url:
        return ""
    try:
        scheme = urlparse(url).scheme.lower()
    except Exception:
        return ""
    return url if scheme in _ALLOWED_SCHEMES else ""


@lru_cache(maxsize=1024)
def _render_display_name(
    display_name: str, emoji_data: tuple[tuple[str, str], ...]
) -> Markup:
    rendered = markup_escape(display_name)
    for shortcode, url in emoji_data:
        safe_url = _safe_url(url)
        if not safe_url:
            continue
        placeholder = markup_escape(f":{shortcode}:")
        if placeholder not in rendered:
            continue
        replacement = Markup(
            f'<img alt="{markup_escape(shortcode)}" src="{markup_escape(safe_url)}">'
        )
        rendered = rendered.replace(placeholder, replacement)
    return Markup(rendered)


def _serialize_media_attachment(media: dict) -> dict | None:
    media_type = media.get("type", "image")
    url = _safe_url(
        media.get("url") or media.get("remote_url") or media.get("preview_url")
    )
    if not url:
        return None
    preview_url = _safe_url(media.get("preview_url")) or url
    description = media.get("description") or ""
    return {
        "type": media_type,
        "is_video": media_type in _MEDIA_VIDEO_TYPES,
        "autoplay": media_type == "gifv",
        "original_url": url,
        "preview_url": preview_url,
        "description": description,
    }


def _format_displayname(display_name: str, emojis: list[dict]) -> Markup:
    emoji_key = tuple((emoji["shortcode"], emoji["url"]) for emoji in emojis)
    return _render_display_name(display_name, emoji_key)


def _sanitize_html(value: str) -> Markup:
    return Markup(
        nh3.clean(
            value,
            tags={
                "p",
                "span",
                "br",
                "a",
                "img",
                "blockquote",
                "code",
                "pre",
                "b",
                "strong",
                "i",
                "em",
                "ul",
                "ol",
                "li",
            },
            attributes={
                "a": {"href", "class", "target"},
                "img": {"src", "alt", "title", "width", "height"},
                "span": {"class"},
            },
            link_rel="noopener noreferrer",
        )
    )


def _serialize_poll(poll: dict) -> dict | None:
    if not poll:
        return None
    votes_count = poll.get("votes_count") or 0
    options = []
    for opt in poll.get("options", []):
        opt_votes = opt.get("votes_count")
        percent = (
            round(opt_votes / votes_count * 100)
            if votes_count > 0 and opt_votes is not None
            else None
        )
        options.append(
            {
                "title": opt.get("title", ""),
                "votes_count": opt_votes,
                "percent": percent,
            }
        )
    expires_at = poll.get("expires_at")
    return {
        "options": options,
        "votes_count": votes_count,
        "expired": poll.get("expired", False),
        "multiple": poll.get("multiple", False),
        "expires_at": (
            expires_at.isoformat()
            if hasattr(expires_at, "isoformat")
            else (expires_at or "")
        ),
    }


def _serialize_quote(quote: dict) -> dict | None:
    if not quote or not isinstance(quote, dict):
        return None
    account = quote.get("account", {})
    display_name = account.get("display_name") or account.get("username", "")
    username = account.get("acct") or account.get("username", "")
    return {
        "account_url": _safe_url(account.get("url") or ""),
        "display_name": display_name,
        "username": username,
        "content": _sanitize_html(quote.get("content") or ""),
        "original_url": _safe_url(quote.get("url") or quote.get("uri") or ""),
    }


def format_post(
    post: ScoredPost,
    mastodon_base_url: str,
) -> dict:
    account = post.data["account"]
    display_name = _format_displayname(account["display_name"], account["emojis"])
    content = _sanitize_html(post.data["content"])
    media_attachments = [
        serialized
        for media in post.data["media_attachments"]
        if (serialized := _serialize_media_attachment(media)) is not None
    ]
    created_at = post.data["created_at"].isoformat()
    home_url = _safe_url(post.get_home_url(mastodon_base_url))
    original_url = _safe_url(post.data["url"])

    raw_quote = post.data.get("quote")
    if not raw_quote and post.data.get("quote_url"):
        raw_quote = {"url": post.data["quote_url"]}

    return dict(
        account_avatar=_safe_url(account["avatar"]),
        account_url=_safe_url(account["url"]),
        display_name=display_name,
        raw_display_name=account["display_name"],
        username=account["username"],
        content=content,
        media=media_attachments,
        created_at=created_at,
        home_url=home_url,
        original_url=original_url,
        replies_count=post.data["replies_count"],
        reblogs_count=post.data["reblogs_count"],
        favourites_count=post.data["favourites_count"],
        poll=_serialize_poll(post.data.get("poll")),
        quote=_serialize_quote(raw_quote),
    )


def format_posts(
    posts: list[ScoredPost],
    mastodon_base_url: str,
) -> list[dict]:
    return [format_post(post, mastodon_base_url) for post in posts]
