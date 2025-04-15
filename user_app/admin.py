from django.contrib import admin

from user_app import models

# Register your models here.
admin.site.register(models.unitRegister)
admin.site.register(models.User)