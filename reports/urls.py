from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from reports import views

urlpatterns = [
    path('fund/turnover', views.fund_middle_turnover, name='fund_turn_over'),
    path('tarakonesh', views.fund_turnover_user, name='fund_turn_over_user'),
    path('units/fund/', views.UnitReportsTurnOver.as_view(), name='unit_reports'),
    path('debtor/units/report/', views.debtor_units_report, name='debtor_units_report'),
    path('history/unit/report/', views.HistoryUnitReports.as_view(), name='unit_history_report'),
    path('history/expense/', views.ReportExpenseView.as_view(), name='expense_history_report'),
    path('history/income/', views.ReportIncomeView.as_view(), name='income_history_report'),
    path('history/property/', views.ReportPropertyView.as_view(), name='property_history_report'),
    path('history/maintenance/', views.ReportMaintenanceView.as_view(), name='maintenance_history_report'),
    path('pay/receive/', views.PayReceiveReportView.as_view(), name='pay_receive_report'),

    path('middle-charge/report/pdf/', views.charge_units_list_report_pdf, name='charge_units_list_report_pdf'),
    path('middle-charge-report/excel/', views.charge_units_list_report_excel, name='charge_units_list_report_excel'),
    path(
        'middle-charge<int:charge_id>',
        views.charge_units_report_pdf,
        name='single_charge_invoice_report_pdf'
    ),
    path('charges/notify/list/', views.charge_notify_report_list, name='charge_notify_report_list'),

    path('report/export/excel/', views.export_units_report_excel, name='export_units_report_excel'),
    path('report/export/pdf/', views.export_units_report_pdf, name='export_units_report_pdf'),

    path('report/middle/export/excel/', views.export_middle_report_excel, name='export_middle_report_excel'),
    path('report/middle/export/pdf/', views.export_middle_report_pdf, name='export_middle_report_pdf'),

    path('report/user/export/excel/', views.export_user_report_excel, name='export_user_report_excel'),
    path('report/user/export/pdf/', views.export_user_report_pdf, name='export_user_report_pdf'),

    path('report/history/unit/export/excel/', views.export_unit_history_report_excel,
         name='export_history_unit_report_excel'),
    path('report/history/unit/export/pdf/', views.export_unit_history_report_pdf,
         name='export_history_unit_report_pdf'),
    path('report/expense/export/excel/', views.export_expense_report_excel, name='export_expense_report_excel'),
    path('report/expense/export/pdf/', views.export_expense_report_pdf, name='export_expense_report_pdf'),

    path('report/income/export/excel/', views.export_income_report_excel, name='export_income_report_excel'),
    path('report/income/export/pdf/', views.export_income_report_pdf, name='export_income_report_pdf'),

    path('report/property/export/excel/', views.export_property_report_excel, name='export_property_report_excel'),
    path('report/property/export/pdf/', views.export_property_report_pdf, name='export_property_report_pdf'),

    path('report/maintenance/export/excel/', views.export_maintenance_report_excel,
         name='export_maintenance_report_excel'),
    path('report/maintenance/export/pdf/', views.export_maintenance_report_pdf,
         name='export_maintenance_report_pdf'),

    path('report/pay/receive/export/excel/', views.export_pay_receive_report_excel,
         name='export_pay_receive_report_excel'),
    path('report/pay/receive/export/pdf/', views.export_pay_receive_report_pdf,
         name='export_pay_receive_report_pdf'),

    path('report/debtor/export/excel/', views.export_debtor_report_excel,
         name='export_debtor_report_excel'),
    path('report/debtor/export/pdf/', views.export_debtor_report_pdf,
         name='export_debtor_report_pdf'),

    path('report/balance/', views.house_balance_view, name='house_balance_view'),


    path('middleAdmin-fund', views.middleAdmin_turnover, name='middleAdmin_fund_turn_over'),
    path('report/middleFund/export/excel/', views.middleFund_report_excel, name='middle_report_excel'),
    path('report/middleFund/export/pdf/', views.middleFund_report_pdf, name='middle_report_pdf'),

    # admin Urls
    path('admin/fund/turnover', views.admin_fund_turnover, name='admin_fund_turn_over'),


]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
