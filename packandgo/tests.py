from django.test import TestCase
from django.urls import reverse

from .testing import make_admin, make_package, make_place, make_user


class PageTests(TestCase):
    def setUp(self):
        make_place(is_featured=True)
        make_package()

    def test_public_pages(self):
        for name in ['home', 'about', 'tour_list', 'package_list', 'planner', 'where_to_go', 'login', 'signup',
                     'api-home']:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_dashboards(self):
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 302)
        self.client.force_login(make_user())
        self.assertTemplateUsed(self.client.get(reverse('dashboard')), 'core/dashboard.html')
        self.client.force_login(make_admin())
        self.assertTemplateUsed(self.client.get(reverse('dashboard')), 'core/admin_dashboard.html')

    def test_404_page(self):
        with self.settings(DEBUG=False):
            response = self.client.get('/no-such-page/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')

    def test_security_headers(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response['X-Frame-Options'], 'DENY')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
