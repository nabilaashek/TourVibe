"""Order rules shared by the website (cart checkout) and the REST API."""
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Order, OrderItem, TourPackage


def check_seats(lines, skip_order=None):
    """lines = [(package, travelers), ...]. Raises ValidationError if any tour cannot take them."""
    problems = []
    for package, travelers in lines:
        if not package.is_active or package.has_started:
            problems.append(f'"{package.title}" is no longer available.')
            continue
        free = package.total_seats - package.seats_taken(skip_order=skip_order)
        if travelers > free:
            problems.append(f'Only {max(free, 0)} seat(s) left for "{package.title}".')
    if problems:
        raise ValidationError(problems)


@transaction.atomic
def place_order(user, lines, contact_name, contact_phone, note=''):
    """Create one order with several tour packages. All or nothing."""
    if not lines:
        raise ValidationError('Your cart is empty.')
    # Lock the package rows so two people cannot take the same last seats at the same time
    ids = [package.pk for package, _ in lines]
    locked = {p.pk: p for p in TourPackage.objects.select_for_update().filter(pk__in=ids)}
    lines = [(locked[package.pk], travelers) for package, travelers in lines]
    check_seats(lines)

    order = Order.objects.create(user=user, contact_name=contact_name, contact_phone=contact_phone, note=note)
    total = 0
    for package, travelers in lines:
        OrderItem.objects.create(order=order, package=package, travelers=travelers,
                                 unit_price=package.price_per_person)
        total += package.price_per_person * travelers
    order.total_price = total
    order.save(update_fields=['total_price'])
    return order


@transaction.atomic
def change_status(order, new_status):
    if new_status not in dict(Order.STATUS_CHOICES):
        raise ValidationError('Unknown status.')
    # A cancelled order takes seats again only if they are still free
    if order.status == Order.CANCELLED and new_status in Order.ACTIVE:
        lines = [(item.package, item.travelers) for item in order.items.select_related('package')]
        check_seats(lines, skip_order=order)
    order.status = new_status
    order.save(update_fields=['status', 'updated_at'])
    return order
