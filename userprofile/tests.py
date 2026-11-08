from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from packandgo.testing import make_admin, make_user

from .models import UserProfile, bd_phone, is_admin


class SignUpTests(TestCase):
    def test_signup_creates_traveler_with_profile(self):
        response = self.client.post(reverse('signup'), {
            'username': 'rahim', 'full_name': 'Rahim Uddin', 'email': 'rahim@test.bd', 'phone_number': '01712345678',
            'password1': 'Tr4vel!Bangla', 'password2': 'Tr4vel!Bangla'})
        self.assertRedirects(response, reverse('dashboard'))
        user = User.objects.get(username='rahim')
        self.assertFalse(user.is_staff)
        self.assertEqual(user.profile.full_name, 'Rahim Uddin')
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_signup_cannot_make_admin(self):
        self.client.post(reverse('signup'), {
            'username': 'hacker', 'full_name': 'H', 'email': 'h@test.bd', 'is_staff': 'on', 'is_superuser': 'on',
            'password1': 'Tr4vel!Bangla', 'password2': 'Tr4vel!Bangla'})
        self.assertFalse(User.objects.get(username='hacker').is_staff)

    def test_same_email_twice_is_rejected(self):
        make_user('first')
        response = self.client.post(reverse('signup'), {
            'username': 'second', 'full_name': 'S', 'email': 'FIRST@test.bd',
            'password1': 'Tr4vel!Bangla', 'password2': 'Tr4vel!Bangla'})
        self.assertContains(response, 'already registered')
        self.assertFalse(User.objects.filter(username='second').exists())

    def test_weak_password_is_rejected(self):
        self.client.post(reverse('signup'), {'username': 'weak', 'full_name': 'W', 'email': 'w@test.bd',
                                             'password1': '12345678', 'password2': '12345678'})
        self.assertFalse(User.objects.filter(username='weak').exists())


class LoginAndProfileTests(TestCase):
    def test_login_logout(self):
        make_user('karim')
        response = self.client.post(reverse('login'), {'username': 'karim', 'password': 'Str0ng!Pass'})
        self.assertRedirects(response, reverse('dashboard'))
        self.assertRedirects(self.client.post(reverse('logout')), reverse('home'))

    def test_wrong_password(self):
        make_user('karim')
        self.client.post(reverse('login'), {'username': 'karim', 'password': 'wrong'})
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_profile_needs_login(self):
        for name in ['profile', 'edit_profile']:
            self.assertEqual(self.client.get(reverse(name)).status_code, 302)

    def test_every_user_gets_a_profile(self):
        user = make_user()
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    def test_edit_profile(self):
        user = make_user()
        self.client.force_login(user)
        response = self.client.post(reverse('edit_profile'), {
            'full_name': 'Karim Ali', 'email': 'karim@test.bd', 'phone_number': '01812345678', 'home_city': 'Sylhet',
            'address': 'Zindabazar'})
        self.assertRedirects(response, reverse('profile'))
        user.refresh_from_db()
        self.assertEqual(user.profile.home_city, 'Sylhet')
        self.assertEqual(user.email, 'karim@test.bd')

    def test_bad_phone_is_rejected(self):
        self.client.force_login(make_user())
        response = self.client.post(reverse('edit_profile'), {'full_name': 'K', 'email': 'k@test.bd',
                                                              'phone_number': '12345'})
        self.assertEqual(response.status_code, 200)


class HelperTests(TestCase):
    def test_is_admin(self):
        self.assertFalse(is_admin(make_user()))
        self.assertTrue(is_admin(make_admin()))

    def test_bangladeshi_phone(self):
        for good in ['01712345678', '8801712345678', '+8801912345678']:
            bd_phone(good)
        for bad in ['0171234567', '01212345678', 'hello']:
            with self.assertRaises(ValidationError):
                bd_phone(bad)
