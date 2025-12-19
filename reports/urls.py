from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from reports import views

urlpatterns = [
    path('fund/turnover', views.fund_turnover, name='fund_turn_over'),
    path('tarakonesh', views.fund_turnover_user, name='fund_turn_over_user'),
    path('report/', views.UnitReportsTurnOver.as_view(), name='unit_reports'),

    path('report/export/excel/', views.export_units_report_excel, name='export_units_report_excel'),
    path('report/export/pdf/', views.export_units_report_pdf, name='export_units_report_pdf'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)