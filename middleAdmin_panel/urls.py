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

    # Expense_category Urls
    path('middle_add-category-expense', views.MiddleExpenseCategoryView.as_view(), name='middle_add_category_expense'),
    path('edit/middle/category/expense/<int:pk>/', views.MiddleExpenseCategoryUpdate.as_view(),
         name='middle_edit_category_expense'),
    path('delete/middle/category/expense/<int:pk>/', views.middle_expense_category_delete,
         name='middle_delete_category_expense'),

    # Expense Urls
    path('middle-add-expense', views.MiddleExpenseView.as_view(), name='middle_add_expense'),
    path('expense/middle/edit/<int:pk>/', views.middle_expense_edit, name='middle_expense_edit'),
    path('expense/middle/delete/<int:pk>/', views.middle_expense_delete, name='middle_expense_delete'),
    path('expense/middle/delete-document/', views.middle_delete_expense_document,
         name='middle_delete_expense_document'),
    path('expense/export/excel/', views.export_units_excel, name='export_expense_excel'),
    path('expense/export/pdf/', views.export_expense_pdf, name='export_expense_pdf'),

    # Income_category Urls
    path('middle-add-category_income', views.MiddleIncomeCategoryView.as_view(), name='middle_add_category_income'),
    path('edit/category/middle/income/<int:pk>/', views.MiddleIncomeCategoryUpdate.as_view(),
         name='middle_edit_category_income'),
    path('delete/category/middle/income/<int:pk>/', views.middle_income_category_delete,
         name='middle_delete_category_income'),

    # Income Urls
    path('middle-add-income', views.MiddleIncomeView.as_view(), name='middle_add_income'),
    path('income/middle/edit/<int:pk>/', views.middle_income_edit, name='middle_income_edit'),
    path('income/middle/delete/<int:pk>/', views.middle_income_delete, name='middle_income_delete'),
    path('income/middle/delete-document/', views.middle_delete_income_document, name='middle_delete_income_document'),
    path('income/export/excel/', views.export_income_excel, name='export_income_excel'),
    path('income/export/pdf/', views.export_income_pdf, name='export_income_pdf'),

    # ReceiveMoney Urls
    path('middle-add-receive', views.MiddleReceiveMoneyCreateView.as_view(), name='middle_add_receive'),
    path('receive/middle/edit/<int:pk>/', views.middle_receive_edit, name='middle_receive_edit'),
    path('receive/middle/delete/<int:pk>/', views.middle_receive_delete, name='middle_receive_delete'),
    path('receive/middle/delete-document/', views.middle_delete_receive_document, name='middle_delete_delete_document'),
    path('receive/export/excel/', views.export_receive_excel, name='export_receive_excel'),
    path('receive/export/pdf/', views.export_receive_pdf, name='export_receive_pdf'),

    # PayMoney Urls
    path('middle-add-pay', views.MiddlePaymentMoneyCreateView.as_view(), name='middle_add_pay'),
    path('pay/middle/edit/<int:pk>/', views.middle_pay_edit, name='middle_pay_edit'),
    path('pay/middle/delete/<int:pk>/', views.middle_pay_delete, name='middle_pay_delete'),
    path('pay/middle/delete-document/', views.middle_delete_pay_document, name='middle_delete_pay_document'),
    path('pay/export/excel/', views.export_pay_excel, name='export_pay_excel'),
    path('pay/export/pdf/', views.export_pay_pdf, name='export_pay_pdf'),

    # Property Urls
    path('middle-add-Property', views.MiddlePropertyCreateView.as_view(), name='middle_add_property'),
    path('Property/middle/edit/<int:pk>/', views.middle_property_edit, name='middle_property_edit'),
    path('Property/middle/delete/<int:pk>/', views.middle_property_delete, name='middle_property_delete'),
    path('middleProperty/delete-document/', views.middle_delete_property_document, name='middle_delete_property_document'),
    path('Property/export/excel/', views.export_property_excel, name='export_property_excel'),
    path('Property/export/pdf/', views.export_property_pdf, name='export_property_pdf'),

    # Maintenance Urls
    path('middle-add-maintenance', views.MiddleMaintenanceCreateView.as_view(), name='middle_add_maintenance'),
    path('maintenance/middle/edit/<int:pk>/', views.middle_maintenance_edit, name='middle_maintenance_edit'),
    path('maintenance/middle/delete/<int:pk>/', views.middle_maintenance_delete, name='middle_maintenance_delete'),
    path('maintenance/middle/delete-document/', views.middle_delete_maintenance_document,
         name='middle_delete_maintenance_document'),
    path('maintenance/export/excel/', views.export_maintenance_excel, name='export_maintenance_excel'),
    path('maintenance/export/pdf/', views.export_maintenance_pdf, name='export_maintenance_pdf'),

    # Charge Urls
    path('middle-add-charge', views.middle_charge_view, name='middle_add_charge'),

    path('middle-add-fixed-Charge', views.MiddleFixChargeCreateView.as_view(), name='middle_add_fixed_charge'),
    path('charge/middle/edit/<int:pk>/', views.middle_fix_charge_edit, name='middle_charge_edit'),
    path('charge/middle/delete/<int:pk>/', views.middle_fix_charge_delete, name='middle_fix_charge_delete'),
    path('charge/middle/notify/<int:pk>/', views.middle_show_fix_charge_notification_form,
         name='middle_show_notification_fix_charge_form'),
    path('charge/middle/notify/send/<int:pk>/', views.middle_send_notification_fix_charge_to_user,
         name='middle_send_notification_fix_charge_to_user'),
    path('charge/middle/notify/remove/<int:pk>/', views.middle_remove_send_notification_fix,
         name='middle_remove_send_notification_ajax'),

    path('middle-add-area-charge', views.MiddleAreaChargeCreateView.as_view(), name='middle_add_area_charge'),
    path('area/middle/charge/edit/<int:pk>/', views.middle_area_charge_edit, name='middle_charge_area_edit'),
    path('area/middle/charge/delete/<int:pk>/', views.middle_area_charge_delete, name='middle_charge-area_delete'),
    path('charge/middle/area/notify/<int:pk>/', views.middle_show_area_charge_notification_form,
         name='middle_show_notification_area_charge_form'),
    path('charge/area/notify/send/<int:pk>/', views.middle_send_notification_area_charge_to_user,
         name='send_notification_area_charge_to_user'),
    path('remove-send-notification-ajax/<int:pk>/', views.middle_remove_send_notification_area,
         name='remove_send_notification_ajax'),

]
