from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone

from booking.models import Order, OrderItem, TourPackage
from tour.models import Category, Division, Review, TourDestination
from userprofile.models import is_admin


def home(request):
    today = timezone.localdate()
    places = TourDestination.objects.active().select_related('division', 'category')
    return render(request, 'core/home.html', {
        'featured': places.filter(is_featured=True).with_rating()[:6],
        'in_season': [p for p in places if p.good_in_month(today.month)][:5],
        'divisions': Division.objects.annotate(total=Count('destinations', filter=Q(destinations__is_active=True))),
        'categories': Category.objects.annotate(total=Count('destinations', filter=Q(destinations__is_active=True))),
        'packages': TourPackage.objects.filter(is_active=True, start_date__gt=today).prefetch_related('destinations')[:3],
        'counts': {'places': places.count(), 'divisions': Division.objects.count(), 'reviews': Review.objects.count()},
    })


def about(request):
    return render(request, 'core/about.html')


@login_required
def dashboard(request):
    if is_admin(request.user):
        return admin_dashboard(request)
    user = request.user
    today = timezone.localdate()
    orders = user.orders.prefetch_related('items__package')
    upcoming = (OrderItem.objects.filter(order__user=user, order__status__in=Order.ACTIVE,
                                         package__start_date__gte=today)
                .select_related('order', 'package').order_by('package__start_date'))
    return render(request, 'core/dashboard.html', {
        'upcoming': upcoming[:5],
        'order_count': orders.exclude(status=Order.CANCELLED).count(),
        'spent': orders.filter(status=Order.CONFIRMED).aggregate(t=Sum('total_price'))['t'] or 0,
        'wishlist_items': user.wishlist.select_related('tour')[:5],
        'wishlist_total': user.wishlist.count(),
        'plans': user.trip_plans.all()[:4],
        'review_total': user.reviews.count(),
    })


def admin_dashboard(request):
    today = timezone.localdate()
    orders = Order.objects.all()
    since = (today.replace(day=1) - timedelta(days=150)).replace(day=1)
    monthly = (orders.filter(status=Order.CONFIRMED, created_at__date__gte=since)
               .annotate(month=TruncMonth('created_at')).values('month')
               .annotate(total=Sum('total_price')).order_by('month'))
    by_status = {code: orders.filter(status=code).count() for code, _ in Order.STATUS_CHOICES}
    divisions = Division.objects.annotate(total=Count('destinations')).order_by('name')
    popular = (TourPackage.objects.annotate(sold=Sum('order_items__travelers', filter=Q(order_items__order__status=Order.CONFIRMED)))
               .filter(sold__gt=0).order_by('-sold')[:5])

    return render(request, 'core/admin_dashboard.html', {
        'stats': {
            'revenue': orders.filter(status=Order.CONFIRMED).aggregate(t=Sum('total_price'))['t'] or 0,
            'orders': orders.exclude(status=Order.CANCELLED).count(),
            'pending': by_status[Order.PENDING],
            'travelers': User.objects.filter(is_staff=False).count(),
            'places': TourDestination.objects.active().count(),
            'tours': TourPackage.objects.filter(is_active=True, start_date__gt=today).count(),
        },
        'recent': orders.select_related('user')[:8],
        'popular': popular,
        'chart': {
            'revenue_labels': [m['month'].strftime('%b %Y') for m in monthly],
            'revenue_values': [m['total'] for m in monthly],
            'status_labels': [label for _, label in Order.STATUS_CHOICES],
            'status_values': [by_status[code] for code, _ in Order.STATUS_CHOICES],
            'division_labels': [d.name for d in divisions],
            'division_values': [d.total for d in divisions],
        },
    })


def page_not_found(request, exception):
    return render(request, '404.html', status=404)
