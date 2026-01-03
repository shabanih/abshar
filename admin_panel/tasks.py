from celery import shared_task
from django.utils import timezone
from .models import UnifiedCharge


@shared_task(
    bind=True,
    name='admin_panel.tasks.calculate_daily_penalties',
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
)
def calculate_daily_penalties(self):
    today = timezone.now().date()

    qs = UnifiedCharge.objects.filter(
        is_paid=False,
        payment_deadline_date__lt=today,
        penalty_percent__gt=0
    )

    CHUNK_SIZE = 1000
    start = 0
    while True:
        chunk = qs[start:start + CHUNK_SIZE]
        if not chunk:
            break

        to_update = []
        for charge in chunk:
            base_total = charge.base_charge or 0
            percent = charge.penalty_percent or 0
            delay_days = (today - charge.payment_deadline_date).days

            new_penalty = int((base_total * percent / 100) * delay_days)

            if new_penalty != (charge.penalty_amount or 0):
                charge.penalty_amount = new_penalty
                charge.total_charge_month = base_total + new_penalty + (charge.other_cost_amount or 0) + (charge.civil or 0)
                to_update.append(charge)

        if to_update:
            UnifiedCharge.objects.bulk_update(to_update, ['penalty_amount', 'total_charge_month'], batch_size=500)

        start += CHUNK_SIZE

