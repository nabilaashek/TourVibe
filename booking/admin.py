from django.contrib import admin

from .models import Cart, CartItem, Order, OrderItem, TourPackage


@admin.register(TourPackage)
class TourPackageAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_date', 'days', 'price_per_person', 'total_seats', 'seats_left', 'is_active']
    list_filter = ['is_active', 'transport']
    filter_horizontal = ['destinations']
    prepopulated_fields = {'slug': ['title']}


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['package', 'travelers', 'unit_price']
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['reference', 'user', 'contact_name', 'total_price', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['reference', 'contact_name', 'user__username']
    readonly_fields = ['reference', 'total_price', 'created_at']
    inlines = [OrderItemInline]


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    inlines = [CartItemInline]
