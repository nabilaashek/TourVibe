from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from booking.models import Transport
from tour.models import TourDestination


class TripPlan(models.Model):
    BUDGET_CHOICES = [('BUDGET', 'Budget'), ('STANDARD', 'Standard'), ('PREMIUM', 'Premium')]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trip_plans')
    title = models.CharField(max_length=120)
    places = models.ManyToManyField(TourDestination, related_name='trip_plans')
    start_date = models.DateField()
    days = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(30)])
    travelers = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(20)])
    budget = models.CharField(max_length=10, choices=BUDGET_CHOICES, default='STANDARD')
    transport = models.CharField(max_length=10, choices=Transport.choices, default=Transport.BUS)
    estimated_total = models.PositiveIntegerField(default=0)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
