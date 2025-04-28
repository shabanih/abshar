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

    # Unit Urls
    path('add-unit', views.UnitRegisterView.as_view(), name='add_unit'),
    path('info-unit/<int:pk>/', views.UnitInfoView.as_view(), name='unit_info'),
    path('edit/unit/<int:pk>/', views.UnitUpdateView.as_view(), name='edit_unit'),
    path('delete/unit/<int:pk>/', views.unit_delete, name='delete_unit'),
    path('manage-unit', views.UnitListView.as_view(), name='manage_unit'),
    path('units/export/excel/', views.export_units_excel, name='export_units_excel'),
    path('units/export/pdf/', views.export_units_pdf, name='export_units_pdf'),


    # Expense Urls
    path('add-expense', views.ExpenseView.as_view(), name='add_expense'),
    path('expense/edit/<int:pk>/', views.ExpenseUpdateView.as_view(), name='expense_edit'),
    path('expense/delete/<int:pk>/', views.expense_delete, name='expense_delete'),
    path('expense/delete-document/', views.delete_expense_document, name='delete_expense_document'),

    path('add-category', views.ExpenseCategoryView.as_view(), name='add_category'),
    path('edit/category/<int:pk>/', views.ExpenseCategoryUpdate.as_view(), name='edit_category'),
    path('delete/category/<int:pk>/', views.category_delete, name='delete_category'),


]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
