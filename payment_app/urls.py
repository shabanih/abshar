from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from payment_app import views

urlpatterns = [
    path('request-pay/<int:charge_id>/', views.request_pay, name='request_pay'),
    path('verify-pay/', views.verify_pay, name='verify_pay'),
    path('payment/gateway/<int:pk>/', views.paymentUserView, name='payment_gateway'),
    path('payment/charge/done/<int:pk>/', views.payment_done_view, name='payment_done'),

    path(
        'unit-charge/payment/<str:charge_type>/<int:charge_id>/',
        views.unit_charge_payment_view,
        name='unit_charge_payment'
    ),
    path('payment/unit-charge/done/<int:pk>/', views.charge_payment_done_view, name='charge_payment_done'),

    # path('request-pay-area/<int:charge_id>/', views.request_pay_area, name='request_pay_area'),
    # path('verify-pay-area/', views.verify_pay_area, name='verify_pay_area'),
    #
    # path('request-pay-person/<int:charge_id>/', views.request_pay_person, name='request_pay_person'),
    # path('verify-pay-person/', views.verify_pay_person, name='verify_pay_person'),
    #
    # path('request-pay-fix-person/<int:charge_id>/', views.request_pay_fix_person, name='request_pay_fix_person'),
    # path('verify-pay-fix-person/', views.verify_pay_fix_person, name='verify_pay_fix_person'),
    #
    # path('request-pay-fix-area/<int:charge_id>/', views.request_pay_fix_area, name='request_pay_fix_area'),
    # path('verify-pay-fix-area/', views.verify_pay_fix_area, name='verify_pay_fix_area'),
    #
    # path('request-pay-person-area/<int:charge_id>/', views.request_pay_person_area, name='request_pay_person_area'),
    # path('verify-pay-person-area/', views.verify_pay_person_area, name='verify_pay_person_area'),
    #
    # path('request-pay-fix-person-area/<int:charge_id>/', views.request_pay_fix_person_area, name='request_pay_fix_person_area'),
    # path('verify-pay-fix-person-area/', views.verify_pay_fix_person_area, name='verify_pay_fix_person_area'),
    #
    # path('request-pay-fix-variable/<int:charge_id>/', views.request_pay_fix_variable, name='request_pay_fix_variable'),
    # path('verify-pay-fix-variable/', views.verify_pay_fix_variable, name='verify_pay_fix_variable'),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
