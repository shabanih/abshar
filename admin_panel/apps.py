from django.apps import AppConfig

# admin_panel/apps.py
from django.apps import AppConfig


class AdminPanelConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin_panel'  # نام اپ شما

    def ready(self):
        # این خط بسیار مهم است و باید وجود داشته باشد
        # مسیر signals باید مطابق با ساختار پوشه شما باشد
        import admin_panel.signals
        print("AdminPanelConfig ready and signals imported.")  # برای دیباگ

