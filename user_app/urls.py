from django.urls import path

from user_app import views

urlpatterns = [
    path('', views.index, name='index'),
    # path('dashboard/', views.dashboard, name='dashboard'),
    path('mobile-login/', views.mobile_login, name='mobile_login'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
]

