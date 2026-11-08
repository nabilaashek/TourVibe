import secrets
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from tour.models import TourDestination, make_unique_slug


class Transport(models.TextChoices):
    BUS = 'BUS', 'AC Bus'
    TRAIN = 'TRAIN', 'Train'
    AIR = 'AIR', 'Flight'
    CAR = 'CAR', 'Private Car'


class TourPackage(models.Model):
    title = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    destinations = models.ManyToManyField(TourDestination, related_name='packages')
    start_city = models.CharField(max_length=50, default='Dhaka')
    transport = models.CharField(max_length=10, choices=Transport.choices, default=Transport.BUS)
    days = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(30)])
    price_per_person = models.PositiveIntegerField(validators=[MinValueValidator(500)])
    total_seats = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(200)])
    start_date = models.DateField()
    summary = models.CharField(max_length=200)
    description = models.TextField()
    includes = models.TextField(help_text='One per line')
    excludes = models.TextField(blank=True, help_text='One per line')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['start_date', 'title']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = make_unique_slug(self, self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('package_detail', args=[self.slug])

    @property
    def end_date(self):
        return self.start_date + timedelta(days=self.days - 1)

    def seats_taken(self, skip_order=None):
        items = OrderItem.objects.filter(package=self, order__status__in=Order.ACTIVE)
        if skip_order is not None:
            items = items.exclude(order=skip_order)
        return items.aggregate(total=Sum('travelers'))['total'] or 0

    @property
    def seats_left(self):
        return max(self.total_seats - self.seats_taken(), 0)

    @property
    def has_started(self):
        return self.start_date <= timezone.localdate()

    @property
    def can_book(self):
        return self.is_active and not self.has_started and self.seats_left > 0

    @property
    def include_list(self):
        return [x.strip() for x in self.includes.splitlines() if x.strip()]

    @property
    def exclude_list(self):
        return [x.strip() for x in self.excludes.splitlines() if x.strip()]


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')

    def __str__(self):
        return f'Cart of {self.user.username}'

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.select_related('package'))


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    package = models.ForeignKey(TourPackage, on_delete=models.CASCADE)
    travelers = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(20)])

    class Meta:
        constraints = [models.UniqueConstraint(fields=['cart', 'package'], name='one_line_per_package')]

    def __str__(self):
        return f'{self.travelers} x {self.package.title}'

    @property
    def subtotal(self):
        return self.travelers * self.package.price_per_person


def new_reference():
    return 'PKG-' + secrets.token_hex(3).upper()


class Order(models.Model):
    PENDING = 'PENDING'
    CONFIRMED = 'CONFIRMED'
    CANCELLED = 'CANCELLED'
    STATUS_CHOICES = [(PENDING, 'Pending'), (CONFIRMED, 'Confirmed'), (CANCELLED, 'Cancelled')]
    ACTIVE = [PENDING, CONFIRMED]

    reference = models.CharField(max_length=12, unique=True, default=new_reference, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    contact_name = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=14)
    note = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    total_price = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.reference

    def get_absolute_url(self):
        return reverse('order_detail', args=[self.reference])

    @property
    def can_cancel(self):
        if self.status == self.CANCELLED:
            return False
        return not any(item.package.has_started for item in self.items.select_related('package'))


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    package = models.ForeignKey(TourPackage, on_delete=models.PROTECT, related_name='order_items')
    travelers = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(20)])
    unit_price = models.PositiveIntegerField()  # price is saved at the time of order

    def __str__(self):
        return f'{self.travelers} x {self.package.title}'

    @property
    def subtotal(self):
        return self.travelers * self.unit_price
