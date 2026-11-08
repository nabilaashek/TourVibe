from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from packandgo.utils import safe_next
from userprofile.decorators import admin_only
from userprofile.models import is_admin

from .forms import ReviewForm, SearchForm, TourDestinationForm, TourImageForm
from .models import Review, TourDestination, Wishlist

SORTING = {
    'name': ['name'],
    'rating': [F('avg_rating').desc(nulls_last=True), 'name'],
    'cheap': ['price_per_day', 'name'],
    'expensive': ['-price_per_day', 'name'],
    'popular': ['-review_count', 'name'],
}


def search_destinations(params):
    """Used by the tour list page and the REST API, so both filter the same way."""
    form = SearchForm(params or None)
    tours = TourDestination.objects.active().select_related('division', 'category').with_rating()
    sort = 'name'
    if form.is_valid():
        data = form.cleaned_data
        if data['q']:
            q = data['q']
            tours = tours.filter(Q(name__icontains=q) | Q(district__icontains=q) | Q(short_description__icontains=q)
                                 | Q(division__name__icontains=q) | Q(category__name__icontains=q))
        if data['division']:
            tours = tours.filter(division=data['division'])
        if data['category']:
            tours = tours.filter(category=data['category'])
        if data['max_price']:
            tours = tours.filter(price_per_day__lte=data['max_price'])
        if data['month']:
            month = int(data['month'])
            ids = [t.pk for t in tours if t.good_in_month(month)]
            tours = tours.filter(pk__in=ids)
        sort = data['sort'] or 'name'
    return form, tours.order_by(*SORTING[sort])


def tour_list(request):
    form, tours = search_destinations(request.GET)
    page = Paginator(tours, 9).get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)
    return render(request, 'tour/tour_list.html', {'form': form, 'page_obj': page, 'querystring': params.urlencode()})


def tour_detail(request, slug):
    tour = get_object_or_404(TourDestination.objects.select_related('division', 'category'), slug=slug)
    if not tour.is_active and not is_admin(request.user):
        return render(request, '404.html', status=404)

    my_review = None
    if request.user.is_authenticated:
        my_review = tour.reviews.filter(user=request.user).first()

    nearby = sorted(TourDestination.objects.active().exclude(pk=tour.pk).select_related('category'),
                    key=lambda t: t.km_from(tour.latitude, tour.longitude))[:3]
    for place in nearby:
        place.km_away = round(place.km_from(tour.latitude, tour.longitude))

    return render(request, 'tour/tour_detail.html', {
        'tour': tour,
        'rating': tour.rating(),
        'reviews': tour.reviews.select_related('user__profile')[:10],
        'review_form': ReviewForm(instance=my_review),
        'my_review': my_review,
        'photo_form': TourImageForm(),
        'packages': tour.packages.filter(is_active=True, start_date__gt=timezone.localdate()),
        'nearby': nearby,
        'this_month': timezone.localdate().month,
    })


# ---- Admin: create, edit, delete destinations (as in the first Pack-Go) ----

@admin_only
def create_tour(request):
    form = TourDestinationForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        tour = form.save()
        messages.success(request, f'{tour.name} was added.')
        return redirect(tour.get_absolute_url())
    return render(request, 'tour/tour_form.html', {'form': form, 'title': 'Add a destination'})


@admin_only
def update_tour(request, slug):
    tour = get_object_or_404(TourDestination, slug=slug)
    form = TourDestinationForm(request.POST or None, request.FILES or None, instance=tour)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Destination updated.')
        return redirect(tour.get_absolute_url())
    return render(request, 'tour/tour_form.html', {'form': form, 'title': f'Edit {tour.name}', 'tour': tour})


@admin_only
def delete_tour(request, slug):
    tour = get_object_or_404(TourDestination, slug=slug)
    if request.method == 'POST':
        if tour.packages.exists():
            # Keep booking history safe: hide the place instead of deleting it
            tour.is_active = False
            tour.save(update_fields=['is_active'])
            messages.info(request, f'{tour.name} is used in tour packages, so it was hidden instead of deleted.')
        else:
            tour.delete()
            messages.success(request, f'{tour.name} was deleted.')
        return redirect('tour_list')
    return render(request, 'tour/delete_tour.html', {'tour': tour})


@admin_only
@require_POST
def add_photo(request, slug):
    tour = get_object_or_404(TourDestination, slug=slug)
    form = TourImageForm(request.POST, request.FILES)
    if form.is_valid():
        photo = form.save(commit=False)
        photo.tour = tour
        photo.save()
        messages.success(request, 'Photo added to the gallery.')
    else:
        for errors in form.errors.values():
            messages.error(request, errors[0])
    return redirect(f'{tour.get_absolute_url()}#gallery')


# ---- Reviews and wishlist ----

@login_required
@require_POST
def save_review(request, slug):
    tour = get_object_or_404(TourDestination.objects.active(), slug=slug)
    old = Review.objects.filter(tour=tour, user=request.user).first()
    form = ReviewForm(request.POST, instance=old)
    if form.is_valid():
        review = form.save(commit=False)
        review.tour = tour
        review.user = request.user
        review.save()
        messages.success(request, 'Review updated.' if old else 'Thank you for your review!')
    else:
        for errors in form.errors.values():
            messages.error(request, errors[0])
    return redirect(f'{tour.get_absolute_url()}#reviews')


@login_required
@require_POST
def delete_review(request, pk):
    review = get_object_or_404(Review, pk=pk)
    if review.user == request.user or is_admin(request.user):
        review.delete()
        messages.success(request, 'Review deleted.')
    else:
        messages.error(request, 'You can only delete your own review.')
    return redirect(f'{review.tour.get_absolute_url()}#reviews')


@login_required
@require_POST
def toggle_wishlist(request, slug):
    tour = get_object_or_404(TourDestination.objects.active(), slug=slug)
    item, created = Wishlist.objects.get_or_create(user=request.user, tour=tour)
    if not created:
        item.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'saved': created, 'count': request.user.wishlist.count()})
    messages.success(request, f'{tour.name} {"saved to" if created else "removed from"} your wishlist.')
    return redirect(safe_next(request, tour.get_absolute_url()))


@login_required
def wishlist(request):
    items = request.user.wishlist.select_related('tour__division', 'tour__category')
    return render(request, 'tour/wishlist.html', {'items': items})
