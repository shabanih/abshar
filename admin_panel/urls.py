from django.urls import path

from admin_panel import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('announcement/', views.AnnouncementView.as_view(), name='announcement'),
    path('edit/announcement/<int:pk>/', views.AnnouncementUpdateView.as_view(), name='edit_announcement'),
    path('announcement-delete/<int:pk>/', views.announcement_delete, name='delete_announcement'),
]
