from django.urls import path

from . import views

urlpatterns = [
    path('', views.tour_list, name='tour_list'),
    path('create/', views.create_tour, name='create_tour'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('review/<int:pk>/delete/', views.delete_review, name='delete_review'),
    path('<slug:slug>/', views.tour_detail, name='tour_detail'),
    path('<slug:slug>/edit/', views.update_tour, name='update_tour'),
    path('<slug:slug>/delete/', views.delete_tour, name='delete_tour'),
    path('<slug:slug>/photo/', views.add_photo, name='add_photo'),
    path('<slug:slug>/review/', views.save_review, name='save_review'),
    path('<slug:slug>/wishlist/', views.toggle_wishlist, name='toggle_wishlist'),
]
