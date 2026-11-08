from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'phone_number', 'home_city']
    search_fields = ['user__username', 'full_name', 'phone_number']
