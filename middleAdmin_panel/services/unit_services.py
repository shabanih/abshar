from decimal import Decimal
from django.db import transaction
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone

from admin_panel.models import Fund
from middleAdmin_panel.services.bank_services import BankTransactionService
from user_app.models import User, Renter, MyHouse


class UnitUpdateService:
    def __init__(self, *, unit, form, request):
        self.unit = unit
        self.form = form
        self.request = request

    def execute(self):
        with transaction.atomic():
            if not self.unit.myhouse:
                self.unit.myhouse = MyHouse.objects.filter(user=self.request.user, is_active=True).first()

            owner_changed = self._check_owner_changed()
            if owner_changed:
                self._deactivate_renters()
                self.unit.owner_name = self.form.cleaned_data.get('owner_name')
                self.unit.owner_mobile = self.form.cleaned_data.get('owner_mobile')
                self.unit.is_renter = False
                self.unit.save(update_fields=['owner_name', 'owner_mobile', 'is_renter'])

            self._update_owner_user()
            self._update_unit(owner_changed=owner_changed)

            # فقط وقتی مالک تغییر نکرده، مستاجر را به‌روزرسانی کن
            # if self.unit.is_renter and not owner_changed:
            #     self._update_or_create_renter()
            #     self._handle_renter_charge()

            if self.unit.is_renter and not owner_changed:
                self._update_or_create_renter()

            self._handle_owner_charge()
            self._handle_renter_charge()
            self._update_people_count()

    # ------------------------------

    def _check_owner_changed(self):
        old_unit = type(self.unit).objects.get(pk=self.unit.pk)
        print("OLD NAME:", old_unit.owner_name)
        print("NEW NAME:", self.form.cleaned_data.get('owner_name'))
        print("OLD MOBILE:", old_unit.owner_mobile)
        print("NEW MOBILE:", self.form.cleaned_data.get('owner_mobile'))

        old_name = (old_unit.owner_name or "").strip()
        new_name = (self.form.cleaned_data.get('owner_name') or "").strip()

        old_mobile = (old_unit.owner_mobile or "").strip()
        new_mobile = (self.form.cleaned_data.get('owner_mobile') or "").strip()

        return old_name != new_name or old_mobile != new_mobile

    def _deactivate_renters(self):
        self.unit.renters.filter(renter_is_active=True).update(renter_is_active=False)

    def _update_owner_user(self):
        user = self.unit.user

        new_mobile = self.form.cleaned_data.get('owner_mobile')
        new_name = self.form.cleaned_data.get('owner_name')

        # ----------------------------
        # CASE 1: موبایل تغییر نکرده
        # ----------------------------
        if new_mobile == user.mobile:
            if new_name and new_name != user.full_name:
                user.full_name = new_name
                user.save(update_fields=['full_name'])
            return  # 🚨 مهم: خروج کامل

        # ----------------------------
        # CASE 2: موبایل تغییر کرده
        # ----------------------------
        if User.objects.filter(mobile=new_mobile).exclude(pk=user.pk).exists():
            self.form.add_error('owner_mobile', 'این شماره موبایل قبلاً ثبت شده است.')
            raise ValueError('duplicate_mobile')

        user.mobile = new_mobile
        user.full_name = new_name
        user.save()

    # def _update_unit(self):
    #     self.unit.is_renter = self.form.cleaned_data.get('is_renter', False)
    #     self.unit.owner_bank = self.form.cleaned_data.get('owner_bank')
    #     self.unit.save(update_fields=['is_renter', 'owner_bank'])

    def _update_unit(self, owner_changed=False):
        if not owner_changed:
            # فقط وقتی مالک تغییر نکرده، مقدار فرم را اعمال کن
            self.unit.is_renter = self.form.cleaned_data.get('is_renter')
        self.unit.owner_bank = self.form.cleaned_data.get('owner_bank')
        self.unit.save(update_fields=['is_renter', 'owner_bank'])

    def _update_or_create_renter(self):
        renter_mobile = self.form.cleaned_data.get('renter_mobile')
        renter_name = self.form.cleaned_data.get('renter_name')

        if not renter_mobile:
            return

        active_renter = self.unit.get_active_renter()

        # ----------------------------
        # اگر مستاجر فعلی وجود دارد
        # ----------------------------
        if active_renter:
            renter_user = active_renter.user

            # بررسی تغییر موبایل
            if renter_mobile != renter_user.mobile:
                existing_user = User.objects.filter(
                    mobile=renter_mobile
                ).exclude(pk=renter_user.pk).first()

                if existing_user:
                    self.form.add_error('renter_mobile', 'این شماره موبایل قبلاً ثبت شده است.')
                    raise ValueError('duplicate_mobile')

                renter_user.mobile = renter_mobile

            renter_user.full_name = renter_name
            renter_user.is_unit = True
            renter_user.manager = self.request.user
            renter_user.save()

            r = active_renter

        # ----------------------------
        # اگر مستاجر جدید است
        # ----------------------------
        else:
            renter_user = User.objects.filter(mobile=renter_mobile).first()

            if not renter_user:
                renter_user = User.objects.create(
                    mobile=renter_mobile,
                    username=f"user_{renter_mobile}",
                    full_name=renter_name,
                    is_active=True,
                    manager=self.request.user,
                    is_unit=True
                )

            r = Renter.objects.create(
                unit=self.unit,
                user=renter_user
            )

        # ----------------------------
        # آپدیت اطلاعات مستاجر
        # ----------------------------
        r.renter_name = renter_name
        r.renter_mobile = renter_mobile
        r.renter_national_code = self.form.cleaned_data.get('renter_national_code')
        r.renter_people_count = self.form.cleaned_data.get('renter_people_count')
        r.start_date = self.form.cleaned_data.get('start_date')
        r.end_date = self.form.cleaned_data.get('end_date')
        r.contract_number = self.form.cleaned_data.get('contract_number')
        r.estate_name = self.form.cleaned_data.get('estate_name')
        r.renter_is_active = True
        r.renter_bank = self.form.cleaned_data.get('renter_bank')

        r.save()

        # پسورد (اختیاری)
        renter_password = self.form.cleaned_data.get('renter_password')
        if renter_password:
            renter_user.set_password(renter_password)
            renter_user.save()

    def _handle_renter_charge(self):
        renter = self.unit.get_active_renter()
        amount = Decimal(self.form.cleaned_data.get('first_charge_renter') or 0)
        if not renter or amount <= 0:
            return
        Fund.objects.update_or_create(
            unit=self.unit,
            user=renter.user,
            house=renter.myhouse,
            payment_description='شارژ اولیه مستاجر',
            is_initial=True,
            defaults={
                'bank': self.form.cleaned_data.get('renter_bank'),
                'debtor_amount': amount,
                'creditor_amount': 0,
                'amount': amount,
                'payment_date': self.form.cleaned_data.get('renter_payment_date'),
                'payer_name': self.unit.get_label,
                'payment_gateway': 'پرداخت الکترونیک',
                'transaction_no': self.form.cleaned_data.get('renter_transaction_no'),
                'content_object': self.unit,
            }
        )
        BankTransactionService.deposit(
            user=self.request.user,
            bank=self.form.cleaned_data.get('renter_bank'),
            unit=self.unit,
            amount=Decimal(amount),
            description=f"شارژ اولیه مستاجر {self.unit.get_label}",
            content_object=self.unit,
            payment_date=self.form.cleaned_data.get('renter_payment_date'),
            transaction_no=self.form.cleaned_data.get('renter_transaction_no'),
            gateway="شارژ واحد",
            house=self.unit.myhouse
        )

    def _handle_owner_charge(self):
        amount = Decimal(self.form.cleaned_data.get('first_charge_owner') or 0)
        if amount <= 0:
            return
        Fund.objects.update_or_create(
            unit=self.unit,
            user=self.unit.user,
            house=self.unit.myhouse,
            payment_description='شارژ اولیه مالک',
            is_initial=True,
            defaults={
                'bank': self.form.cleaned_data.get('owner_bank'),
                'debtor_amount': amount,
                'creditor_amount': 0,
                'amount': amount,
                'payment_date': self.form.cleaned_data.get('owner_payment_date'),
                'payer_name': self.unit.get_unit(),
                'payment_gateway': 'پرداخت الکترونیک',
                'transaction_no': self.form.cleaned_data.get('owner_transaction_no'),
                'content_object': self.unit,
            }
        )
        BankTransactionService.deposit(
            user=self.request.user,
            unit=self.unit,
            bank=self.form.cleaned_data.get('owner_bank'),
            amount=Decimal(amount),
            description=f"شارژ اولیه مالک {self.unit.get_label}",
            content_object=self.unit,
            payment_date=self.form.cleaned_data.get('owner_payment_date'),
            transaction_no=self.form.cleaned_data.get('owner_transaction_no'),
            gateway="شارژ واحد",
            house=self.unit.myhouse
        )

    def _update_people_count(self):
        renter = self.unit.get_active_renter()

        if renter and renter.renter_people_count not in [None, '']:
            self.unit.people_count = int(renter.renter_people_count)
        else:
            try:
                self.unit.people_count = int(self.unit.owner_people_count)
            except (TypeError, ValueError):
                self.unit.people_count = 0

        self.unit.save(update_fields=['people_count'])


