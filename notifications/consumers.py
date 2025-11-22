import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer

from notifications.models import SupportMessage, AdminTicketMessage


class TicketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return

        self.group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # ارسال شمارنده اولیه
        await self.send_count()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # فعلاً نیازی به دریافت پیام از کلاینت نداریم
        pass

    async def send_ticket_count(self, event):
        await self.send_count()

    async def send_count(self):
        count = await self.get_unread_count()
        await self.send(text_data=json.dumps({"count": count}))

    @database_sync_to_async
    def get_unread_count(self):
        if self.user.is_middle_admin:
            # فقط پیام‌های کاربران تحت مدیریت این مدیر
            return SupportMessage.objects.filter(
                support_user__user__manager=self.user,  # کاربرانی که مدیرشان این مدیر است
                sender__is_middle_admin=False,  # فقط پیام‌های کاربران
                is_read=False
            ).count()
        else:
            # پیام‌های مدیر برای کاربر
            return SupportMessage.objects.filter(
                support_user__user=self.user,
                sender__is_middle_admin=True,
                is_read=False
            ).count()


# class AdminTicketConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.user = self.scope["user"]
#
#         if not self.user.is_authenticated:
#             await self.close()
#             return
#
#         # فقط ادمین‌ها و مدیران میانی اجازه اتصال دارند
#         if not (self.user.is_superuser or self.user.is_middle_admin):
#             await self.close()
#             return
#
#         # گروه‌بندی برای WebSocket
#         if self.user.is_middle_admin:
#             # هر مدیر میانی گروه خودش را دارد
#             self.group_name = f"middle_admin_group_{self.user.id}"
#         else:
#             # ادمین‌ها در یک گروه مشترک هستند
#             self.group_name = "admins_group"
#
#         await self.channel_layer.group_add(self.group_name, self.channel_name)
#         await self.accept()
#
#         # ارسال تعداد پیام‌های خوانده نشده
#         await self.send_count()
#
#     async def disconnect(self, close_code):
#         await self.channel_layer.group_discard(self.group_name, self.channel_name)
#
#     async def receive(self, text_data):
#         # فعلاً نیازی به دریافت پیام از کلاینت نیست
#         pass
#
#     # فراخوانی از view برای آپدیت آنی
#     async def send_admin_ticket_count(self, event):
#         await self.send_count()
#
#     async def send_count(self):
#         count = await self.get_unread_count()
#         await self.send(text_data=json.dumps({"count": count}))
#
#     @database_sync_to_async
#     def get_unread_count(self):
#         # اگر مدیر میانی است → پیام‌های خوانده‌نشده از ادمین
#         if self.user.is_middle_admin:
#             return AdminTicketMessage.objects.filter(
#                 support_ma__middle_admin=self.user,  # فقط پیام‌های مرتبط با این مدیر
#                 sender__is_superuser=True,
#                 is_read=False
#             ).count()
#
#         # اگر ادمین است → پیام‌های خوانده‌نشده از تمام مدیران میانی
#         if self.user.is_superuser:
#             return AdminTicketMessage.objects.filter(
#                 sender__is_middle_admin=True,
#                 is_read=False
#             ).count()
#
#         return 0

class AdminTicketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        # فقط ادمین و مدیر میانی
        if not (self.user.is_superuser or self.user.is_middle_admin):
            await self.close()
            return

        if self.user.is_superuser:
            self.group_name = "admins_group"

        elif self.user.is_middle_admin:
            self.group_name = f"middle_admin_group_{self.user.id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.send_count()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_admin_ticket_count(self, event):
        await self.send_count()

    async def send_count(self):
        count = await self.get_unread_count()
        await self.send(text_data=json.dumps({"count": count}))

    @database_sync_to_async
    def get_unread_count(self):

        # مدیر میانی ← پیام unread از ادمین
        if self.user.is_middle_admin:
            count = AdminTicketMessage.objects.filter(
                ticket__middle_admin=self.user,
                sender__is_superuser=True,
                is_read=False
            ).count()
            print(f"Unread count for middle admin {self.user.id}: {count}")
            return count

        # ادمین ← پیام unread از مدیر میانی
        if self.user.is_superuser:
            return AdminTicketMessage.objects.filter(
                sender__is_middle_admin=True,
                is_read=False
            ).count()

        return 0


# class AdminTicketConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.user = self.scope["user"]
#
#         if not self.user.is_authenticated:
#             await self.close()
#             return
#
#         # ✔ ادمین و مدیر میانی هر دو باید بتوانند وصل شوند
#         if not (self.user.is_superuser or self.user.is_middle_admin):
#             await self.close()
#             return
#
#         # گروه‌بندی:
#         # مدیرهای میانی گروه مخصوص خود دارند
#         # ادمین‌ها همه در یک گروه هستند
#         if self.user.is_middle_admin:
#             self.group_name = f"middle_admin_group_{self.user.id}"
#         else:
#             self.group_name = "admins_group"
#
#         await self.channel_layer.group_add(self.group_name, self.channel_name)
#         await self.accept()
#
#         # ارسال تعداد پیام‌های خوانده نشده
#         await self.send_count()
#
#     async def disconnect(self, close_code):
#         await self.channel_layer.group_discard(self.group_name, self.channel_name)
#
#     async def receive(self, text_data):
#         pass  # فعلاً نیازی نداریم
#
#     # فراخوانی از view برای آپدیت آنی
#     async def send_admin_ticket_count(self, event):
#         await self.send_count()
#
#     async def send_count(self):
#         count = await self.get_unread_count()
#         await self.send(text_data=json.dumps({"count": count}))
#
#     @database_sync_to_async
#     def get_unread_count(self):
#
#         # اگر مدیر میانی است → پیام‌های خوانده‌نشده از ادمین را بگیرد
#         if self.user.is_middle_admin:
#             return AdminTicketMessage.objects.filter(
#                 support_ma__middle_admin=self.user,
#                 sender__is_superuser=True,
#                 is_read=False
#             ).count()
#
#         # اگر ادمین است → پیام‌های خوانده‌نشده از مدیر میانی را بگیرد
#         if self.user.is_superuser:
#             return AdminTicketMessage.objects.filter(
#                 sender__is_middle_admin=True,
#                 is_read=False
#             ).count()
#
#         return 0
