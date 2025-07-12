from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import ScoredPost


def format_post(post: ScoredPost, mastodon_base_url: str) -> dict[str, str | int]:
    
    def format_media(media) -> str:
        # Use pattern matching for media type handling (Python 3.10+)
        match media.type:
            case 'image':
                return f'<div class="media"><img src={media["url"]} alt="{media["description"] or ""}"></img></div>'
            case 'video':
                return f'<div class="media"><video src={media["url"]} controls width="100%"></video></div>'
            case 'gifv':
                return f'<div class="media"><video src={media["url"]} autoplay loop muted playsinline width="100%"></video></div>'
            case _:
                return ""

    def format_displayname(display_name: str, emojis: list[dict]) -> str:
        for emoji in emojis:
            display_name = display_name.replace(f':{emoji["shortcode"]}:', f'<img alt={emoji["shortcode"]} src="{emoji["url"]}">')
        return display_name

    account_avatar = post.data['account']['avatar']
    account_url = post.data['account']['url']
    display_name = format_displayname(
        post.data['account']['display_name'],
        post.data['account']['emojis']
    )
    username = post.data['account']['username']
    content = post.data['content']
    media = "\n".join([format_media(media) for media in post.data['media_attachments']])
    # created_at = post.data['created_at'].strftime('%B %d, %Y at %H:%M')
    created_at = post.data['created_at'].isoformat()
    home_link = f'<a href="{post.get_home_url(mastodon_base_url)}" target="_blank" rel="noopener">home</a>'
    original_link = f'<a href="{post.data["url"]}" target="_blank" rel="noopener">original</a>'
    replies_count = post.data['replies_count']
    reblogs_count = post.data['reblogs_count']
    favourites_count = post.data['favourites_count']
    
    return dict(
        account_avatar=account_avatar,
        account_url=account_url,
        display_name=display_name,
        username=username,
        content=content,
        media=media,
        created_at=created_at,
        home_link=home_link,
        original_link=original_link,
        replies_count=replies_count,
        reblogs_count=reblogs_count,
        favourites_count=favourites_count
    )
    
def format_posts(posts: list[ScoredPost], mastodon_base_url: str) -> list[dict[str, str | int]]:
    return [format_post(post, mastodon_base_url) for post in posts]
