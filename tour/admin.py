from django.contrib import admin

from .models import Category, Division, Review, TourDestination, TourImage, Wishlist


class TourImageInline(admin.TabularInline):
    model = TourImage
    extra = 1


@admin.register(TourDestination)
class TourDestinationAdmin(admin.ModelAdmin):
    list_display = ['name', 'district', 'division', 'category', 'price_per_day', 'is_featured', 'is_active']
    list_filter = ['division', 'category', 'is_featured', 'is_active']
    list_editable = ['is_featured', 'is_active']
    search_fields = ['name', 'district']
    prepopulated_fields = {'slug': ['name']}
    inlines = [TourImageInline]


admin.site.register(Division)
admin.site.register(Category)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['tour', 'user', 'rating', 'title', 'created_at']
    list_filter = ['rating']


admin.site.register(Wishlist)
