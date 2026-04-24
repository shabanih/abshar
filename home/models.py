import os
import uuid

from ckeditor_uploader.fields import RichTextUploadingField
from django.db import models


class SliderText(models.Model):
    title = models.CharField(max_length=500)
    title2 = models.CharField(max_length=500)
    text = models.TextField(max_length=1000)
    created = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class FreeRequest(models.Model):
    name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=11)
    is_call = models.BooleanField(default=False)
    consultant_date = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ContactUs(models.Model):
    name = models.CharField(max_length=100, null=False, blank=False, verbose_name="نام")
    subject = models.CharField(max_length=200, null=False, blank=False, verbose_name="موضوع")
    mobile = models.CharField(max_length=100, null=False, blank=False, verbose_name="")
    message = models.TextField(max_length=360, verbose_name="پیام")
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")

    def __str__(self):
        return self.name


def article_image_path(instance, filename):
    # Get extension (jpg, png, etc.)
    ext = filename.split('.')[-1]
    # Create custom filename: articles_<random_id>.<ext>
    new_filename = f"articles_{uuid.uuid4().hex[:6]}.{ext}"
    return os.path.join('articles', new_filename)


class Articles(models.Model):
    title = models.CharField(max_length=100, null=True, blank=True)
    short_description = models.TextField(null=True, blank=True)
    description = RichTextUploadingField(null=True, blank=True)  # ⬅ـ تغییر
    image = models.ImageField(upload_to=article_image_path, null=True, blank=True)
    # template_name = models.CharField(max_length=100, null=True, blank=True)
    keywords = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title