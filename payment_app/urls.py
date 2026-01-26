from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from payment_app import views

urlpatterns = [
    path('request-pay/<int:charge_id>/', views.request_pay, name='request_pay'),
    path('verify-pay/', views.verify_pay, name='verify_pay'),
    path('payment/gateway/<int:pk>/', views.payment_user_view, name='payment_gateway'),
    # path('payment/charge/done/<int:pk>/', views.payment_done_view, name='payment_done'),

    path(
        'unit-charge/payment<int:charge_id>/',
        views.unit_charge_payment_view,
        name='unit_charge_payment'
    ),
    path('payment/unit-charge/done/<int:pk>/', views.charge_payment_done_view, name='charge_payment_done'),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
