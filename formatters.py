from __future__ import annotations

from functools import lru_cache
from html import escape
from typing import TYPE_CHECKING

import bleach
from markupsafe import Markup, escape as markup_escape

if TYPE_CHECKING:
    from models import ScoredPost


_MEDIA_VIDEO_TYPES = {"video", "gifv", "audio"}
_ALLOWED_CONTENT_TAGS = frozenset(
    bleach.sanitizer.ALLOWED_TAGS.union({"p", "span", "br", "a", "img", "blockquote", "code", "pre"})
)
_ALLOWED_CONTENT_ATTRS = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "a": ["href", "class", "rel", "target"],
    "img": ["src", "alt", "title", "width", "height"],
    "span": ["class"],
}
_ALLOWED_PROTOCOLS = tuple(sorted(set(bleach.sanitizer.ALLOWED_PROTOCOLS).union({"http", "https"})))


@lru_cache(maxsize=1024)
def _render_display_name(display_name: str, emoji_data: tuple[tuple[str, str], ...]) -> Markup:
    rendered = markup_escape(display_name)
    for shortcode, url in emoji_data:
        placeholder = markup_escape(f":{shortcode}:")
        if placeholder not in rendered:
            continue
        replacement = Markup(
            f'<img alt="{markup_escape(shortcode)}" src="{markup_escape(url)}">'
        )
        rendered = rendered.replace(placeholder, replacement)
    return Markup(rendered)


def _serialize_media_attachment(media: dict) -> dict | None:
    media_type = media.get("type", "image")
    url = media.get("url") or media.get("remote_url") or media.get("preview_url")
    if not url:
        return None
    preview_url = media.get("preview_url") or url
    description = media.get("description") or ""

    safe_description_attr = escape(description, quote=True)
    safe_description_text = escape(description)

    return {
        "type": media_type,
        "is_video": media_type in _MEDIA_VIDEO_TYPES,
        "autoplay": media_type == "gifv",
        "original_url": escape(url, quote=True),
        "preview_url": escape(preview_url, quote=True),
        "description_attr": safe_description_attr,
        "description_text": safe_description_text,
    }


def _format_displayname(display_name: str, emojis: list[dict]) -> Markup:
    emoji_key = tuple((emoji["shortcode"], emoji["url"]) for emoji in emojis)
    return _render_display_name(display_name, emoji_key)


def _sanitize_html(value: str) -> str:
    return bleach.clean(
        value,
        tags=_ALLOWED_CONTENT_TAGS,
        attributes=_ALLOWED_CONTENT_ATTRS,
        protocols=_ALLOWED_PROTOCOLS,
        strip=True,
    )


def format_post(
    post: ScoredPost,
    mastodon_base_url: str,
) -> dict:
    account_avatar = escape(post.data['account']['avatar'], quote=True)
    account_url = escape(post.data['account']['url'], quote=True)
    display_name = _format_displayname(
        post.data['account']['display_name'],
        post.data['account']['emojis']
    )
    username = escape(post.data['account']['username'])
    content = _sanitize_html(post.data['content'])
    media_attachments = [
        serialized for media in post.data['media_attachments']
        if (serialized := _serialize_media_attachment(media)) is not None
    ]
    created_at = post.data['created_at'].isoformat()
    home_url = escape(post.get_home_url(mastodon_base_url), quote=True)
    original_url = escape(post.data["url"], quote=True)

    return dict(
        account_avatar=account_avatar,
        account_url=account_url,
        display_name=display_name,
        raw_display_name=post.data['account']['display_name'],
        username=username,
        content=content,
        media=media_attachments,
        created_at=created_at,
        home_url=home_url,
        original_url=original_url,
        replies_count=post.data['replies_count'],
        reblogs_count=post.data['reblogs_count'],
        favourites_count=post.data['favourites_count'],
    )


def format_posts(
    posts: list[ScoredPost],
    mastodon_base_url: str,
) -> list[dict]:
    return [format_post(post, mastodon_base_url) for post in posts]
