from django.urls import path

from user_app import views

urlpatterns = [
    path('', views.index, name='index'),
    path('user_dashboard/', views.user_panel, name='user_panel'),
    path('switch-to-manager/', views.switch_to_manager, name='switch_to_manager'),
    path('mobile-login/', views.mobile_login, name='mobile_login'),
    path('logout_user/', views.logout_user, name='logout_user'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),

    path('charge/pdf/<int:pk>/', views.export_charge_pdf, name='export_charge_pdf'),
    path('user-charges/', views.fetch_user_charges, name='user_charges'),
    path('user-announce/', views.AnnouncementListView.as_view(), name='user_announce_manage'),
    path('user/messages/', views.MessageListView.as_view(), name='user_message'),

    path('user-pay/', views.UserPayMoneyViewCreateView.as_view(), name='user_pay_money'),
    path('pay/user/edit/<int:pk>/', views.pay_user_edit, name='user_pay_money_edit'),
    path('pay/user/delete/<int:pk>/', views.user_pay_delete, name='user_pay_delete'),
    path('user/pay/delete-document/', views.user_delete_pay_document, name='user_delete_pay_document'),
    path('user-pay-pdf/', views.export_user_pay_money_pdf, name='user_pay_money_pdf'),
    path('user-pay-excel/', views.export_user_pay_money_excel, name='user_pay_money_excel'),

    path('profile/', views.user_profile, name='user_profile'),

]
