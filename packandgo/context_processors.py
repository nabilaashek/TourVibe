from django.utils import timezone

from userprofile.models import is_admin


def navbar_info(request):
    info = {'year': timezone.localdate().year, 'wishlist_ids': set(), 'cart_count': 0,
            'user_is_admin': is_admin(request.user)}
    if request.user.is_authenticated:
        info['wishlist_ids'] = set(request.user.wishlist.values_list('tour_id', flat=True))
        cart = getattr(request.user, 'cart', None)
        if cart:
            info['cart_count'] = cart.items.count()
    return info
