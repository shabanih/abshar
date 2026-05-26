from django.urls import path
from . import views

urlpatterns = [
    path('create/poll/', views.create_poll, name='create_poll'),
    path('poll-list', views.PollListView.as_view(), name='poll_list'),
    path('poll-edit/<int:poll_id>/', views.edit_poll, name='edit_poll'),
    path('poll-detaild/<int:poll_id>/', views.poll_detail, name='poll_detail'),
    path('delete-poll/<int:poll_id>/', views.delete_poll, name='delete_poll'),
    path('polls-list-pdf', views.polls_list_pdf, name='polls_list_pdf'),
]
