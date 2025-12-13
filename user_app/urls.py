from django.urls import path

from user_app import views

urlpatterns = [
    path('', views.index, name='index'),
    path('user_dashboard/', views.user_panel, name='user_panel'),
    path('mobile-login/', views.mobile_login, name='mobile_login'),
    path('logout_user/', views.logout_user, name='logout_user'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),

    path('charge/pdf/<int:pk>/', views.export_charge_pdf, name='export_charge_pdf'),
    path('user-charges/', views.fetch_user_charges, name='user_charges'),
    path('user-announce/', views.user_announcements, name='user_announce_manage'),

]
