from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from payment_app import views

urlpatterns = [
    path('request-pay/<int:charge_id>/', views.request_pay, name='request_pay'),
    path('verify-pay/', views.verify_pay, name='verify_pay'),
    path('payment/gateway/<int:pk>/', views.payment_charge_user_view, name='payment_gateway'),
    path('user/pay/money/<int:pk>/', views.user_pay_money_view, name='user_pay_money'),
    path('user-pay/request/<int:pay_id>/', views.request_user_pay_money, name='request_user_pay'),
    path('user-pay-verify/', views.verify_user_pay_money, name='verify_user_pay'),

    path(
        'unit-charge/payment<int:charge_id>/',
        views.unit_charge_middle_payment_view,
        name='unit_charge_payment'
    ),
    path('middle/pay/civil/<int:pk>/', views.middle_pay_civil_charge, name='middle_pay_civil_charge'),
    path('middle/cancel/pay/civil/<int:pk>/', views.middle_cancel_pay_civil_charge,
         name='middle_cancel_pay_civil_charge'),

    path('middle/pay/sewage/<int:pk>/', views.middle_pay_sewage, name='middle_pay_sewage'),
    path('middle/cancel/pay/sewage/<int:pk>/', views.middle_cancel_pay_sewage,
         name='middle_cancel_pay_sewage'),

    path('user/pay/civil/<int:pk>/', views.user_pay_civil_installment, name='user_pay_civil_charge'),
    path('user-pay/installment/request/<int:inst_id>/', views.request_user_pay_installment,
         name='request_user_pay_installment'),
    path('user-pay-installment-verify/', views.verify_user_pay_installment, name='verify_user_pay_installment'),

    path('user/pay/sewage/<int:pk>/', views.user_pay_sewage_installment, name='user_pay_sewage_installment'),
    path('user-pay-sewage/installment/request/<int:inst_id>/', views.request_user_pay_sewage_installment,
         name='request_user_pay_sewage_installment'),
    path('user-pay-sewage-installment-verify/', views.verify_user_pay_sewage_installment,
         name='verify_user_pay_sewage_installment'),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
