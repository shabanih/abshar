from decimal import Decimal
from django.db import transaction
from django.contrib.auth import update_session_auth_hash

from admin_panel.models import Fund
from user_app.models import User, Renter, MyHouse


class UnitUpdateService:
    def __init__(self, *, unit, form, request):
        self.unit = unit
        self.form = form
        self.request = request

    # def execute(self):
    #     with transaction.atomic():
    #         owner_changed = self._check_owner_changed()
    #         if owner_changed:
    #             self._deactivate_renters()
    #             # آپدیت مالک در واحد
    #             self.unit.owner_name = self.form.cleaned_data.get('owner_name')
    #             self.unit.owner_mobile = self.form.cleaned_data.get('owner_mobile')
    #             self.unit.save(update_fields=['owner_name', 'owner_mobile'])
    #
    #         self._update_user(owner_changed)
    #         self._update_unit()
    #
    #         if self.unit.is_renter:
    #             self._update_or_create_renter()
    #
    #         self._handle_renter_charge()
    #         self._handle_owner_charge()
    #         self._update_people_count()
    def execute(self):
        with transaction.atomic():
            # ست کردن خانه (myhouse) اگر خالی باشد
            if not self.unit.myhouse:
                self.unit.myhouse = MyHouse.objects.filter(user=self.request.user, is_active=True).first()

            owner_changed = self._check_owner_changed()
            if owner_changed:
                self._deactivate_renters()
                self.unit.owner_name = self.form.cleaned_data.get('owner_name')
                self.unit.owner_mobile = self.form.cleaned_data.get('owner_mobile')
                self.unit.save(update_fields=['owner_name', 'owner_mobile'])

            self._update_user(owner_changed)
            self._update_unit()
            if self.unit.is_renter:
                self._update_or_create_renter()
            self._handle_renter_charge()
            self._handle_owner_charge()
            self._update_people_count()

            # # اضافه کردن مالک و مستاجر فعال به residents
            # if self.unit.user and self.unit.myhouse and self.unit.user not in self.unit.myhouse.residents.all():
            #     self.unit.myhouse.residents.add(self.unit.user)
            #
            # renter = self.unit.get_active_renter()
            # if renter and renter.user not in self.unit.myhouse.residents.all():
            #     self.unit.myhouse.residents.add(renter.user)

    # ------------------------------

    def _check_owner_changed(self):
        return (
            self.unit.owner_name != self.form.cleaned_data.get('owner_name') or
            self.unit.owner_mobile != self.form.cleaned_data.get('owner_mobile')
        )

    def _deactivate_renters(self):
        self.unit.renters.filter(renter_is_active=True).update(renter_is_active=False)

    def _update_user(self, owner_changed):
        # آپدیت مالک یا مستاجر فعال بسته به owner_changed
        if owner_changed or not self.unit.get_active_renter():
            user = self.unit.user
            mobile = self.form.cleaned_data.get('owner_mobile')
            name = self.form.cleaned_data.get('owner_name')
            field = 'mobile'
        else:
            renter = self.unit.get_active_renter()
            user = renter.user
            mobile = self.form.cleaned_data.get('renter_mobile')
            name = self.form.cleaned_data.get('renter_name')
            field = 'renter_mobile'

        if mobile and mobile != user.mobile:
            if User.objects.filter(mobile=mobile).exclude(pk=user.pk).exists():
                self.form.add_error(field, 'این شماره موبایل قبلاً ثبت شده است.')
                raise ValueError('duplicate_mobile')
            user.mobile = mobile
            user.username = mobile

        if name:
            user.full_name = name

        password = self.form.cleaned_data.get('password')
        if password:
            user.set_password(password)

        user.save()
        if password and user.pk == self.request.user.pk:
            update_session_auth_hash(self.request, user)

    def _update_unit(self):
        self.unit.is_renter = self.form.cleaned_data.get('is_renter', False)
        self.unit.owner_bank = self.form.cleaned_data.get('owner_bank')
        self.unit.save(update_fields=['is_renter', 'owner_bank'])

    def _update_or_create_renter(self):
        active_renter = self.unit.get_active_renter()
        renter_mobile = self.form.cleaned_data.get('renter_mobile')

        if active_renter:
            r = active_renter
        else:
            renter_user, created = User.objects.get_or_create(
                mobile=renter_mobile,
                defaults={
                    'username': renter_mobile,
                    'full_name': self.form.cleaned_data.get('renter_name'),
                    'is_active': True,
                    'manager': self.request.user,
                }
            )
            if not created and renter_user.manager is None:
                renter_user.manager = self.request.user
                renter_user.save(update_fields=['manager'])

            r = Renter.objects.filter(unit=self.unit, user=renter_user).first()
            if not r:
                r = Renter(unit=self.unit, user=renter_user)

        r.renter_name = self.form.cleaned_data.get('renter_name')
        r.renter_mobile = renter_mobile
        r.renter_national_code = self.form.cleaned_data.get('renter_national_code')
        r.renter_people_count = self.form.cleaned_data.get('renter_people_count')
        r.start_date = self.form.cleaned_data.get('start_date')
        r.end_date = self.form.cleaned_data.get('end_date')
        r.contract_number = self.form.cleaned_data.get('contract_number')
        r.estate_name = self.form.cleaned_data.get('estate_name')
        r.renter_details = self.form.cleaned_data.get('renter_details')
        r.first_charge_renter = self.form.cleaned_data.get('first_charge_renter') or 0
        r.renter_payment_date = self.form.cleaned_data.get('renter_payment_date')
        r.renter_transaction_no = self.form.cleaned_data.get('renter_transaction_no')
        r.renter_is_active = True
        r.renter_bank = self.form.cleaned_data.get('renter_bank')
        r.save()

    def _handle_renter_charge(self):
        renter = self.unit.get_active_renter()
        amount = Decimal(self.form.cleaned_data.get('first_charge_renter') or 0)
        if not renter or amount <= 0:
            return
        Fund.objects.update_or_create(
            unit=self.unit,
            user=renter.user,
            payment_description='شارژ اولیه مستاجر',
            is_initial=True,
            defaults={
                'bank': self.form.cleaned_data.get('renter_bank'),
                'debtor_amount': amount,
                'creditor_amount': 0,
                'amount': amount,
                'payment_date': self.form.cleaned_data.get('renter_payment_date'),
                'payer_name': self.unit.get_label(),
                'payment_gateway': 'پرداخت الکترونیک',
                'transaction_no': self.form.cleaned_data.get('renter_transaction_no'),
                'content_object': self.unit,
            }
        )

    def _handle_owner_charge(self):
        amount = Decimal(self.form.cleaned_data.get('first_charge_owner') or 0)
        if amount <= 0:
            return
        Fund.objects.update_or_create(
            unit=self.unit,
            user=self.unit.user,
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


# =======================================================

