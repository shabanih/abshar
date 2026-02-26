from django.db import models


class SliderText(models.Model):
    title = models.CharField(max_length=500)
    title2 = models.CharField(max_length=500)
    text = models.TextField(max_length=1000)
    created = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title