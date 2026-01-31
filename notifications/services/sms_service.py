from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.db.models import Sum

from admin_panel import helper
from admin_panel.models import SmsCredit
from notifications.services.sms_calculator import calculate_sms_count
import re

class SmsServiceResult:
    def __init__(self, success, message, total_sms=0, total_price=0):
        self.success = success
        self.message = message
        self.total_sms = total_sms
        self.total_price = total_price



def normalize_mobile(mobile: str):
    if not mobile:
        return None

    mobile = str(mobile).strip().replace(' ', '').replace('-', '')

    if mobile.startswith('0098'):
        mobile = '0' + mobile[4:]
    elif mobile.startswith('98'):
        mobile = '0' + mobile[2:]
    elif re.fullmatch(r'9\d{9}', mobile):
        mobile = '0' + mobile

    if re.fullmatch(r'09\d{9}', mobile):
        return mobile

    return None

class SmsService:

    @staticmethod
    def send_for_unified_charges(
        *,
        user,
        unified_charges,
        charge_title: str,
        meta_callback=None
    ) -> SmsServiceResult:

        receivers = []

        for uc in unified_charges:
            raw_mobile = uc.get_mobile()
            mobile = normalize_mobile(raw_mobile)

            if not mobile:
                continue

            renter = uc.unit.get_active_renter()
            name = (
                renter.renter_name
                if renter and renter.renter_name
                else uc.unit.owner_name
                or "مشتری"
            )

            receivers.append({
                'mobile': mobile,
                'name': name
            })

        if not receivers:
            return SmsServiceResult(False, 'شماره موبایل معتبری یافت نشد')

        # چون پیامک template است → هر گیرنده = ۱ پیامک
        total_sms = len(receivers)

        sms_price = Decimal(str(settings.SMS_PRICE))
        total_price = total_sms * sms_price

        total_credit = SmsCredit.objects.filter(
            user=user,
            is_paid=True
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        if total_credit < total_price:
            return SmsServiceResult(
                False,
                'شارژ پیامکی کافی نیست',
                total_sms,
                total_price
            )

        with transaction.atomic():

            # کسر شارژ FIFO
            remaining = total_price
            credits = SmsCredit.objects.filter(
                user=user,
                is_paid=True,
                amount__gt=0
            ).order_by('created_at')

            for credit in credits:
                if remaining <= 0:
                    break

                used = min(credit.amount, remaining)
                credit.amount -= used
                remaining -= used
                credit.save()

            # ارسال پیامک
            for r in receivers:
                helper.send_notify_user_by_sms(
                    mobile=r['mobile'],
                    name=r['name'],
                    charge_title=charge_title         # ✅ فقط نام شارژ
                )

            if meta_callback:
                meta_callback(
                    total_sms=total_sms,
                    total_price=total_price
                )

        return SmsServiceResult(
            True,
            'ارسال پیامک با موفقیت انجام شد',
            total_sms,
            total_price
        )


