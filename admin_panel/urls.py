from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from admin_panel import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('login-admin/', views.admin_login_view, name='login_admin'),
    path('log-out-admin/', views.logout_admin, name='logout_admin'),

    path('create-middle-admin/', views.MiddleAdminCreateView.as_view(), name='create_middle_admin'),
    path('middle/edit/<int:pk>/', views.MiddleAdminUpdateView.as_view(), name='edit_middle_admin'),
    path('middle/delete/<int:pk>/', views.middleAdmin_delete, name='delete_middle_admin'),

    # Announce urls
    path('announcement/', views.AnnouncementView.as_view(), name='announcement'),
    path('edit/announcement/<int:pk>/', views.AnnouncementUpdateView.as_view(), name='edit_announcement'),
    path('announcement-delete/<int:pk>/', views.announcement_delete, name='delete_announcement'),

    # House Urls
    path('manage-house', views.AddMyHouseView.as_view(), name='manage_house'),
    path('bank/edit/<int:pk>/', views.MyBankUpdateView.as_view(), name='edit_bank'),
    path('delete/bank/<int:pk>/', views.bank_delete, name='delete_bank'),



    # Unit Urls
    path('add-unit', views.UnitRegisterView.as_view(), name='add_unit'),
    path('info-unit/<int:pk>/', views.UnitInfoView.as_view(), name='unit_info'),
    path('edit/unit/<int:pk>/', views.UnitUpdateView.as_view(), name='edit_unit'),
    path('delete/unit/<int:pk>/', views.unit_delete, name='delete_unit'),
    path('manage-unit', views.UnitListView.as_view(), name='manage_unit'),
    path('units/export/excel/', views.export_units_excel, name='export_units_excel'),
    path('units/export/pdf/', views.export_units_pdf, name='export_units_pdf'),

    # Expense_category Urls
    path('add-category-expense', views.ExpenseCategoryView.as_view(), name='add_category_expense'),
    path('edit/category/expense/<int:pk>/', views.ExpenseCategoryUpdate.as_view(), name='edit_category_expense'),
    path('delete/category/expense/<int:pk>/', views.expense_category_delete, name='delete_category_expense'),

    # Expense Urls
    path('add-expense', views.ExpenseView.as_view(), name='add_expense'),
    path('expense/edit/<int:pk>/', views.expense_edit, name='expense_edit'),
    path('expense/delete/<int:pk>/', views.expense_delete, name='expense_delete'),
    path('expense/delete-document/', views.delete_expense_document, name='delete_expense_document'),
    path('expense/export/excel/', views.export_units_excel, name='export_expense_excel'),
    path('expense/export/pdf/', views.export_expense_pdf, name='export_expense_pdf'),

    # Income_category Urls
    path('add-category_income', views.IncomeCategoryView.as_view(), name='add_category_income'),
    path('edit/category/income/<int:pk>/', views.IncomeCategoryUpdate.as_view(), name='edit_category_income'),
    path('delete/category/income/<int:pk>/', views.income_category_delete, name='delete_category_income'),

    # Income Urls
    path('add-income', views.IncomeView.as_view(), name='add_income'),
    path('income/edit/<int:pk>/', views.income_edit, name='income_edit'),
    path('income/delete/<int:pk>/', views.income_delete, name='income_delete'),
    path('income/delete-document/', views.delete_income_document, name='delete_income_document'),
    path('income/export/excel/', views.export_income_excel, name='export_income_excel'),
    path('income/export/pdf/', views.export_income_pdf, name='export_income_pdf'),

    # ReceiveMoney Urls
    path('add-receive', views.ReceiveMoneyCreateView.as_view(), name='add_receive'),
    path('receive/edit/<int:pk>/', views.receive_edit, name='receive_edit'),
    path('receive/delete/<int:pk>/', views.receive_delete, name='receive_delete'),
    path('receive/delete-document/', views.delete_receive_document, name='delete_delete_document'),
    path('receive/export/excel/', views.export_receive_excel, name='export_receive_excel'),
    path('receive/export/pdf/', views.export_receive_pdf, name='export_receive_pdf'),

    # PayMoney Urls
    path('add-pay', views.PaymentMoneyCreateView.as_view(), name='add_pay'),
    path('pay/edit/<int:pk>/', views.pay_edit, name='pay_edit'),
    path('pay/delete/<int:pk>/', views.pay_delete, name='pay_delete'),
    path('pay/delete-document/', views.delete_pay_document, name='delete_pay_document'),
    path('pay/export/excel/', views.export_pay_excel, name='export_pay_excel'),
    path('pay/export/pdf/', views.export_pay_pdf, name='export_pay_pdf'),

    # Property Urls
    path('add-productProperty', views.PropertyCreateView.as_view(), name='add_property'),
    path('productProperty/edit/<int:pk>/', views.property_edit, name='property_edit'),
    path('productProperty/delete/<int:pk>/', views.property_delete, name='property_delete'),
    path('productProperty/delete-document/', views.delete_property_document, name='delete_property_document'),
    path('productProperty/export/excel/', views.export_property_excel, name='export_property_excel'),
    path('productProperty/export/pdf/', views.export_property_pdf, name='export_property_pdf'),

    # Maintenance Urls
    path('add-maintenance', views.MaintenanceCreateView.as_view(), name='add_maintenance'),
    path('maintenance/edit/<int:pk>/', views.maintenance_edit, name='maintenance_edit'),
    path('maintenance/delete/<int:pk>/', views.maintenance_delete, name='maintenance_delete'),
    path('maintenance/delete-document/', views.delete_maintenance_document, name='delete_maintenance_document'),
    path('maintenance/export/excel/', views.export_maintenance_excel, name='export_maintenance_excel'),
    path('maintenance/export/pdf/', views.export_maintenance_pdf, name='export_maintenance_pdf'),

    # Charge Urls
    path('add-charge', views.charge_view, name='add_charge'),

    path('add-fixed-Charge', views.FixChargeCreateView.as_view(), name='add_fixed_charge'),
    path('charge/edit/<int:pk>/', views.fix_charge_edit, name='charge_edit'),
    path('charge/delete/<int:pk>/', views.fix_charge_delete, name='fix_charge_delete'),
    path('charge/notify/<int:pk>/', views.show_fix_charge_notification_form, name='show_notification_fix_charge_form'),
    path('charge/fix/notify/send/<int:pk>/', views.send_notification_fix_charge_to_user,
         name='send_notification_fix_charge_to_user'),
    path('remove-send-notification-fix/<int:pk>/', views.remove_send_notification_fix,
         name='remove_send_notification_fix'),

    path('add-area-charge', views.AreaChargeCreateView.as_view(), name='add_area_charge'),
    path('area/charge/edit/<int:pk>/', views.area_charge_edit, name='charge_area_edit'),
    path('area/charge/delete/<int:pk>/', views.area_charge_delete, name='charge-area_delete'),
    path('charge/area/notify/<int:pk>/', views.show_area_charge_notification_form,
         name='show_notification_area_charge_form'),
    path('charge/area/notify/send/<int:pk>/', views.send_notification_area_charge_to_user,
         name='send_notification_area_charge_to_user'),
    path('remove-send-notification-ajax/<int:pk>/', views.remove_send_notification_ajax,
         name='remove_send_notification_ajax'),

    path('add-person-charge', views.PersonChargeCreateView.as_view(), name='add_person_charge'),
    path('person/charge/edit/<int:pk>/', views.person_charge_edit, name='charge_person_edit'),
    path('person/charge/delete/<int:pk>/', views.person_charge_delete, name='charge-person_delete'),
    path('charge/person/notify/<int:pk>/', views.show_person_charge_notification_form,
         name='show_notification_person_charge_form'),
    path('charge/person/notify/send/<int:pk>/', views.send_notification_person_charge_to_user,
         name='send_notification_person_charge_to_user'),
    path('remove-send-notification-person/<int:pk>/', views.remove_send_notification_person,
         name='remove_send_notification_person'),

    path('add-fix_person-charge', views.FixPersonChargeCreateView.as_view(), name='add_fix_person_charge'),
    path('fix/person/charge/edit/<int:pk>/', views.fix_person_charge_edit, name='charge_fix_person_edit'),
    path('fix/person/charge/delete/<int:pk>/', views.fix_person_charge_delete, name='charge_fix_person_delete'),
    path('charge/fix/person/notify/<int:pk>/', views.show_fix_person_charge_notification_form,
         name='show_notification_fix_person_charge_form'),
    path('charge/fix/person/notify/send/<int:pk>/', views.send_notification_fix_person_charge_to_user,
         name='send_notification_fix_person_charge_to_user'),
    path('remove-send-notification-fix-person/<int:pk>/', views.remove_send_notification_fix_person,
         name='remove_send_notification_fix_person'),

    path('add-fix_area-charge', views.FixAreaChargeCreateView.as_view(), name='add_fix_area_charge'),
    path('fix/area/charge/edit/<int:pk>/', views.fix_area_charge_edit, name='charge_fix_area_edit'),
    path('fix/area/charge/delete/<int:pk>/', views.fix_area_charge_delete, name='charge-fix_area_delete'),
    path('charge/fix/area/notify/<int:pk>/', views.show_fix_area_charge_notification_form,
         name='show_notification_fix_area_charge_form'),
    path('charge/fix/area/notify/send/<int:pk>/', views.send_notification_fix_area_charge_to_user,
         name='send_notification_fix_area_charge_to_user'),
    path('remove-send-notification-fix-area/<int:pk>/', views.remove_send_notification_fix_area,
         name='remove_send_notification_fix_area'),


    path('add-person_area-charge', views.PersonAreaChargeCreateView.as_view(), name='add_person_area_charge'),
    path('area/person/charge/edit/<int:pk>/', views.person_area_charge_edit, name='charge_area_person_edit'),
    path('area/person/charge/delete/<int:pk>/', views.person_area_charge_delete, name='charge_area_person_delete'),
    path('charge/person/area/notify/<int:pk>/', views.show_person_area_charge_notification_form,
         name='show_notification_person_area_charge_form'),
    path('charge/person/area/notify/send/<int:pk>/', views.send_notification_person_area_charge_to_user,
         name='send_notification_person_area_charge_to_user'),
    path('remove-send-notification-person-area/<int:pk>/', views.remove_send_notification_person_area,
         name='remove_send_notification_person_area'),


    path('add-person_area-fix-charge', views.PersonAreaFixChargeCreateView.as_view(),
         name='add_person_area_fix_charge'),
    path('fix/area/person/charge/edit/<int:pk>/', views.person_area_fix_charge_edit,
         name='charge_area_person_fix_edit'),
    path('fix/area/person/charge/delete/<int:pk>/', views.person_area_fix_delete, name='charge_area_person_fix_delete'),
    path('charge/fix/person/area/notify/<int:pk>/', views.show_fix_person_area_charge_notification_form,
         name='show_notification_fix_person_area_charge_form'),
    path('charge/fix/person/area/notify/send/<int:pk>/', views.send_notification_fix_person_area_charge_to_user,
         name='send_notification_fix_person_area_charge_to_user'),
    path('remove-send-notification-fix-person-area/<int:pk>/', views.remove_send_notification_fix_person_area,
         name='remove_send_notification_fix_person_area'),

    path('add-variable-fix-charge', views.VariableFixChargeCreateView.as_view(), name='add_variable_fix_charge'),
    path('fix/variable/charge/edit/<int:pk>/', views.variable_fix_charge_edit, name='charge_variable_fix_edit'),
    path('variable/fix/charge/delete/<int:pk>/', views.variable_fix_charge_delete, name='charge_variable_fix_delete'),
    path('charge/fix/variable/middleCharge/notify/<int:pk>/', views.show_fix_variable_notification_form,
         name='show_notification_fix_variable_charge_form'),
    path('charge/fix/variable/middleCharge/notify/send/<int:pk>/', views.send_notification_fix_variable_to_user,
         name='send_notification_fix_variable_charge_to_user'),
    path('remove-send-notification-fix-variable-middleCharge/<int:pk>/', views.remove_send_notification_fix_variable,
         name='remove_send_notification_fix_variable_charge'),

    # Sms_Management
    path('sms/management/', views.SmsManagementView.as_view(), name='sms_management'),
    path('edit/sms/<int:pk>/', views.SmsUpdateView.as_view(), name='edit_sms'),
    path('sms-delete/<int:pk>/', views.sms_delete, name='delete_sms'),
    path('sms/send/form/<int:pk>/', views.show_send_sms_form, name='show_send_sms_form'),
    path('send-sms/<int:pk>/', views.send_sms, name='send_sms')
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
