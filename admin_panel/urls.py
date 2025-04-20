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
    path('edit/unit/<int:pk>/', views.UnitUpdateView.as_view(), name='edit_unit'),
    path('delete/unit/<int:pk>/', views.unit_delete, name='delete_unit'),
    path('manage-unit', views.unit_management, name='manage_unit'),

    # Renter Urls
    path('add-renter', views.RenterRegisterView.as_view(), name='add_renter'),
    path('edit/renter/<int:pk>/', views.RenterUpdateView.as_view(), name='edit_renter'),
    path('delete/renter/<int:pk>/', views.renter_delete, name='delete_renter'),


]
