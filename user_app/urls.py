from django.urls import path

from user_app import views

urlpatterns = [
    path('', views.index, name='index'),
    path('user_dashboard/', views.user_panel, name='user_panel'),
    path('mobile-login/', views.mobile_login, name='mobile_login'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),

    path('fixed-charges/', views.fetch_user_fixed_charges, name='user_fixed_charges'),
]

