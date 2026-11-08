from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from booking.models import TourPackage
from packandgo.testing import make_admin, make_package, make_place, make_user

from .models import Review, TourDestination, Wishlist, distance_km


class PlaceModelTests(TestCase):
    def test_unique_slug(self):
        self.assertEqual(make_place('Blue Lake').slug, 'blue-lake')
        self.assertEqual(make_place('Blue  Lake!').slug, 'blue-lake-2')

    def test_months(self):
        place = make_place(months='11, 12,1')
        self.assertEqual(place.month_list, [11, 12, 1])
        self.assertEqual(place.month_names, 'Nov, Dec, Jan')
        self.assertTrue(place.good_in_month(12))
        self.assertFalse(place.good_in_month(6))

    def test_bad_months_rejected(self):
        place = make_place()
        for bad in ['13', 'abc', '']:
            place.best_months = bad
            with self.assertRaises(ValidationError):
                place.full_clean()

    def test_location_must_be_in_bangladesh(self):
        place = make_place()
        place.latitude = 40
        with self.assertRaises(ValidationError):
            place.full_clean()

    def test_distance(self):
        # Dhaka to Cox's Bazar is about 290-300 km in a straight line
        self.assertAlmostEqual(distance_km(23.7261, 90.4125, 21.4272, 92.0058), 300, delta=30)

    def test_rating(self):
        place = make_place()
        Review.objects.create(tour=place, user=make_user('a'), rating=5, title='t', comment='c')
        Review.objects.create(tour=place, user=make_user('b'), rating=4, title='t', comment='c')
        self.assertEqual(place.rating(), {'avg': 4.5, 'total': 2})


class ListPageTests(TestCase):
    def setUp(self):
        make_place('Sunny Beach', division='Chattogram', category='Beach', months='12,1', price=3000)
        make_place('Old Fort', division='Dhaka', category='Heritage & History', months='6,7', price=1500)
        self.hidden = make_place('Secret Place', is_active=False)

    def names(self, response):
        return [p.name for p in response.context['page_obj']]

    def test_hidden_places_not_shown(self):
        self.assertNotIn('Secret Place', self.names(self.client.get(reverse('tour_list'))))
        self.assertEqual(self.client.get(self.hidden.get_absolute_url()).status_code, 404)

    def test_filters(self):
        url = reverse('tour_list')
        self.assertEqual(self.names(self.client.get(url, {'q': 'fort'})), ['Old Fort'])
        self.assertEqual(self.names(self.client.get(url, {'division': 'chattogram'})), ['Sunny Beach'])
        self.assertEqual(self.names(self.client.get(url, {'month': '7'})), ['Old Fort'])
        self.assertEqual(self.names(self.client.get(url, {'max_price': '2000'})), ['Old Fort'])
        self.assertEqual(self.names(self.client.get(url, {'sort': 'expensive'})), ['Sunny Beach', 'Old Fort'])


class AdminCrudTests(TestCase):
    """Create / edit / delete pages from the first Pack-Go, now admin-only."""

    def setUp(self):
        self.place = make_place()

    def test_travelers_cannot_manage_places(self):
        self.client.force_login(make_user())
        self.client.post(reverse('delete_tour', args=[self.place.slug]))
        self.assertTrue(TourDestination.objects.filter(pk=self.place.pk).exists())
        self.assertEqual(self.client.get(reverse('create_tour')).status_code, 302)

    def test_visitors_cannot_manage_places(self):
        self.client.post(reverse('delete_tour', args=[self.place.slug]))
        self.assertTrue(TourDestination.objects.filter(pk=self.place.pk).exists())

    def test_admin_can_edit_and_delete(self):
        self.client.force_login(make_admin())
        data = {'name': 'Renamed Beach', 'division': self.place.division_id, 'district': 'Cox', 'category': self.place.category_id,
                'short_description': 'x', 'description': 'y', 'best_months': '1,2', 'price_per_day': 2000,
                'latitude': '21.5', 'longitude': '92.0', 'is_active': 'on'}
        self.client.post(reverse('update_tour', args=[self.place.slug]), data)
        self.place.refresh_from_db()
        self.assertEqual(self.place.name, 'Renamed Beach')
        self.client.post(reverse('delete_tour', args=[self.place.slug]))
        self.assertFalse(TourDestination.objects.filter(pk=self.place.pk).exists())

    def test_place_used_by_a_tour_is_hidden_not_deleted(self):
        make_package(places=[self.place])
        self.client.force_login(make_admin())
        self.client.post(reverse('delete_tour', args=[self.place.slug]))
        self.place.refresh_from_db()
        self.assertFalse(self.place.is_active)
        self.assertEqual(TourPackage.objects.count(), 1)


class ReviewAndWishlistTests(TestCase):
    def setUp(self):
        self.place = make_place()
        self.user = make_user()
        self.url = reverse('save_review', args=[self.place.slug])

    def test_one_review_per_user(self):
        self.client.force_login(self.user)
        self.client.post(self.url, {'rating': 3, 'title': 'Ok', 'comment': 'Fine'})
        self.client.post(self.url, {'rating': 5, 'title': 'Great', 'comment': 'Better now'})
        self.assertEqual(Review.objects.get().rating, 5)

    def test_bad_reviews_rejected(self):
        self.client.force_login(self.user)
        self.client.post(self.url, {'rating': 9, 'title': 'x', 'comment': 'x'})
        self.client.post(self.url, {'rating': 4, 'title': 'x', 'comment': 'x', 'visited_on': '2999-01-01'})
        self.assertEqual(Review.objects.count(), 0)

    def test_only_owner_or_admin_deletes_review(self):
        review = Review.objects.create(tour=self.place, user=self.user, rating=4, title='t', comment='c')
        url = reverse('delete_review', args=[review.pk])
        self.client.force_login(make_user('other'))
        self.client.post(url)
        self.assertTrue(Review.objects.filter(pk=review.pk).exists())
        self.client.force_login(make_admin())
        self.client.post(url)
        self.assertFalse(Review.objects.filter(pk=review.pk).exists())

    def test_wishlist_toggle(self):
        self.client.force_login(self.user)
        url = reverse('toggle_wishlist', args=[self.place.slug])
        self.assertEqual(self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest').json(), {'saved': True, 'count': 1})
        self.assertEqual(self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest').json(), {'saved': False, 'count': 0})
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {'next': 'https://evil.example.com/'}).url, self.place.get_absolute_url())
        self.assertEqual(Wishlist.objects.count(), 1)
