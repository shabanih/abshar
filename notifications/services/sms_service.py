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

    mobile = re.sub(r"[ -]", "", str(mobile))

    if mobile.startswith("0098"):
        mobile = "0" + mobile[4:]
    elif mobile.startswith("98"):
        mobile = "0" + mobile[2:]
    elif re.fullmatch(r"9\d{9}", mobile):
        mobile = "0" + mobile

    return mobile if re.fullmatch(r"09\d{9}", mobile) else None


class SmsService:

    @staticmethod
    def send_for_unified_charges(*, user, unified_charges, meta_callback=None):

        receivers = []

        for uc in unified_charges:
            mobile = normalize_mobile(uc.get_mobile())
            if not mobile:
                continue

            renter = uc.unit.get_active_renter()

            name = (
                renter.renter_name
                if renter and renter.renter_name
                else uc.unit.owner_name or "مشتری"
            )

            # هر واحد مبلغ خودش را دارد
            amount = uc.total_charge_month

            receivers.append((mobile, name, amount))

        if not receivers:
            return SmsServiceResult(False, "شماره موبایل معتبری یافت نشد")

        total_sms = len(receivers)
        sms_price = Decimal(settings.SMS_PRICE)
        total_price = total_sms * sms_price

        total_credit = (
                SmsCredit.objects
                .filter(user=user, is_paid=True)
                .aggregate(total=Sum("amount"))["total"] or Decimal("0")
        )

        if total_credit < total_price:
            return SmsServiceResult(False, "شارژ پیامکی کافی نیست", total_sms, total_price)

        with transaction.atomic():

            # کسر شارژ
            remaining = total_price
            for credit in SmsCredit.objects.filter(
                    user=user, is_paid=True, amount__gt=0
            ).order_by("created_at"):

                if remaining <= 0:
                    break

                used = min(credit.amount, remaining)
                credit.amount -= used
                credit.save()

                remaining -= used

            # ارسال پیامک برای هر واحد با مبلغ خودش
            for mobile, name, amount in receivers:
                helper.send_notify_user_by_sms(
                    mobile=mobile,
                    name=name,
                    amount=amount
                )

            if meta_callback:
                meta_callback(total_sms=total_sms, total_price=total_price)

        return SmsServiceResult(True, "ارسال پیامک موفق", total_sms, total_price)

