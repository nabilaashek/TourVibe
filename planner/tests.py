from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from packandgo.testing import make_place, make_user
from tour.models import TourDestination

from . import engine
from .models import TripPlan


class EngineTests(TestCase):
    def setUp(self):
        self.north = make_place('North Place', lat=24.9, lng=91.9, price=2000)
        self.near = make_place('Near Place', lat=23.46, lng=91.18, price=1000, entry_fee=50)
        self.south = make_place('South Place', lat=21.43, lng=92.0, price=3000)

    def test_share_days(self):
        self.assertEqual(engine.share_days(7, 3), [3, 2, 2])

    def test_route_starts_with_nearest_place(self):
        route, km = engine.best_route([self.south, self.north, self.near])
        self.assertEqual(route[0], self.near)
        self.assertGreater(km, 0)

    def test_cost_parts_add_up(self):
        r = engine.estimate_trip([self.near], 2, 2)
        b = r['breakdown']
        self.assertAlmostEqual(r['total'], sum(b.values()), delta=3)
        self.assertEqual(b['entry_fees'], 100)
        self.assertEqual(r['per_person'], round(r['total'] / 2))

    def test_budget_levels(self):
        totals = [engine.estimate_trip([self.south], 3, 2, level)['total'] for level in ['BUDGET', 'STANDARD', 'PREMIUM']]
        self.assertEqual(totals, sorted(totals))

    def test_car_and_flight(self):
        self.assertEqual(engine.transport_cost(100, 2, 5, 'CAR'), engine.transport_cost(100, 2, 4, 'CAR') * 2)
        self.assertEqual(engine.transport_cost(10, 2, 1, 'AIR'), engine.MIN_AIR_FARE * 2)

    def test_bad_input(self):
        for args in [([], 2, 1), ([self.south, self.north], 1, 1), ([self.south], 2, 0), ([self.south], 'x', 1)]:
            with self.assertRaises(engine.PlannerError):
                engine.estimate_trip(*args)

    def test_recommendation_order(self):
        make_place('Winter Spot', months='12,1', price=1500)
        make_place('Summer Spot', months='6,7', price=1500)
        make_place('Pricey Winter', months='12,1', price=5000)
        places = TourDestination.objects.filter(name__in=['Winter Spot', 'Summer Spot', 'Pricey Winter'])
        names = [r['place'].name for r in engine.recommend(places, 12, 2000)]
        self.assertEqual(names, ['Winter Spot', 'Pricey Winter', 'Summer Spot'])

    def test_distance_limit(self):
        results = engine.recommend(TourDestination.objects.all(), 1, max_km=150)
        self.assertEqual([r['place'] for r in results], [self.near])


class PlannerPageTests(TestCase):
    def test_estimate_and_save(self):
        place = make_place()
        user = make_user()
        self.client.force_login(user)
        data = {'places': [place.slug], 'days': 2, 'travelers': 2, 'budget': 'STANDARD', 'transport': 'BUS',
                'start_date': (timezone.localdate() + timedelta(days=3)).isoformat()}
        self.assertIsNotNone(self.client.post(reverse('planner'), {**data, 'estimate': '1'}).context['result'])
        response = self.client.post(reverse('planner'), {**data, 'save': '1', 'title': 'Weekend'})
        self.assertRedirects(response, reverse('my_plans'))
        self.assertEqual(TripPlan.objects.get(user=user).title, 'Weekend')

    def test_past_date_rejected(self):
        place = make_place()
        response = self.client.post(reverse('planner'), {'places': [place.slug], 'days': 2, 'travelers': 1,
                                                         'budget': 'BUDGET', 'transport': 'BUS',
                                                         'start_date': '2000-01-01'})
        self.assertIsNone(response.context['result'])

    def test_where_to_go_page(self):
        make_place(months='12')
        self.assertEqual(len(self.client.get(reverse('where_to_go'), {'month': 12}).context['results']), 1)
