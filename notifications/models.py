import os
import random

from ckeditor_uploader.fields import RichTextUploadingField
from django.db import models

from user_app.models import User


def generate_ticket_no():
    """Generate a unique 8-digit ticket number."""
    while True:
        number = random.randint(10000000, 99999999)
        if not SupportUser.objects.filter(ticket_no=number).exists():
            return number


class SupportUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=200, null=True, blank=True, verbose_name='عنوان')
    ticket_no = models.PositiveIntegerField(unique=True, editable=False, default=generate_ticket_no)
    message = RichTextUploadingField()
    answer_message = RichTextUploadingField(null=True, blank=True)
    is_sent = models.BooleanField(default=False, verbose_name='')
    is_read = models.BooleanField(default=False, verbose_name='')
    is_call = models.BooleanField(default=False, verbose_name='تماس گرفته شده')
    is_closed = models.BooleanField(default=False, verbose_name='فعال')
    is_answer = models.BooleanField(default=False, verbose_name='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.user)

    def delete(self, *args, **kwargs):
        for f in self.files.all():
            try:
                f.delete()
            except:
                pass
        super().delete(*args, **kwargs)


class SupportFile(models.Model):
    support_user = models.ForeignKey(SupportUser, on_delete=models.CASCADE, related_name='files')
    file = models.ImageField(upload_to='support_files/', null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.support_user.user.username} - {self.file.name}"

    def delete(self, *args, **kwargs):
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)


class SupportMessage(models.Model):
    support_user = models.ForeignKey(SupportUser, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = RichTextUploadingField()
    attachments = models.ManyToManyField(SupportFile, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)  # ← اضافه کردن این خط

    def sender_role(self):
        if self.sender.is_superuser:
            return "ادمین"
        elif self.sender.is_middle_admin:
            return "مدیر ساختمان"
        else:
            return "کاربر"

    def __str__(self):
        return ""


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    ticket = models.ForeignKey(SupportUser, null=True, blank=True, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=255, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    def mark_as_read(self):
        self.is_read = True
        self.save()


# =================================================

class AdminTicket(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="admin_ticket_creator")
    subject = models.CharField(max_length=200, null=True, blank=True, verbose_name='عنوان')
    middle_admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets"
    )

    ticket_no = models.PositiveIntegerField(unique=True, editable=False, default=generate_ticket_no)
    message = RichTextUploadingField()
    answer_message = RichTextUploadingField(null=True, blank=True)
    is_sent = models.BooleanField(default=False, verbose_name='')
    is_read = models.BooleanField(default=False, verbose_name='')
    is_call = models.BooleanField(default=False, verbose_name='تماس گرفته شده')
    is_closed = models.BooleanField(default=False, verbose_name='فعال')
    is_answer = models.BooleanField(default=False, verbose_name='')
    is_waiting = models.BooleanField(default=False, verbose_name='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ticket_no} - {self.user.id}"


class AdminTicketFile(models.Model):
    ticket = models.ForeignKey(AdminTicket, on_delete=models.CASCADE, related_name='files_ticket')
    file = models.FileField(upload_to='admin_ticket_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name


class AdminTicketMessage(models.Model):
    ticket = models.ForeignKey('AdminTicket', on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_ticket_sender')
    message = RichTextUploadingField()
    attachments = models.ManyToManyField(AdminTicketFile, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender} - {self.ticket}"

    def sender_role(self):
        if self.sender.is_superuser:
            return "ادمین"
        elif self.sender.is_middle_admin:
            return "مدیر ساختمان"
        else:
            return "کاربر"


class MiddleAdminNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='middleAdmin_notifications')
    ticket = models.ForeignKey(AdminTicket, null=True, blank=True, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=255, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    def mark_as_read(self):
        self.is_read = True
        self.save()
