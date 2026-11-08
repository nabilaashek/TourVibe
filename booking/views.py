import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from packandgo.utils import safe_next
from userprofile.decorators import admin_only
from userprofile.models import is_admin

from .forms import AddToCartForm, CheckoutForm
from .invoice import make_invoice
from .models import Cart, CartItem, Order, TourPackage
from .services import change_status, place_order


# ---- Packages ----

def package_list(request):
    packages = TourPackage.objects.filter(is_active=True, start_date__gt=timezone.localdate())
    q = request.GET.get('q', '').strip()
    if q:
        packages = packages.filter(Q(title__icontains=q) | Q(summary__icontains=q)
                                   | Q(destinations__name__icontains=q)).distinct()
    page = Paginator(packages.prefetch_related('destinations'), 9).get_page(request.GET.get('page'))
    return render(request, 'booking/package_list.html', {'page_obj': page, 'q': q})


def package_detail(request, slug):
    package = get_object_or_404(TourPackage.objects.prefetch_related('destinations__category'), slug=slug,
                                is_active=True)
    return render(request, 'booking/package_detail.html', {'package': package, 'form': AddToCartForm()})


# ---- Cart (the main idea of the first Pack-Go) ----

def get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@login_required
@require_POST
def add_to_cart(request, slug):
    package = get_object_or_404(TourPackage, slug=slug, is_active=True)
    form = AddToCartForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Choose between 1 and 20 travelers.')
        return redirect(package.get_absolute_url())
    if not package.can_book:
        messages.error(request, 'This tour cannot be booked any more.')
        return redirect(package.get_absolute_url())
    travelers = form.cleaned_data['travelers']
    if travelers > package.seats_left:
        messages.error(request, f'Only {package.seats_left} seat(s) left.')
        return redirect(package.get_absolute_url())
    item, created = CartItem.objects.get_or_create(cart=get_cart(request.user), package=package,
                                                   defaults={'travelers': travelers})
    if not created:
        item.travelers = travelers
        item.save()
    messages.success(request, f'{package.title} is in your cart.')
    return redirect('cart')


@login_required
def cart_view(request):
    cart = get_cart(request.user)
    items = cart.items.select_related('package')
    return render(request, 'booking/cart.html', {'cart': cart, 'items': items, 'total': cart.total})


@login_required
@require_POST
def update_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    form = AddToCartForm(request.POST)
    if form.is_valid():
        item.travelers = form.cleaned_data['travelers']
        item.save()
        messages.success(request, 'Cart updated.')
    else:
        messages.error(request, 'Travelers must be a number from 1 to 20.')
    return redirect('cart')


@login_required
@require_POST
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    messages.success(request, 'Removed from cart.')
    return redirect('cart')


@login_required
def checkout(request):
    cart = get_cart(request.user)
    items = list(cart.items.select_related('package'))
    if not items:
        messages.info(request, 'Your cart is empty.')
        return redirect('package_list')
    profile = request.user.profile
    form = CheckoutForm(request.POST or None,
                        initial={'contact_name': profile.display_name, 'contact_phone': profile.phone_number})
    if request.method == 'POST' and form.is_valid():
        try:
            order = place_order(request.user, [(i.package, i.travelers) for i in items],
                                form.cleaned_data['contact_name'], form.cleaned_data['contact_phone'],
                                form.cleaned_data['note'])
        except ValidationError as error:
            for text in error.messages:
                form.add_error(None, text)
        else:
            cart.items.all().delete()
            messages.success(request, f'Order {order.reference} placed! We will confirm it soon.')
            return redirect(order.get_absolute_url())
    return render(request, 'booking/checkout.html', {'form': form, 'items': items, 'total': cart.total})


# ---- Orders ----

def get_order_for(request, reference):
    order = get_object_or_404(Order, reference=reference)
    if order.user != request.user and not is_admin(request.user):
        raise Http404
    return order


@login_required
def order_history(request):
    orders = request.user.orders.prefetch_related('items__package')
    return render(request, 'booking/order_history.html', {'orders': orders})


@login_required
def order_detail(request, reference):
    order = get_order_for(request, reference)
    return render(request, 'booking/order_detail.html', {'order': order, 'items': order.items.select_related('package')})


@login_required
@require_POST
def cancel_order(request, reference):
    order = get_order_for(request, reference)
    if order.can_cancel:
        change_status(order, Order.CANCELLED)
        messages.success(request, f'Order {order.reference} was cancelled.')
    else:
        messages.error(request, 'This order can no longer be cancelled.')
    return redirect(order.get_absolute_url())


@login_required
def invoice(request, reference):
    order = get_order_for(request, reference)
    response = HttpResponse(make_invoice(order), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice-{order.reference}.pdf"'
    return response


# ---- Admin ----

@admin_only
def manage_orders(request):
    orders = Order.objects.select_related('user').prefetch_related('items__package')
    status = request.GET.get('status', '')
    q = request.GET.get('q', '').strip()
    if status in dict(Order.STATUS_CHOICES):
        orders = orders.filter(status=status)
    if q:
        orders = orders.filter(Q(reference__icontains=q) | Q(contact_name__icontains=q) | Q(user__username__icontains=q))
    page = Paginator(orders, 15).get_page(request.GET.get('page'))
    return render(request, 'booking/manage_orders.html', {
        'page_obj': page, 'status': status, 'q': q, 'statuses': Order.STATUS_CHOICES,
    })


@admin_only
@require_POST
def set_status(request, reference):
    order = get_object_or_404(Order, reference=reference)
    try:
        change_status(order, request.POST.get('status'))
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
    else:
        messages.success(request, f'{order.reference} is now {order.get_status_display()}.')
    return redirect(safe_next(request, reverse('manage_orders')))


@admin_only
def export_orders(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="orders-{timezone.localdate()}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Reference', 'Customer', 'Phone', 'Tours', 'Travelers', 'Total (BDT)', 'Status', 'Date'])
    for order in Order.objects.prefetch_related('items__package'):
        items = list(order.items.all())
        writer.writerow([order.reference, order.contact_name, order.contact_phone,
                         '; '.join(i.package.title for i in items), sum(i.travelers for i in items),
                         order.total_price, order.get_status_display(),
                         timezone.localtime(order.created_at).strftime('%Y-%m-%d %H:%M')])
    return response
