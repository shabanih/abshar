from django.core.management.base import BaseCommand
from user_app.models import ChargeMethod

class Command(BaseCommand):
    help = "ایجاد رکوردهای پیش‌فرض روش‌های شارژ"

    def handle(self, *args, **options):
        defaults = [
            {'code': 1, 'name': 'شارژ ثابت'},
            {'code': 2, 'name': 'شارژ متراژی'},
            {'code': 3, 'name': 'شارژ نفری'},
            {'code': 4, 'name': 'شارژ واحدی متراژی'},
            {'code': 5, 'name': 'شارژ واحدی نفری'},
            {'code': 6, 'name': 'شارژ نفری متراژی'},
            {'code': 7, 'name': 'شارژ واحدی متراژی نفری'},
            {'code': 8, 'name': 'شارژ ثابت و متغیر'},
        ]

        for item in defaults:
            obj, created = ChargeMethod.objects.get_or_create(
                code=item['code'],
                defaults={'name': item['name'], 'is_active': True}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created: {obj.name}"))
            else:
                self.stdout.write(self.style.WARNING(f"Already exists: {obj.name}"))

        self.stdout.write(self.style.SUCCESS("Seed charge methods finished."))
