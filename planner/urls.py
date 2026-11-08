from django.urls import path

from . import views

urlpatterns = [
    path('', views.trip_planner, name='planner'),
    path('where-to-go/', views.where_to_go, name='where_to_go'),
    path('my-plans/', views.my_plans, name='my_plans'),
    path('my-plans/<int:pk>/delete/', views.delete_plan, name='delete_plan'),
]
