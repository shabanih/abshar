import uuid
from decimal import Decimal

import jdatetime
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.contenttypes.models import ContentType

from user_app.models import Bank
from admin_panel.models import BankFund


class BankTransactionService:

    @staticmethod
    @transaction.atomic
    def deposit(*, user, bank: Bank,unit, amount: Decimal, description: str,
                content_object=None, payment_date=None, payer_name=None,
                transaction_no=None, gateway="پرداخت الکترونیک", house=None, transfer_group_id=None):
        if amount <= 0:
            raise ValueError("Amount must be positive")

        # آپدیت موجودی
        bank.current_balance += amount
        bank.save(update_fields=['current_balance'])

        content_type = ContentType.objects.get_for_model(content_object or bank)

        # ثبت تراکنش
        return BankFund.objects.create(
            user=user,
            bank=bank,
            unit=unit,
            payer_name=payer_name,
            house=house or bank.house,
            amount=amount,
            payment_gateway=gateway,
            transaction_no=transaction_no,
            payment_date=payment_date,
            payment_description=description,
            transaction_type='deposit',
            content_type=content_type,
            object_id=(content_object.pk if content_object else bank.pk),
            balance_after=bank.current_balance,
            is_paid=True,
            transfer_group_id=transfer_group_id,
        )


    @staticmethod
    @transaction.atomic
    def withdraw(*, user, bank: Bank, unit, amount: Decimal, description: str,
                 content_object=None, payment_date=None, transaction_no=None, receiver_name=None,
                 gateway="پرداخت الکترونیک", house=None, transfer_group_id=None):

        if amount <= 0:
            raise ValueError("Amount must be positive")

        if bank.current_balance < amount:
            raise ValueError("Insufficient bank balance")

        # آپدیت موجودی
        bank.current_balance -= amount
        bank.save(update_fields=['current_balance'])

        content_type = ContentType.objects.get_for_model(content_object or bank)

        # ثبت تراکنش
        return BankFund.objects.create(
            user=user,
            bank=bank,
            unit=unit,
            house=house or bank.house,
            amount=amount,
            payment_gateway=gateway,
            transaction_no=transaction_no,
            payment_date=payment_date,
            payment_description=description,
            transaction_type='withdraw',
            content_type=content_type,
            object_id=(content_object.pk if content_object else bank.pk),
            balance_after=bank.current_balance,
            receiver_name=receiver_name,
            transfer_group_id=transfer_group_id,
            is_paid=True
        )

    @staticmethod
    @transaction.atomic
    def transfer(*, user, from_bank: Bank, to_bank: Bank, unit, amount: Decimal,
                 description: str, payment_date=None, transaction_no=None, content_object=None, transfer_group_id=None):

        if amount <= 0:
            raise ValueError("Amount must be positive")

        if from_bank.id == to_bank.id:
            raise ValueError("Banks cannot be the same")

        from_bank = Bank.objects.select_for_update().get(pk=from_bank.pk)
        to_bank = Bank.objects.select_for_update().get(pk=to_bank.pk)

        if from_bank.current_balance < amount:
            raise ValueError("Insufficient balance in source bank")

        group_id = uuid.uuid4()

        BankTransactionService.withdraw(
            user=user,
            bank=from_bank,
            unit=unit,
            amount=amount,
            transaction_no=transaction_no,
            description=f"انتقال به {to_bank.bank_name} - {description}",
            payment_date=payment_date,
            content_object=content_object,
            transfer_group_id=group_id,
            # object_id=content_object.pk,
        )

        BankTransactionService.deposit(
            user=user,
            bank=to_bank,
            unit=unit,
            amount=amount,
            transaction_no=transaction_no,
            description=f"دریافت از {from_bank.bank_name} - {description}",
            payment_date=payment_date,
            content_object=content_object,
            transfer_group_id=group_id,
            # object_id=content_object.pk,
        )

        return True


def validate_bank_transaction_date(bank, payment_date):
    """
    جلوگیری از ثبت تراکنش قبل از تاریخ افتتاح حساب
    """

    if not bank or not payment_date:
        return

    opening_date = bank.create_at.date()

    if payment_date < opening_date:
        opening_date_jalali = jdatetime.date.fromgregorian(date=opening_date)

        raise ValidationError(
            f'تاریخ تراکنش نمی‌تواند قبل از تاریخ افتتاح حساب '
            f'({opening_date_jalali.strftime("%Y/%m/%d")}) باشد.'
        )