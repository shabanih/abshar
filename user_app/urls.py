from django.urls import path

from user_app import views

urlpatterns = [
    path('', views.index, name='index'),
    path('user_dashboard/', views.user_panel, name='user_panel'),
    path('mobile-login/', views.mobile_login, name='mobile_login'),
    path('logout_user/', views.logout_user, name='logout_user'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),

    path('charge/fv/pdf/<int:pk>/', views.export_fix_variable_charge_pdf, name='export_fix_variable_charge_pdf'),
    path('charge/area/pdf/<int:pk>/', views.export_area_charge_pdf, name='export_area_charge_pdf'),
    path('charge/fix/person/pdf/<int:pk>/', views.export_fix_person_charge_pdf, name='export_fix_person_charge_pdf'),
    path('charge/person/area/pdf/<int:pk>/', views.export_person_area_charge_pdf, name='export_person_area_charge_pdf'),
    path('charge/fix/pdf/<int:pk>/', views.export_fix_charge_pdf, name='export_fix_charge_pdf'),
    path('charge/person/pdf/<int:pk>/', views.export_person_charge_pdf, name='export_person_charge_pdf'),
    path('charge/fix/area/pdf/<int:pk>/', views.export_fix_area_charge_pdf, name='export_fix_area_charge_pdf'),
    path('charge/fix/person/area/pdf/<int:pk>/', views.export_fix_person_area_charge_pdf,
         name='export_fix_person_area_charge_pdf'),

    path('fixed-charges/', views.fetch_user_fixed_charges, name='user_fixed_charges'),
]

