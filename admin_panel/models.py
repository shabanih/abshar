from django.db import models

from user_app.models import User


# Create your models here.

class Announcement(models.Model):
    title = models.CharField(max_length=400, verbose_name='عنوان')
    slug = models.SlugField(db_index=True, default='', null=True, max_length=200, verbose_name='عنوان در url')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return self.title

