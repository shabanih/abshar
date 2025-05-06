from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from admin_panel import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),

    # Announce urls
    path('announcement/', views.AnnouncementView.as_view(), name='announcement'),
    path('edit/announcement/<int:pk>/', views.AnnouncementUpdateView.as_view(), name='edit_announcement'),
    path('announcement-delete/<int:pk>/', views.announcement_delete, name='delete_announcement'),

    # House Urls
    path('manage-house', views.AddMyHouseView.as_view(), name='manage_house'),
    path('delete/bank/<int:pk>/', views.bank_delete, name='delete_bank'),
    path('delete/house/<int:pk>/', views.house_delete, name='delete_house'),
    path('bank/edit/<int:pk>/', views.edit_bank, name='edit_bank'),
    path('house/edit/<int:pk>/', views.edit_house, name='edit_house'),

    # Unit Urls
    path('add-unit', views.UnitRegisterView.as_view(), name='add_unit'),
    path('info-unit/<int:pk>/', views.UnitInfoView.as_view(), name='unit_info'),
    path('edit/unit/<int:pk>/', views.UnitUpdateView.as_view(), name='edit_unit'),
    path('delete/unit/<int:pk>/', views.unit_delete, name='delete_unit'),
    path('manage-unit', views.UnitListView.as_view(), name='manage_unit'),
    path('units/export/excel/', views.export_units_excel, name='export_units_excel'),
    path('units/export/pdf/', views.export_units_pdf, name='export_units_pdf'),
    path('expense/export/excel/', views.export_expense_excel, name='export_expense_excel'),

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

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
