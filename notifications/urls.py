from django.urls import path
from . import views

urlpatterns = [
    path('support-ticket/', views.SupportUserCreateView.as_view(), name='user_support_ticket'),
    path('myTicket/', views.TicketsView.as_view(), name='tickets'),
    path('tiket/details/<int:pk>/', views.user_ticket_detail, name='ticket_detail'),
    path('ticket/close/<int:pk>/', views.close_ticket, name='close_ticket'),

    path('middle/tickets/', views.MiddleTicketsView.as_view(), name='middle_tickets'),

    path('middle-ticket/<int:pk>/', views.middleAdmin_ticket_detail, name='middleAdmin_ticket_detail'),
    path('middle/ticket/close/<int:pk>/', views.middle_close_ticket, name='middle_close_ticket'),
    path('middle/ticket/open/<int:pk>/', views.middle_open_ticket, name='middle_open_ticket'),
    path('middle/ticket/waiting/<int:pk>/', views.middle_is_waiting, name='middle_waiting_ticket'),
    path('middle/ticket/continue/<int:pk>/', views.middle_is_continue, name='middle_continue_ticket'),

    # path('ticket-counter/user/', views.ticket_counter_user, name='ticket_counter_user'),
    # path('reset-ticket-counter-user/<int:ticket_id>/', views.reset_ticket_counter_user,
    #      name='reset_ticket_counter_user'),
    #
    # path('ticket-counter/admin/', views.ticket_counter_admin, name='ticket_counter_admin'),
    # path('reset-ticket-counter-admin/<int:ticket_id>/', views.reset_ticket_counter_admin,
    #      name='reset_ticket_counter_admin'),

    # admin/middleAdmin
    path('create/MiddleAdmin/ticket/', views.MiddleAdminTicketCreateView.as_view(), name='middleAdmin_support_ticket'),
    path('list/MiddleAdmin/ticket/', views.MiddleAdminTicketsView.as_view(), name='middleAdmin_tickets'),
    path('update/MiddleAdmin/ticket/<int:pk>/', views.MiddleAdmin_ticket_detail, name='MAdmin_ticket_detail'),
    path('middleAdmin/ticket/close/<int:pk>/', views.middlAdmin_close_ticket, name='middleAdmin_close_ticket'),

    path('admin/tickets/', views.AdminTicketsView.as_view(), name='admin_tickets'),
    path('admin-ticket/<int:pk>/', views.admin_ticket_detail, name='admin_ticket_detail'),

    path('admin/ticket/close/<int:pk>/', views.admin_close_ticket, name='admin_close_ticket'),
    path('admin/ticket/open/<int:pk>/', views.admin_open_ticket, name='admin_open_ticket'),
    path('admin/ticket/waiting/<int:pk>/', views.admin_is_waiting, name='admin_waiting_ticket'),
    path('admin/ticket/continue/<int:pk>/', views.admin_is_continue, name='admin_continue_ticket'),

    path('message/to/user/', views.MessageToUserListCreateView.as_view(), name='message_to_user'),
    path('edit/message/to/user/<int:pk>/', views.MiddleMessageUpdateView.as_view(), name='edit_message_to_user'),
    path('message-to-user-delete/<int:pk>/', views.message_user_delete, name='delete_message_to_user'),
    path('message-to-user-list-delete/<int:pk>/', views.message_user_delete_list, name='delete_message_to_user_list'),
    path('middle/message/send/form/<int:pk>/', views.middle_show_message_form, name='middle_show_message_form'),
    path('middle-send-message/<int:pk>/', views.middle_send_message, name='middle_send_message'),
    path('middle/message/management/', views.MiddleMessageToUserListView.as_view(), name='middle_message_management'),

    path('message//admin/to/middle/', views.AdminMessageToMiddleListCreateView.as_view(), name='message_admin_to_middle'),
    path('edit/message/admin/to/middle/<int:pk>/', views.AdminMessageToMiddleUpdateView.as_view(),
         name='edit_message_admin_to_middle'),
    path('message-admin-to-middle-delete/<int:pk>/', views.admin_message_delete, name='delete_message_admin_to_middle'),
    path('admin/message/send/form/<int:pk>/', views.admin_show_send_form, name='admin_show_message_form'),
    path('admin-send-message/<int:pk>/', views.admin_send_message, name='admin_send_message'),
    path('admin/message/management/', views.AdminMessageToMiddleListView.as_view(), name='admin_message_management'),
    path('middle/message//from/adminmanagement/', views.MiddleMessageListView.as_view(),
         name='middle_message_management_from_admin'),


]
