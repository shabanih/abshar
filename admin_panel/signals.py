from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import date
from dateutil.relativedelta import relativedelta
from admin_panel.models import CivilManage, CivilInstallment


# @receiver(post_save, sender=CivilManage)
# def create_installments(sender, instance, created, **kwargs):
#     if created:
#         count = instance.installment_count
#         if count == 0:
#             return
#
#         # مبلغ قابل تقسیط (کل مبلغ - پیش‌پرداخت)
#         total = instance.amount - instance.prepayment
#         per_installment = total // count
#
#         # اگر first_due_date نداده بود، از امروز شروع کن
#         base_date = instance.first_due_date or date.today()
#
#         for i in range(1, count + 1):
#             due_date = base_date + relativedelta(months=i - 1)
#             CivilInstallment.objects.create(
#                 civil_manage=instance,
#                 installment_number=i,
#                 amount=per_installment,
#                 due_date=due_date
#             )
