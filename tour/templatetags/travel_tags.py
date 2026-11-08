from django import template

register = template.Library()


@register.filter
def taka(value):
    """Format a number as Bangladeshi Taka, e.g. 12500 -> ৳12,500."""
    try:
        return f'৳{int(round(float(value))):,}'
    except (TypeError, ValueError):
        return '—'


@register.inclusion_tag('partials/stars.html')
def stars(value, size='sm'):
    """Render 0-5 stars (supports halves)."""
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        value = 0
    full = int(value)
    half = 1 if value - full >= 0.5 else 0
    return {'full': range(full), 'half': half, 'empty': range(5 - full - half), 'size': size}


@register.simple_tag(takes_context=True)
def url_with(context, **kwargs):
    """Return the current query string with some parameters replaced."""
    query = context['request'].GET.copy()
    for key, value in kwargs.items():
        if value in (None, ''):
            query.pop(key, None)
        else:
            query[key] = value
    return '?' + query.urlencode() if query else '?'
