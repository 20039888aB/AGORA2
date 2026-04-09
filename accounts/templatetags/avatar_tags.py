from django import template
import time

register = template.Library()


@register.filter
def avatar_url(user, request=None):
    """
    Return the user's avatar URL with a cache-busting ?v= timestamp.
    Falls back to an empty string (templates handle the fallback <img>).
    Usage: {{ user|avatar_url }}
    """
    if not user:
        return ''
    try:
        if user.avatar and user.avatar.name:
            ts = int(user.updated_at.timestamp()) if hasattr(user, 'updated_at') and user.updated_at else int(time.time())
            return f'{user.avatar.url}?v={ts}'
    except (ValueError, AttributeError):
        pass
    return ''


@register.simple_tag
def avatar_src(user, default='/static/images/default-avatar.svg'):
    """
    Return a ready-to-use src value: avatar URL (cache-busted) or default.
    Usage: {% avatar_src user %} or {% avatar_src user '/path/to/fallback.svg' %}
    """
    url = avatar_url(user)
    return url if url else default
