from django.urls import reverse
from rest_framework.test import APITestCase

from packandgo.testing import make_admin, make_package, make_place, make_user
from tour.models import Category, Division, Review, TourDestination


class DestinationApiTests(APITestCase):
    def setUp(self):
        self.place = make_place('Api Beach', months='12,1')
        make_place('Hidden', is_active=False)

    def test_list_and_filter(self):
        data = self.client.get(reverse('api-destinations-list')).data
        self.assertEqual([p['name'] for p in data['results']], ['Api Beach'])
        self.assertEqual(self.client.get(reverse('api-destinations-list'), {'month': 6}).data['count'], 0)

    def test_traveler_cannot_create(self):
        self.client.force_authenticate(make_user())
        self.assertEqual(self.client.post(reverse('api-destinations-list'), {'name': 'X'}).status_code, 403)

    def test_admin_creates_with_validation(self):
        self.client.force_authenticate(make_admin())
        body = {'name': 'New Hill', 'division': Division.objects.first().slug, 'category': Category.objects.first().slug,
                'district': 'Bandarban', 'short_description': 'Hill', 'description': 'Nice', 'best_months': '13',
                'price_per_day': 2000, 'latitude': '22.0', 'longitude': '92.3'}
        self.assertEqual(self.client.post(reverse('api-destinations-list'), body).status_code, 400)
        body['best_months'] = '11, 12'
        self.assertEqual(self.client.post(reverse('api-destinations-list'), body).status_code, 201)
        self.assertEqual(TourDestination.objects.get(name='New Hill').best_months, '11,12')


class ReviewApiTests(APITestCase):
    def test_no_double_review_and_no_editing_others(self):
        place = make_place()
        self.client.force_authenticate(make_user('a'))
        body = {'tour': place.slug, 'rating': 5, 'title': 'Great', 'comment': 'Loved it'}
        self.assertEqual(self.client.post(reverse('api-reviews-list'), body).status_code, 201)
        self.assertEqual(self.client.post(reverse('api-reviews-list'), body).status_code, 400)
        review = Review.objects.get()
        self.client.force_authenticate(make_user('b'))
        self.assertEqual(self.client.patch(reverse('api-reviews-detail', args=[review.pk]), {'rating': 1}).status_code, 403)


class OrderApiTests(APITestCase):
    def setUp(self):
        self.tour = make_package(seats=4, price=5000)
        self.alice, self.bob = make_user('alice'), make_user('bob')

    def order(self, user, travelers=2):
        self.client.force_authenticate(user)
        return self.client.post(reverse('api-orders-list'), {
            'items': [{'package': self.tour.slug, 'travelers': travelers}],
            'contact_name': 'Test', 'contact_phone': '01712345678'}, format='json')

    def test_create(self):
        response = self.order(self.alice)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['total_price'], 10000)

    def test_seat_limit(self):
        self.order(self.alice, 3)
        self.assertEqual(self.order(self.bob, 2).status_code, 400)

    def test_privacy(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(reverse('api-orders-list')).status_code, 403)
        ref = self.order(self.bob, 1).data['reference']
        self.order(self.alice, 1)
        self.assertEqual(self.client.get(reverse('api-orders-list')).data['count'], 1)
        self.assertEqual(self.client.get(reverse('api-orders-detail', args=[ref])).status_code, 404)

    def test_status_only_by_admin(self):
        ref = self.order(self.alice).data['reference']
        url = reverse('api-orders-set-status', args=[ref])
        self.assertEqual(self.client.post(url, {'status': 'CONFIRMED'}).status_code, 403)
        self.client.force_authenticate(make_admin())
        self.assertEqual(self.client.post(url, {'status': 'CONFIRMED'}).data['status'], 'CONFIRMED')

    def test_cancel(self):
        ref = self.order(self.alice).data['reference']
        self.assertEqual(self.client.post(reverse('api-orders-cancel', args=[ref])).data['status'], 'CANCELLED')


class TokenAndPlannerApiTests(APITestCase):
    def test_token_login(self):
        make_user('tok')
        token = self.client.post(reverse('api-token'), {'username': 'tok', 'password': 'Str0ng!Pass'}).data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        self.assertEqual(self.client.get(reverse('api-orders-list')).status_code, 200)
        self.client.credentials()
        self.assertEqual(self.client.post(reverse('api-token'), {'username': 'tok', 'password': 'no'}).status_code, 400)

    def test_estimate(self):
        place = make_place()
        ok = self.client.post(reverse('api-estimate'), {'places': [place.slug], 'days': 2, 'travelers': 2}, format='json')
        self.assertEqual(set(ok.data['breakdown']), {'transport', 'hotel', 'food', 'entry_fees', 'extra'})
        bad = self.client.post(reverse('api-estimate'), {'places': ['nope'], 'days': 2, 'travelers': 2}, format='json')
        self.assertEqual(bad.status_code, 400)

    def test_recommend(self):
        make_place('Dec Place', months='12')
        data = self.client.post(reverse('api-recommend'), {'month': 12, 'daily_budget': 3000}, format='json').data
        self.assertEqual(data[0]['place']['name'], 'Dec Place')
