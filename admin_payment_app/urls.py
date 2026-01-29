from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from admin_payment_app import views

urlpatterns = [
    path('sms-pay/request/', views.request_sms_pay, name='request_sms_pay'),
    path('verify-sms-pay/', views.verify_sms_credit_pay, name='verify_sms_pay'),


]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
