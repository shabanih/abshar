from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from reports import views

urlpatterns = [
    path('fund/turnover', views.fund_turnover, name='fund_turn_over'),
    path('report/unit', views.unit_reports, name='unit_reports')
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)