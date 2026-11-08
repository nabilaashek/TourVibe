from django.urls import path

from . import views

urlpatterns = [
    path('', views.package_list, name='package_list'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_history, name='order_history'),
    path('orders/manage/', views.manage_orders, name='manage_orders'),
    path('orders/export.csv', views.export_orders, name='export_orders'),
    path('orders/<str:reference>/', views.order_detail, name='order_detail'),
    path('orders/<str:reference>/cancel/', views.cancel_order, name='cancel_order'),
    path('orders/<str:reference>/invoice/', views.invoice, name='invoice'),
    path('orders/<str:reference>/status/', views.set_status, name='set_status'),
    path('package/<slug:slug>/', views.package_detail, name='package_detail'),
    path('package/<slug:slug>/add/', views.add_to_cart, name='add_to_cart'),
]
