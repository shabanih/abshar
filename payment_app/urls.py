from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from payment_app import views

urlpatterns = [
    path('request-pay-fix/<int:charge_id>/', views.request_pay_fix, name='request_pay_fix'),
    path('verify-pay-fix/', views.verify_pay_fix, name='verify_pay_fix'),

    path('request-pay-area/<int:charge_id>/', views.request_pay_area, name='request_pay_area'),
    path('verify-pay-area/', views.verify_pay_area, name='verify_pay_area'),

    path('request-pay-person/<int:charge_id>/', views.request_pay_person, name='request_pay_person'),
    path('verify-pay-person/', views.verify_pay_person, name='verify_pay_person'),

    path('request-pay-fix-person/<int:charge_id>/', views.request_pay_fix_person, name='request_pay_fix_person'),
    path('verify-pay-fix-person/', views.verify_pay_fix_person, name='verify_pay_fix_person'),

    path('request-pay-fix-area/<int:charge_id>/', views.request_pay_fix_area, name='request_pay_fix_area'),
    path('verify-pay-fix-area/', views.verify_pay_fix_area, name='verify_pay_fix_area'),

    path('request-pay-person-area/<int:charge_id>/', views.request_pay_person_area, name='request_pay_person_area'),
    path('verify-pay-person-area/', views.verify_pay_person_area, name='verify_pay_person_area'),

    path('request-pay-fix-person-area/<int:charge_id>/', views.request_pay_fix_person_area, name='request_pay_fix_person_area'),
    path('verify-pay-fix-person-area/', views.verify_pay_fix_person_area, name='verify_pay_fix_person_area'),

    path('request-pay-fix-variable/<int:charge_id>/', views.request_pay_fix_variable, name='request_pay_fix_variable'),
    path('verify-pay-fix-variable/', views.verify_pay_fix_variable, name='verify_pay_fix_variable'),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
