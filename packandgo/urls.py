from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from . import views

admin.site.site_header = 'TourVibe Admin'
admin.site.site_title = 'TourVibe Admin'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin/', admin.site.urls),
    path('accounts/', include('userprofile.urls')),
    path('tour/', include('tour.urls')),
    path('booking/', include('booking.urls')),
    path('planner/', include('planner.urls')),
    path('api/', include('api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'packandgo.views.page_not_found'
