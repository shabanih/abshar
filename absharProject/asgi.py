import os
import django

# 1️⃣ تنظیم environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'absharProject.settings')

# 2️⃣ setup Django قبل از هر import
django.setup()

# 3️⃣ حالا می‌توانید import کنید
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import notifications.routing  # اینجا safe است
from django.core.asgi import get_asgi_application

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            notifications.routing.websocket_urlpatterns
        )
    ),
})
