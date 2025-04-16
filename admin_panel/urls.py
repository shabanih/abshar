from django.urls import path

from admin_panel import views

urlpatterns = [
    path('', views.index, name='index'),
    path('mobile-login', views.mobile_login, name='mobile_login'),
]