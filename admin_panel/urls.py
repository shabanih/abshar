from django.urls import path

from admin_panel import views

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard', views.login_page, name='dashboard'),
]