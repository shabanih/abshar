import json
import math
from decimal import Decimal

from ckeditor_uploader.fields import RichTextUploadingField
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from datetime import date

from user_app.models import Unit, User, Bank, MyHouse


class Announcement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    house = models.ForeignKey(MyHouse, on_delete=models.CASCADE)
    title = RichTextUploadingField(null=True, blank=True)
    show_in_marquee = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return self.title


class MessageToUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=400, null=True, blank=True)
    message = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    send_notification = models.BooleanField(default=False)
    send_notification_date = models.DateTimeField(null=True, blank=True)

    notified_units = models.ManyToManyField(
        Unit,
        related_name='notified_messages',
        blank=True
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title or str(self.id)


class MessageReadStatus(models.Model):
    message = models.ForeignKey(
        MessageToUser,
        on_delete=models.CASCADE,
        related_name='read_statuses'
    )
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('message', 'unit')

    def __str__(self):
        return f"{self.unit} - {self.message.title} - {'خوانده شده' if self.is_read else 'خوانده نشده'}"


# ------------------- Admin Message To MiddleAdmin --------------------------

class AdminMessageToMiddle(models.Model):
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='sent_admin_messages',
        limit_choices_to={'is_superuser': True},  # فقط ادمین اصلی
        verbose_name='فرستنده'
    )
    middleAdmins = models.ManyToManyField(
        User,
        related_name='received_admin_messages',
        verbose_name='مدیران ساختمان'
    )
    title = models.CharField(max_length=400, null=True, blank=True, verbose_name='عنوان پیام')
    message = models.TextField(null=True, blank=True, verbose_name='متن پیام')
    send_notification = models.BooleanField(default=False)
    send_notification_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال')

    def __str__(self):
        return self.title or f"پیام {self.id} از {self.sender.full_name}"


class MiddleMessageReadStatus(models.Model):
    message = models.ForeignKey(
        AdminMessageToMiddle,
        on_delete=models.CASCADE,
        related_name='read_statuses'
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE
    )
    is_read = models.BooleanField(default=False, verbose_name='خوانده شده')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان خواندن')

    class Meta:
        unique_together = ('message', 'user')

    def __str__(self):
        return f"{self.user.full_name} - {self.message.title} - {'خوانده شده' if self.is_read else 'خوانده نشده'}"


# -------------------- Expense View ------------------------
class ExpenseCategory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100, verbose_name='نام')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return self.title


class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='شماره حساب', null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True)
    house = models.ForeignKey(
        MyHouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='house_expenses',
        verbose_name='ساختمان مرتبط'
    )
    receiver_name = models.CharField(max_length=400, null=True, blank=True)

    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, verbose_name='گروه',
                                 related_name='expenses')
    date = models.DateField(verbose_name='تاریخ سند')
    doc_no = models.IntegerField(verbose_name='شماره سند')
    description = models.CharField(max_length=4000, verbose_name='شرح')
    amount = models.PositiveIntegerField(verbose_name='قیمت', null=True, blank=True, default=0)
    details = models.TextField(verbose_name='توضیحات', null=True, blank=True)
    is_paid = models.BooleanField(default=False, verbose_name='پرداخت شده/ نشده')
    transaction_reference = models.CharField(max_length=20, null=True, blank=True)
    payment_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاریخ پرداخت"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return str(self.doc_no)

    def get_image_urls_json(self):
        # Use the correct attribute to access the file URL in the related `ExpenseDocument` model
        image_urls = [doc.document.url for doc in self.documents.all() if doc.document]
        print(image_urls)
        return mark_safe(json.dumps(image_urls))


class ExpenseDocument(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='documents')
    document = models.FileField(upload_to='images/expense/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


# Income Modals ==============================================================
class IncomeCategory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100, verbose_name='نام')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return self.subject


class Income(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='شماره حساب', null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True)
    house = models.ForeignKey(
        MyHouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='house_incomes',
        verbose_name='ساختمان مرتبط'
    )
    payer_name = models.CharField(max_length=400, null=True, blank=True)
    category = models.ForeignKey(IncomeCategory, on_delete=models.CASCADE, verbose_name='گروه', related_name='incomes')
    doc_date = models.DateField(verbose_name='تاریخ سند')
    doc_number = models.IntegerField(verbose_name='شماره سند')
    description = models.CharField(max_length=4000, verbose_name='شرح')
    amount = models.PositiveIntegerField(verbose_name='قیمت', null=True, blank=True, default=0)
    details = models.TextField(verbose_name='توضیحات', null=True, blank=True)
    is_paid = models.BooleanField(default=False, verbose_name='پرداخت شده/ نشده')
    transaction_reference = models.CharField(max_length=20, null=True, blank=True)
    payment_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاریخ پرداخت"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return str(self.doc_number)

    def get_document_urls_json(self):
        # Use the correct attribute to access the file URL in the related `ExpenseDocument` model
        image_urls = [doc.document.url for doc in self.documents.all() if doc.document]

        return mark_safe(json.dumps(image_urls))


class IncomeDocument(models.Model):
    income = models.ForeignKey(Income, on_delete=models.CASCADE, related_name='documents')
    document = models.FileField(upload_to='images/income/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.income.category)


# ======================= Receive & Pay Modals ==========================
class ReceiveMoney(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='شماره حساب')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True)
    house = models.ForeignKey(
        MyHouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='house_receives',
        verbose_name='ساختمان مرتبط'
    )
    payer_name = models.CharField(max_length=400, null=True, blank=True)
    doc_date = models.DateField(verbose_name='تاریخ سند')
    doc_number = models.IntegerField(verbose_name='شماره سند')
    description = models.CharField(max_length=4000, verbose_name='شرح')
    amount = models.PositiveIntegerField(verbose_name='مبلغ', null=True, blank=True, default=0)
    details = models.TextField(verbose_name='توضیحات', null=True, blank=True)
    is_received_money = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False, verbose_name='پرداخت شده/ نشده')
    transaction_reference = models.CharField(max_length=20, null=True, blank=True, default=0)
    payment_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاریخ پرداخت"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return str(self.unit.unit)

    def save(self, *args, **kwargs):
        self.is_paid = bool(self.transaction_reference and self.payment_date)
        super().save(*args, **kwargs)

    def get_document_json(self):
        # Use the correct attribute to access the file URL in the related `ExpenseDocument` model
        image_urls = [doc.document.url for doc in self.documents.all() if doc.document]
        print(image_urls)
        return mark_safe(json.dumps(image_urls))

    def get_payer_display(self):
        if self.unit:
            renter = self.unit.get_active_renter()
            if renter and getattr(renter, 'renter_name', None):
                return f"واحد {self.unit.unit} - {renter.renter_name}"  # نام مستاجر
            elif self.unit.owner_name:
                return f"واحد {self.unit.unit} - {self.unit.owner_name}"  # نام مالک
            else:
                return f"واحد {self.unit.unit}"  # fallback امن
        else:
            return self.payer_name


class ReceiveDocument(models.Model):
    receive = models.ForeignKey(ReceiveMoney, on_delete=models.CASCADE, related_name='documents')
    document = models.FileField(upload_to='images/receive/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.receive.payer_name)


class PayMoney(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='شماره حساب')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True)
    house = models.ForeignKey(
        MyHouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='house_payments',
        verbose_name='ساختمان مرتبط'
    )
    receiver_name = models.CharField(max_length=200, verbose_name='دریافت کننده')
    document_date = models.DateField(verbose_name='تاریخ سند')
    document_number = models.IntegerField(verbose_name='شماره سند')
    description = models.CharField(max_length=4000, verbose_name='شرح')
    amount = models.PositiveIntegerField(verbose_name='مبلغ', null=True, blank=True, default=0)
    details = models.TextField(verbose_name='توضیحات', null=True, blank=True)
    is_paid_money = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False, verbose_name='پرداخت شده/ نشده')
    transaction_reference = models.CharField(max_length=20, null=True, blank=True, default=0)
    payment_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاریخ پرداخت"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return str(self.receiver_name)

    def save(self, *args, **kwargs):
        self.is_paid = bool(self.transaction_reference and self.payment_date)
        super().save(*args, **kwargs)

    @property
    def get_receiver_display(self):
        return str(self.unit) if self.unit else self.receiver_name

    def get_document_urls_json(self):
        # Use the correct attribute to access the file URL in the related `ExpenseDocument` model
        image_urls = [doc.document.url for doc in self.documents.all() if doc.document]
        print(image_urls)
        return mark_safe(json.dumps(image_urls))


class PayDocument(models.Model):
    payment = models.ForeignKey(PayMoney, on_delete=models.CASCADE, related_name='documents')
    document = models.FileField(upload_to='images/payment/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.payment.receiver_name)


# =========================== middleProperty Views ====================
class Property(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    house = models.ForeignKey(
        MyHouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='house_property',
        verbose_name='ساختمان مرتبط'
    )
    property_name = models.CharField(max_length=400, verbose_name='نام')
    property_unit = models.CharField(max_length=3000, verbose_name='واحد')
    property_location = models.CharField(max_length=400, verbose_name='آدرس')
    property_code = models.CharField(max_length=200, verbose_name='کد')
    property_price = models.IntegerField(verbose_name='ارزش')
    details = models.CharField(max_length=4000, verbose_name='توضیحات', null=True, blank=True)
    property_purchase_date = models.DateField(verbose_name='تاریخ خرید', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد', null=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return str(self.property_name)

    def get_urls_json(self):
        # Use the correct attribute to access the file URL in the related `ExpenseDocument` model
        image_urls = [doc.document.url for doc in self.documents.all() if doc.document]
        print(image_urls)
        return mark_safe(json.dumps(image_urls))


class PropertyDocument(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='documents')
    document = models.FileField(upload_to='images/property/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.property.property_name)


# ======================== Maintenance =============================
class Maintenance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    house = models.ForeignKey(
        MyHouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='house_maintenance',
        verbose_name='ساختمان مرتبط'
    )
    maintenance_description = models.CharField(max_length=1000, verbose_name='')
    maintenance_start_date = models.DateField(verbose_name='')
    maintenance_end_date = models.DateField(verbose_name='')
    maintenance_price = models.PositiveIntegerField(verbose_name='')
    maintenance_status = models.CharField(max_length=100, verbose_name='')
    service_company = models.CharField(max_length=200, verbose_name='')
    maintenance_document_no = models.CharField(max_length=100, verbose_name='', null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.maintenance_description)

    def get_documents_urls_json(self):
        # Use the correct attribute to access the file URL in the related `ExpenseDocument` model
        image_urls = [doc.document.url for doc in self.documents.all() if doc.document]
        print(image_urls)
        return mark_safe(json.dumps(image_urls))


class MaintenanceDocument(models.Model):
    maintenance = models.ForeignKey(Maintenance, on_delete=models.CASCADE, related_name='documents')
    document = models.FileField(upload_to='images/maintenance/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.maintenance.maintenance_description)


# =========================== Charge Modals =============================

class BaseCharge(models.Model):
    # فیلدهای عمومی
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=300, null=True, blank=True)
    unit_count = models.IntegerField(null=True, blank=True)
    civil = models.PositiveIntegerField(default=0, null=True, blank=True, verbose_name='شارژ عمرانی')
    other_cost_amount = models.PositiveIntegerField(null=True, blank=True)
    payment_deadline = models.DateField(null=True, blank=True)
    payment_penalty_amount = models.PositiveIntegerField(null=True, blank=True)
    details = models.CharField(max_length=4000, null=True, blank=True)
    unified_charges = GenericRelation('UnifiedCharge', related_query_name='charge')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    charge_type = ''  # باید در مدل فرزند مشخص شود

    # ⚡ اضافه می‌کنیم: فیلدهایی که میخوای در template نمایش داده شوند
    display_fields = []

    class Meta:
        abstract = True

    def to_dict(self):
        data = {
            'id': self.id,
            'name': self.name,
            'charge_type': self.charge_type,
            'created_at': self.created_at,
            'details': self.details,
            'civil': self.civil or 0,
            'other_cost_amount': self.other_cost_amount,
            'payment_penalty_amount': self.payment_penalty_amount,
            'payment_deadline': self.payment_deadline,
            'unit_count': self.unit_count,
            'app_label': self._meta.app_label,
            'model_name': self._meta.model_name,
        }

        # فقط فیلدهای قابل نمایش
        for field_name in getattr(self, 'display_fields', []):
            if hasattr(self, field_name):
                field = self._meta.get_field(field_name)  # گرفتن فیلد مدل
                data[str(field.verbose_name)] = getattr(self, field_name)

        return data


class FixCharge(BaseCharge):
    fix_amount = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ شارژ به ازای هر واحد')
    charge_type = 'fix'
    display_fields = ['fix_amount']


class AreaCharge(BaseCharge):
    area_amount = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ شارژ به ازای هر متر')
    total_area = models.PositiveIntegerField(null=True, blank=True)
    charge_type = 'area'
    display_fields = ['area_amount']


class PersonCharge(BaseCharge):
    person_amount = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ شارژ به ازای هر نفر')
    total_people = models.PositiveIntegerField(null=True, blank=True)
    charge_type = 'person'
    display_fields = ['person_amount']


class FixPersonCharge(BaseCharge):
    fix_charge_amount = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ شارژ به ازای هر واحد')
    person_amount = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ شارژ به ازای هر نفر')
    total_people = models.PositiveIntegerField(null=True, blank=True)
    charge_type = 'fix_person'
    display_fields = ['fix_charge_amount', 'person_amount']


class FixAreaCharge(BaseCharge):
    fix_charge_amount = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ شارژ به ازای هر واحد')
    area_amount = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ شارژ به ازای هر متر')
    total_area = models.PositiveIntegerField(null=True, blank=True, )
    total_people = models.PositiveIntegerField(null=True, blank=True)
    charge_type = 'fix_area'
    display_fields = ['fix_charge_amount', 'area_amount']


class ChargeByPersonArea(BaseCharge):
    area_amount = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ شارژ به ازای هر متر')
    person_amount = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ شارژ به ازای هر نفر')
    total_area = models.PositiveIntegerField(null=True, blank=True)
    total_people = models.PositiveIntegerField(null=True, blank=True)
    charge_type = 'person_area'
    display_fields = ['area_amount', 'person_amount', ]


class ChargeByFixPersonArea(BaseCharge):
    fix_charge_amount = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ شارژ به ازای هر واحد')
    area_amount = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ شارژ به ازای هر متر')
    person_amount = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ شارژ به ازای هر نفر')
    total_area = models.PositiveIntegerField(null=True, blank=True)
    total_people = models.PositiveIntegerField(null=True, blank=True)
    parking_count = models.PositiveIntegerField(null=True, blank=True)
    charge_type = 'fix_person_area'
    display_fields = ['fix_charge_amount', 'area_amount', 'person_amount', ]


class ChargeFixVariable(BaseCharge):
    unit_fix_amount = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ شارژ ثابت به ازای هر واحد')
    unit_variable_person_amount = models.PositiveIntegerField(null=True, blank=True,
                                                              verbose_name='مبلغ شارژ متغیر به ازای هر نفر')
    unit_variable_area_amount = models.PositiveIntegerField(null=True, blank=True,
                                                            verbose_name='مبلغ شارژ متغیر به ازای هر متر')
    extra_parking_amount = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ هزینه پارکینگ اضافه')
    total_area = models.PositiveIntegerField(null=True, blank=True)
    total_people = models.PositiveIntegerField(null=True, blank=True)
    charge_type = 'fix_variable'
    display_fields = ['unit_fix_amount', 'unit_variable_amount', 'unit_variable_area_amount', 'extra_parking_amount', ]


class ChargeByExpense(BaseCharge):
    unit_power_amount = models.PositiveIntegerField(null=True, blank=True, verbose_name='')
    unit_water_amount = models.PositiveIntegerField(null=True)
    unit_gas_amount = models.PositiveIntegerField(null=True)
    extra_parking_amount = models.PositiveIntegerField(null=True)
    charge_type = 'expense_charge'
    display_fields = ['unit_power_amount', 'unit_water_amount', 'unit_gas_amount', 'extra_parking_amount', ]


class UnifiedCharge(models.Model):
    class ChargeType(models.TextChoices):
        FIX = 'fix', 'ثابت'  # Fixed Charge → ثابت
        AREA = 'area', 'متراژی'  # Area Charge → متراژ
        PERSON = 'person', 'نفری'  # Person Charge → نفر
        FIX_PERSON = 'fix_person', 'ثابت + نفر'  # Fixed Person Charge → ثابت + نفر
        FIX_AREA = 'fix_area', 'ثابت + متراژ'  # Fixed Area Charge → ثابت + متراژ
        PERSON_AREA = 'person_area', 'نفر + متراژ'  # Person Area Charge → نفر + متراژ
        FIX_PERSON_AREA = 'fix_person_area', 'ثابت + نفر + متراژ'  # Fixed Person Area → ثابت + نفر + متراژ
        FIX_VARIABLE = 'fix_variable', 'ثابت و متغیر'  # Variable Fixed Charge → ثابت متغیر
        EXPENSE_CHARGE = 'expense_charge', 'هزینه ها'  # Variable Fixed Charge → ثابت متغیر

    main_charge = GenericForeignKey('content_type', 'object_id')
    # کاربر صاحب شارژ
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="unified_charges"
    )

    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name="unified_charges",
        null=True,
        blank=True
    )
    house = models.ForeignKey(
        MyHouse,
        on_delete=models.CASCADE,
        related_name="unified_charges",
        null=True,
        blank=True
    )

    bank = models.ForeignKey(
        Bank,
        on_delete=models.CASCADE,
        related_name="unified_charges",
        null=True,
        blank=True
    )
    # نوع شارژ (نوع محاسبات)
    charge_type = models.CharField(
        max_length=50,
        choices=ChargeType.choices
    )
    # مبلغ نهایی

    amount = models.IntegerField(null=True, blank=True)
    other_cost_amount = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    civil = models.PositiveIntegerField(verbose_name='شارژ عمرانی', default=0, null=True, blank=True)
    base_charge = models.IntegerField(null=True, blank=True)
    penalty_percent = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    penalty_amount = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    total_charge_month = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    extra_parking_price = models.PositiveIntegerField(verbose_name='', null=True, blank=True)

    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    transaction_reference = models.CharField(max_length=20, null=True, blank=True)
    payment_gateway = models.CharField(max_length=100, null=True, blank=True)

    # توضیح
    title = models.TextField(blank=True, null=True)
    send_notification = models.BooleanField(default=False)

    # تاریخ ارسال نوتیفیکیشن
    send_notification_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاریخ ارسال اعلان"
    )
    send_sms = models.BooleanField(default=False)

    # تاریخ ارسال نوتیفیکیشن
    send_sms_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاریخ ارسال پیامک"
    )
    sms_count = models.PositiveIntegerField(default=0)
    sms_price = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    sms_total_price = models.DecimalField(max_digits=12, decimal_places=0, default=0)

    # تاریخ ددلاین پرداخت
    payment_deadline_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="مهلت پرداخت"
    )

    payment_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاریخ پرداخت"
    )

    # وضعیت پرداخت
    is_paid = models.BooleanField(default=False)

    # 🟦 Generic Relation به مدل اصلی محاسبه
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True
    )
    is_penalty_waived = models.BooleanField(default=False)
    penalty_waived_at = models.DateTimeField(null=True, blank=True)
    penalty_waived_by = models.ForeignKey(
        User,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='waived_penalties'
    )
    previous_penalty_amount = models.PositiveIntegerField(null=True, blank=True)

    # تاریخ ایجاد
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.unit:
            self.house = self.unit.myhouse
        super().save(*args, **kwargs)

    @property
    def app_label(self):
        return self._meta.app_label

    @property
    def model_name(self):
        return self._meta.model_name

    @property
    def notified_count_property(self):
        managed_users = self.user.managed_users.all()

        return UnifiedCharge.objects.filter(
            unit__is_active=True,
            unit__user__in=managed_users,
            send_notification=True,
            charge_type=self.charge_type
        ).values('unit').distinct().count()

    def waive_penalty(self, user):
        if not user:
            raise ValueError('user is required to waive penalty')

        # ذخیره جریمه قبل از صفر شدن
        self.previous_penalty_amount = self.penalty_amount

        self.is_penalty_waived = True
        self.penalty_amount = 0
        self.penalty_waived_at = timezone.now()
        self.penalty_waived_by = user

        # محاسبه مبلغ کل بدون جریمه
        self.total_charge_month = self.base_charge or 0

        self.save(update_fields=[
            'is_penalty_waived',
            'penalty_amount',
            'previous_penalty_amount',
            'penalty_waived_at',
            'penalty_waived_by',
            'total_charge_month'
        ])

    def restore_penalty(self):
        if not self.is_penalty_waived or self.previous_penalty_amount is None:
            return None  # جریمه‌ای برای بازیابی وجود ندارد

        self.penalty_amount = self.previous_penalty_amount
        self.is_penalty_waived = False
        self.penalty_waived_at = None
        self.penalty_waived_by = None
        self.previous_penalty_amount = None
        self.total_charge_month = (self.base_charge or 0) + self.penalty_amount
        self.save()

        return {
            'title': getattr(self, 'name', f'واحد {self.id}'),
            'penalty_amount': self.penalty_amount
        }

    @property
    def real_unit_count(self):
        return (
            self.unified_charges
            .filter(unit__is_active=True)
            .values_list('unit_id', flat=True)
            .distinct()
            .count()
        )

    def update_penalty(self, save=True):
        """
        محاسبه جریمه دیرکرد فقط در صورت مجاز بودن
        """

        # 1️⃣ پرداخت شده → جریمه ندارد
        if self.is_paid:
            return

        # 2️⃣ جریمه توسط مدیر بخشیده شده
        if self.is_penalty_waived:
            if self.penalty_amount != 0:
                self.penalty_amount = 0
                self.total_charge_month = self.base_charge or 0
                if save:
                    self.save(update_fields=['penalty_amount', 'total_charge_month'])
            return

        # 3️⃣ شرایط محاسبه
        if not self.payment_deadline_date or not self.penalty_percent:
            return

        today = timezone.now().date()

        # 4️⃣ هنوز مهلت نگذشته
        if today <= self.payment_deadline_date:
            if self.penalty_amount != 0:
                self.penalty_amount = 0
                self.total_charge_month = self.base_charge or 0
                if save:
                    self.save(update_fields=['penalty_amount', 'total_charge_month'])
            return

        # 5️⃣ محاسبه جریمه
        delay_days = (today - self.payment_deadline_date).days
        base = self.base_charge or 0
        new_penalty = int(base * self.penalty_percent / 100 * delay_days)

        if new_penalty != (self.penalty_amount or 0):
            self.penalty_amount = new_penalty
            self.total_charge_month = base + new_penalty
            if save:
                self.save(update_fields=['penalty_amount', 'total_charge_month'])

    def get_mobile(self):
        """
        شماره موبایل برای ارسال پیامک:
        اولویت:
        1️⃣ مستاجر فعال
        2️⃣ مالک واحد
        """
        if not self.unit:
            return None

        # مستاجر فعال
        renter = self.unit.renters.filter(renter_is_active=True).first()
        if renter and renter.renter_mobile:
            return renter.renter_mobile

        # مالک
        if self.unit.owner_mobile:
            return self.unit.owner_mobile

        return None


class Fund(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True)
    house = models.ForeignKey(
        MyHouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='house_funds',
        verbose_name='ساختمان مرتبط'
    )
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='شماره حساب', null=True, blank=True)
    doc_number = models.PositiveIntegerField(null=True, blank=True)
    payer_name = models.CharField(max_length=200, null=True, blank=True)
    receiver_name = models.CharField(max_length=200, null=True, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    amount = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    debtor_amount = models.DecimalField(max_digits=12, decimal_places=0)
    creditor_amount = models.DecimalField(max_digits=12, decimal_places=0)
    final_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)

    payment_gateway = models.CharField(max_length=100, null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    transaction_no = models.CharField(max_length=15, null=True, blank=True)
    payment_description = models.CharField(max_length=500, blank=True, null=True)
    is_initial = models.BooleanField(default=False, verbose_name='افتتاحیه حساب')
    created_at = models.DateTimeField(auto_now_add=True)
    is_received_money = models.BooleanField(default=False)
    is_paid_money = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Fund: {self.payment_description} for {self.content_object}"

    def clean(self):
        """
        قبل از ذخیره، مطمئن شویم final_amount منفی نمی‌شود
        """
        if self.final_amount < 0:
            raise ValidationError("موجودی صندوق کافی نیست. ثبت این تراکنش باعث منفی شدن موجودی می‌شود.")

    @transaction.atomic
    def save(self, *args, **kwargs):
        # تعیین شماره سند فقط برای رکورد جدید
        if not self.pk:
            if not self.doc_number:
                last_doc_number = Fund.objects.aggregate(models.Max('doc_number'))['doc_number__max']
                self.doc_number = (last_doc_number or 0) + 1

            # محاسبه final_amount فقط برای رکورد جدید
            last_fund = Fund.objects.order_by('-doc_number').first()
            previous_final = Decimal(last_fund.final_amount if last_fund and last_fund.final_amount is not None else 0)
            self.final_amount = previous_final + (self.debtor_amount or 0) - (self.creditor_amount or 0)

            # بررسی منفی شدن موجودی
            if self.final_amount < 0:
                raise ValidationError("موجودی صندوق کافی نیست. ثبت این تراکنش باعث منفی شدن موجودی می‌شود.")

        # برای رکوردهای موجود، final_amount با recalc_final_amounts_from به‌روزرسانی می‌شود
        super().save(*args, **kwargs)

    @classmethod
    def recalc_final_amounts_from(cls, fund):
        """
        بازمحاسبه final_amount فقط از Fund داده شده به بعد
        """
        with transaction.atomic():
            # موجودی قبل از fund
            last_before = cls.objects.filter(doc_number__lt=fund.doc_number).order_by('-doc_number').first()
            running_total = Decimal(last_before.final_amount if last_before else 0)

            # بروزرسانی این Fund و بعدی‌ها
            qs = cls.objects.filter(doc_number__gte=fund.doc_number).order_by('doc_number')
            for f in qs:
                running_total += (f.debtor_amount or 0) - (f.creditor_amount or 0)
                if running_total < 0:
                    raise ValidationError(f"خطا: موجودی صندوق در سند شماره {f.doc_number} منفی شد!")
                f.final_amount = running_total
                f.save(update_fields=['final_amount'])


class BankFund(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    house = models.ForeignKey(
        MyHouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bank_funds',
        verbose_name='ساختمان مرتبط'
    )
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='شماره حساب', null=True, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    amount = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    payment_gateway = models.CharField(max_length=100, null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    transaction_no = models.CharField(max_length=15, null=True, blank=True)
    payment_description = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Fund: {self.payment_description} for {self.content_object}"


class AdminFund(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='شماره حساب', null=True, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    amount = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    payment_gateway = models.CharField(max_length=100, null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    transaction_no = models.CharField(max_length=15, null=True, blank=True)
    payment_description = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Fund: {self.payment_description} for {self.content_object}"


class SmsCredit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='مدیر')
    house = models.ForeignKey(
        MyHouse,
        on_delete=models.CASCADE,
        related_name="sms_credit",
        null=True,
        blank=True
    )
    amount = models.DecimalField(max_digits=10, decimal_places=0, verbose_name='مبلغ شارژ')
    amount_with_tax = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='مبلغ با مالیات', default=0)
    is_paid = models.BooleanField(default=False, verbose_name='پرداخت شده؟')
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} تومان - {'پرداخت شده' if self.is_paid else 'در انتظار پرداخت'}"


class SmsManagement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='sms_unit', blank=True, null=True)
    house = models.ForeignKey(
        MyHouse,
        on_delete=models.CASCADE,
        related_name="house_sms",
        null=True,
        blank=True
    )
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    send_notification = models.BooleanField(default=False)
    send_notification_date = models.DateField(null=True, blank=True)
    notified_units = models.ManyToManyField('user_app.Unit', blank=True)  # اضافه کردن رابطه با واحدها
    is_active = models.BooleanField(default=True)

    total_units_sent = models.PositiveIntegerField(default=0)
    sms_per_message = models.PositiveIntegerField(default=0)
    total_sms_sent = models.PositiveIntegerField(default=0)

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0
    )

    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.subject

    @property
    def message_length(self):
        return len(self.message or "")

    @property
    def sms_count(self):
        """
        هر ۷۰ کاراکتر = ۱ پیامک
        """
        if not self.message:
            return 0
        return math.ceil(len(self.message) / 70)

    @property
    def notified_units_count(self):
        return self.notified_units.count()

    @property
    def total_sms_needed(self):
        """
        تعداد کل پیامک = تعداد پیامک هر متن × تعداد واحدها
        """
        return self.sms_count * self.notified_units_count


class AdminSmsManagement(models.Model):
    # فرستنده پیامک
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="admin_sms_sent"
    )

    # گیرندگان پیامک
    notified_users = models.ManyToManyField(
        User,
        blank=True,
        related_name="admin_sms_received"
    )
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    send_notification = models.BooleanField(default=False)
    send_notification_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    total_units_sent = models.PositiveIntegerField(default=0)
    sms_per_message = models.PositiveIntegerField(default=0)
    total_sms_sent = models.PositiveIntegerField(default=0)

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0
    )

    @property
    def sms_count(self):
        """
        هر ۷۰ کاراکتر = ۱ پیامک
        """
        if not self.message:
            return 0
        return math.ceil(len(self.message) / 70)

    @property
    def notified_users_count(self):
        return self.notified_users.count()

    def total_sms_needed(self):
        """
        تعداد کل پیامک = تعداد پیامک هر متن × تعداد واحدها
        """
        return self.sms_count * self.notified_users_count
