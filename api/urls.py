from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.include_root_view = False
router.register('divisions', views.DivisionViewSet, basename='api-divisions')
router.register('categories', views.CategoryViewSet, basename='api-categories')
router.register('destinations', views.DestinationViewSet, basename='api-destinations')
router.register('reviews', views.ReviewViewSet, basename='api-reviews')
router.register('packages', views.PackageViewSet, basename='api-packages')
router.register('orders', views.OrderViewSet, basename='api-orders')
router.register('plans', views.TripPlanViewSet, basename='api-plans')

urlpatterns = [
    path('', views.api_home, name='api-home'),
    path('token/', obtain_auth_token, name='api-token'),
    path('planner/estimate/', views.planner_estimate, name='api-estimate'),
    path('planner/recommend/', views.planner_recommend, name='api-recommend'),
    path('', include(router.urls)),
]
