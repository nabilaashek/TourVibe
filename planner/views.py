from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from tour.models import TourDestination

from .engine import PlannerError, estimate_trip, recommend
from .forms import PlannerForm, RecommendForm
from .models import TripPlan


def trip_planner(request):
    start = {'start_date': timezone.localdate() + timedelta(days=7)}
    if request.GET.get('place'):
        start['places'] = [request.GET['place']]
    form = PlannerForm(request.POST or None, initial=start)
    result = None

    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        try:
            result = estimate_trip(list(data['places']), data['days'], data['travelers'], data['budget'],
                                   data['transport'])
        except PlannerError as error:
            form.add_error(None, str(error))
        else:
            if 'save' in request.POST:
                if not request.user.is_authenticated:
                    messages.info(request, 'Please log in to save your plan.')
                    return redirect('login')
                plan = TripPlan.objects.create(
                    user=request.user, title=data['title'] or f'Trip to {result["route"][0]["name"]}',
                    start_date=data['start_date'], days=data['days'], travelers=data['travelers'],
                    budget=data['budget'], transport=data['transport'], estimated_total=result['total'],
                    details=result)
                plan.places.set(data['places'])
                messages.success(request, f'Plan "{plan.title}" saved.')
                return redirect('my_plans')

    chart = None
    if result:
        b = result['breakdown']
        chart = {'labels': ['Transport', 'Hotel', 'Food', 'Entry fees', 'Extra'],
                 'values': [b['transport'], b['hotel'], b['food'], b['entry_fees'], b['extra']]}
    return render(request, 'planner/planner.html', {'form': form, 'result': result, 'chart': chart})


def where_to_go(request):
    form = RecommendForm(request.GET or None, initial={'month': timezone.localdate().month})
    results = None
    if form.is_bound and form.is_valid():
        data = form.cleaned_data
        results = recommend(TourDestination.objects.active(), int(data['month']), data['daily_budget'],
                            [c.pk for c in data['categories']], data['max_km'])
    return render(request, 'planner/recommend.html', {'form': form, 'results': results})


@login_required
def my_plans(request):
    return render(request, 'planner/my_plans.html', {'plans': request.user.trip_plans.prefetch_related('places')})


@login_required
@require_POST
def delete_plan(request, pk):
    get_object_or_404(TripPlan, pk=pk, user=request.user).delete()
    messages.success(request, 'Plan deleted.')
    return redirect('my_plans')
