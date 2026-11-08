from django.contrib import admin

from .models import TripPlan


@admin.register(TripPlan)
class TripPlanAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'start_date', 'days', 'travelers', 'estimated_total']
