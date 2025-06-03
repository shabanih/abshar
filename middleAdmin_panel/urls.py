from django.urls import path

from middleAdmin_panel import views

urlpatterns = [
    path('', views.middle_admin_dashboard, name='middle_admin_dashboard'),
    path('login-middleAdmin/', views.middle_admin_login_view, name='login_middle_admin'),
    path('log-out/', views.logout__middle_admin, name='logout_middle_admin'),

    path('middle-announcement/', views.MiddleAnnouncementView.as_view(), name='middle_announcement'),
    path('edit/middle/announcement/<int:pk>/', views.MiddleMyBankUpdateView.as_view(),
         name='edit_middle_announcement'),
    path('announcement-middle-delete/<int:pk>/', views.middle_announcement_delete, name='delete_middle_announcement'),

    # House Urls
    path('middle-manage-house', views.MiddleAddMyBankView.as_view(), name='middle_manage_house'),
    path('bank/middle/edit/<int:pk>/', views.MiddleMyBankUpdateView.as_view(), name='middle_edit_bank'),
    path('delete/middle/bank/<int:pk>/', views.middle_bank_delete, name='middle_delete_bank'),

    # Unit Urls
    path('middle-add-unit', views.MiddleUnitRegisterView.as_view(), name='middle_add_unit'),
    path('middle-info-unit/<int:pk>/', views.MiddleUnitInfoView.as_view(), name='middle_unit_info'),
    path('edit/middle/unit/<int:pk>/', views.MiddleUnitUpdateView.as_view(), name='middle_edit_unit'),
    path('delete/middle/unit/<int:pk>/', views.middle_unit_delete, name='middle_delete_unit'),
    path('middle-manage-unit', views.MiddleUnitListView.as_view(), name='middle_manage_unit'),
    path('units/export/excel/', views.export_units_excel, name='export_units_excel'),
    path('units/export/pdf/', views.export_units_pdf, name='export_units_pdf'),




]
