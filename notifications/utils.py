from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Notification

def send_ticket_notification(ticket, sender, receiver):
    notification = Notification.objects.create(
        user=receiver,
        ticket=ticket,
        title=f"تیکت جدید از {sender.username}",
        message=ticket.subject,
        link=f"/tickets/{ticket.id}/"
    )

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{receiver.id}",
        {
            "type": "notify",
            "data": {
                "title": notification.title,
                "message": notification.message,
                "link": notification.link,
            }
        }
    )
