import math
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count
from django.urls import reverse
from django.utils.text import slugify

from userprofile.models import check_photo_size

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

# Dhaka Zero Point, used as the default start of every trip
DHAKA = (23.7261, 90.4125)


def make_unique_slug(obj, text):
    base = slugify(text)[:180] or 'item'
    slug, n = base, 2
    while type(obj).objects.filter(slug=slug).exclude(pk=obj.pk).exists():
        slug = f'{base}-{n}'
        n += 1
    return slug


def distance_km(lat1, lng1, lat2, lng2):
    """Straight-line distance between two GPS points (Haversine formula)."""
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class Division(models.Model):
    name = models.CharField(max_length=50, unique=True)
    bangla_name = models.CharField(max_length=50, blank=True)
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = make_unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    icon = models.CharField(max_length=30, default='geo-alt', help_text='Bootstrap icon name')

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = make_unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class DestinationQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def with_rating(self):
        return self.annotate(avg_rating=Avg('reviews__rating'), review_count=Count('reviews', distinct=True))


class TourDestination(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    division = models.ForeignKey(Division, on_delete=models.PROTECT, related_name='destinations')
    district = models.CharField(max_length=50)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='destinations')
    short_description = models.CharField(max_length=160)
    description = models.TextField()
    highlights = models.TextField(blank=True, help_text='One per line')
    tips = models.TextField(blank=True, help_text='One per line')
    best_months = models.CharField(max_length=40, help_text='Month numbers, e.g. 11,12,1,2')
    price_per_day = models.PositiveIntegerField(help_text='Typical food and stay cost per person per day (BDT)')
    entry_fee = models.PositiveIntegerField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6,
                                   validators=[MinValueValidator(Decimal('20.5')), MaxValueValidator(Decimal('26.7'))])
    longitude = models.DecimalField(max_digits=9, decimal_places=6,
                                    validators=[MinValueValidator(Decimal('88.0')), MaxValueValidator(Decimal('92.7'))])
    cover_image = models.ImageField(upload_to='tour_images/', blank=True, validators=[check_photo_size])
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = DestinationQuerySet.as_manager()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def clean(self):
        try:
            months = self.month_list
        except ValueError:
            months = []
        if not months:
            raise ValidationError({'best_months': 'Write month numbers from 1 to 12, separated by commas.'})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = make_unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('tour_detail', args=[self.slug])

    @property
    def month_list(self):
        months = [int(m) for m in str(self.best_months).replace(' ', '').split(',') if m]
        if any(m < 1 or m > 12 for m in months):
            raise ValueError('bad month')
        return months

    @property
    def month_names(self):
        return ', '.join(MONTHS[m - 1] for m in self.month_list)

    def good_in_month(self, month):
        return month in self.month_list

    @property
    def highlight_list(self):
        return [x.strip() for x in self.highlights.splitlines() if x.strip()]

    @property
    def tip_list(self):
        return [x.strip() for x in self.tips.splitlines() if x.strip()]

    def km_from(self, lat, lng):
        return distance_km(float(lat), float(lng), float(self.latitude), float(self.longitude))

    @property
    def km_from_dhaka(self):
        return round(self.km_from(*DHAKA))

    @property
    def map_link(self):
        return f'https://www.google.com/maps/search/?api=1&query={self.latitude},{self.longitude}'

    def rating(self):
        data = self.reviews.aggregate(avg=Avg('rating'), total=Count('id'))
        return {'avg': round(data['avg'] or 0, 1), 'total': data['total']}


class TourImage(models.Model):
    """Extra photos for the gallery of a destination."""
    tour = models.ForeignKey(TourDestination, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='tour_images/', validators=[check_photo_size])
    caption = models.CharField(max_length=120, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Photo of {self.tour.name}'


class Review(models.Model):
    tour = models.ForeignKey(TourDestination, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=100)
    comment = models.TextField(max_length=1500)
    visited_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [models.UniqueConstraint(fields=['tour', 'user'], name='one_review_per_user')]

    def __str__(self):
        return f'{self.rating} stars for {self.tour} by {self.user}'


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    tour = models.ForeignKey(TourDestination, on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-added_at']
        constraints = [models.UniqueConstraint(fields=['user', 'tour'], name='one_wishlist_item')]

    def __str__(self):
        return f'{self.user} likes {self.tour}'
