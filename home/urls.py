from django.urls import path
from home import views

urlpatterns = [
    path('', views.index, name='home'),
    path('middle/login/', views.middle_login, name='login_middle'),
    path('test/', views.test_subdomain, name='test_subdomain'),
    ]