from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from packandgo.testing import make_admin, make_package, make_user

from .models import CartItem, Order
from .services import change_status, place_order


class OrderRuleTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.tour = make_package(seats=5, price=4000)

    def test_order_total_and_saved_price(self):
        order = place_order(self.user, [(self.tour, 2)], 'A', '01712345678')
        self.assertEqual(order.total_price, 8000)
        self.tour.price_per_person = 9999
        self.tour.save()
        self.assertEqual(order.items.get().unit_price, 4000)

    def test_seats_cannot_be_overbooked(self):
        place_order(self.user, [(self.tour, 4)], 'A', '01712345678')
        self.assertEqual(self.tour.seats_left, 1)
        with self.assertRaises(ValidationError):
            place_order(self.user, [(self.tour, 2)], 'B', '01712345678')

    def test_order_is_all_or_nothing(self):
        full = make_package('Full Tour', seats=1)
        with self.assertRaises(ValidationError):
            place_order(self.user, [(self.tour, 1), (full, 2)], 'A', '01712345678')
        self.assertEqual(Order.objects.count(), 0)

    def test_cancelling_frees_seats(self):
        order = place_order(self.user, [(self.tour, 5)], 'A', '01712345678')
        self.assertEqual(self.tour.seats_left, 0)
        change_status(order, Order.CANCELLED)
        self.assertEqual(self.tour.seats_left, 5)

    def test_cancelled_order_cannot_come_back_if_seats_are_gone(self):
        order = place_order(self.user, [(self.tour, 3)], 'A', '01712345678')
        change_status(order, Order.CANCELLED)
        place_order(make_user('b'), [(self.tour, 4)], 'B', '01712345678')
        with self.assertRaises(ValidationError):
            change_status(order, Order.CONFIRMED)

    def test_started_tour_cannot_be_ordered(self):
        old = make_package('Old Tour', starts_in=-1)
        with self.assertRaises(ValidationError):
            place_order(self.user, [(old, 1)], 'A', '01712345678')


class CartTests(TestCase):
    """The cart from the first Pack-Go, with the old bugs fixed."""

    def setUp(self):
        self.user = make_user()
        self.tour = make_package(seats=3)
        self.client.force_login(self.user)

    def add(self, travelers):
        return self.client.post(reverse('add_to_cart', args=[self.tour.slug]), {'travelers': travelers})

    def test_add_to_cart_uses_chosen_number(self):
        self.add(2)
        self.assertEqual(CartItem.objects.get().travelers, 2)  # old version started at 2 by mistake
        self.add(1)
        self.assertEqual(CartItem.objects.count(), 1)

    def test_add_to_cart_must_be_post(self):
        self.assertEqual(self.client.get(reverse('add_to_cart', args=[self.tour.slug])).status_code, 405)

    def test_bad_numbers_do_not_crash(self):
        self.add(1)
        item = CartItem.objects.get()
        for bad in ['-5', 'abc', '0', '99']:
            response = self.client.post(reverse('update_cart', args=[item.id]), {'travelers': bad})
            self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.travelers, 1)

    def test_too_many_travelers(self):
        self.add(4)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_cannot_touch_other_users_cart(self):
        self.add(1)
        item = CartItem.objects.get()
        self.client.force_login(make_user('other'))
        self.assertEqual(self.client.post(reverse('remove_from_cart', args=[item.id])).status_code, 404)

    def test_checkout_creates_order_and_empties_cart(self):
        self.add(2)
        response = self.client.post(reverse('checkout'), {'contact_name': 'Test', 'contact_phone': '01712345678'})
        order = Order.objects.get()
        self.assertRedirects(response, order.get_absolute_url())
        self.assertEqual(order.status, Order.PENDING)
        self.assertTrue(order.reference.startswith('PKG-'))
        self.assertEqual(CartItem.objects.count(), 0)

    def test_checkout_rejects_bad_phone(self):
        self.add(1)
        self.client.post(reverse('checkout'), {'contact_name': 'Test', 'contact_phone': '123'})
        self.assertEqual(Order.objects.count(), 0)


class OrderPageTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.order = place_order(self.user, [(make_package(), 1)], 'A', '01712345678')

    def test_other_users_get_404(self):
        self.client.force_login(make_user('stranger'))
        for name in ['order_detail', 'invoice']:
            self.assertEqual(self.client.get(reverse(name, args=[self.order.reference])).status_code, 404)

    def test_owner_gets_pdf_and_can_cancel(self):
        self.client.force_login(self.user)
        pdf = self.client.get(reverse('invoice', args=[self.order.reference]))
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.client.post(reverse('cancel_order', args=[self.order.reference]))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.CANCELLED)

    def test_only_admin_confirms(self):
        url = reverse('set_status', args=[self.order.reference])
        self.client.force_login(self.user)
        self.client.post(url, {'status': 'CONFIRMED'})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PENDING)
        self.client.force_login(make_admin())
        self.client.post(url, {'status': 'CONFIRMED'})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.CONFIRMED)
        self.assertIn(self.order.reference, self.client.get(reverse('export_orders')).content.decode())
