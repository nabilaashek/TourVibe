"""Helpers to create test data quickly."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from booking.models import TourPackage
from tour.models import Category, Division, TourDestination


def make_user(username='traveler', password='Str0ng!Pass', **extra):
    return User.objects.create_user(username, f'{username}@test.bd', password, **extra)


def make_admin(username='boss'):
    return make_user(username, is_staff=True)


def make_place(name='Test Beach', division='Chattogram', category='Beach', lat=21.43, lng=92.0,
               months='11,12,1', price=3000, entry_fee=None, **extra):
    div, _ = Division.objects.get_or_create(name=division)
    cat, _ = Category.objects.get_or_create(name=category)
    return TourDestination.objects.create(
        name=name, division=div, district='Test District', category=cat, latitude=lat, longitude=lng,
        best_months=months, price_per_day=price, entry_fee=entry_fee, short_description='Nice place',
        description='A lovely place.', **extra)


def make_package(title='Test Tour', places=None, seats=10, price=5000, starts_in=10, **extra):
    package = TourPackage.objects.create(
        title=title, days=3, price_per_person=price, total_seats=seats,
        start_date=timezone.localdate() + timedelta(days=starts_in), summary='Summary',
        description='Description', includes='Bus\nHotel', **extra)
    package.destinations.set(places or [make_place(name=f'{title} place')])
    return package
