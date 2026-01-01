import json
from decimal import Decimal

from ckeditor_uploader.fields import RichTextUploadingField
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from datetime import date

from user_app.models import Unit, User, Bank


class Announcement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = RichTextUploadingField(null=True, blank=True)  # ⬅ـ تغییر
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return self.title


class MessageToUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    units = models.ManyToManyField(
        Unit,
        related_name='messages',
        verbose_name='واحدها'
    )
    title = models.CharField(max_length=400, null=True, blank=True)
    message = models.CharField(max_length=400, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')
    is_seen = models.BooleanField(default=False, verbose_name='')

    def __str__(self):
        return self.user.full_name


class MessageReadStatus(models.Model):
    message = models.ForeignKey('MessageToUser', on_delete=models.CASCADE, related_name='read_statuses')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

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
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='شماره حساب')

    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, verbose_name='گروه',
                                 related_name='expenses')
    date = models.DateField(verbose_name='تاریخ سند')
    doc_no = models.IntegerField(verbose_name='شماره سند')
    description = models.CharField(max_length=4000, verbose_name='شرح')
    amount = models.PositiveIntegerField(verbose_name='قیمت', null=True, blank=True, default=0)
    details = models.TextField(verbose_name='توضیحات', null=True, blank=True)
    # document = models.FileField(upload_to='images/expense', verbose_name='تصاویر هزینه', null=True, blank=True)
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
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='شماره حساب')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True)
    payer_name = models.CharField(max_length=400, null=True, blank=True)
    category = models.ForeignKey(IncomeCategory, on_delete=models.CASCADE, verbose_name='گروه', related_name='incomes')
    doc_date = models.DateField(verbose_name='تاریخ سند')
    doc_number = models.IntegerField(verbose_name='شماره سند')
    description = models.CharField(max_length=4000, verbose_name='شرح')
    amount = models.PositiveIntegerField(verbose_name='قیمت', null=True, blank=True, default=0)
    details = models.TextField(verbose_name='توضیحات', null=True, blank=True)
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
    payer_name = models.CharField(max_length=400, null=True, blank=True)
    doc_date = models.DateField(verbose_name='تاریخ سند')
    doc_number = models.IntegerField(verbose_name='شماره سند')
    description = models.CharField(max_length=4000, verbose_name='شرح')
    amount = models.PositiveIntegerField(verbose_name='مبلغ', null=True, blank=True, default=0)
    details = models.TextField(verbose_name='توضیحات', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')
    is_received = models.BooleanField(default=False, verbose_name='')

    def __str__(self):
        return str(self.unit.unit)

    def get_document_json(self):
        # Use the correct attribute to access the file URL in the related `ExpenseDocument` model
        image_urls = [doc.document.url for doc in self.documents.all() if doc.document]
        print(image_urls)
        return mark_safe(json.dumps(image_urls))

    def get_payer_display(self):
        return str(self.unit) if self.unit else self.payer_name


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
    receiver_name = models.CharField(max_length=200, verbose_name='دریافت کننده')
    document_date = models.DateField(verbose_name='تاریخ سند')
    document_number = models.IntegerField(verbose_name='شماره سند')
    description = models.CharField(max_length=4000, verbose_name='شرح')
    amount = models.PositiveIntegerField(verbose_name='مبلغ', null=True, blank=True, default=0)
    details = models.TextField(verbose_name='توضیحات', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')
    is_payed = models.BooleanField(default=False, verbose_name='')

    def __str__(self):
        return str(self.receiver_name)

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
class FixCharge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fixCharge')
    name = models.CharField(max_length=300, null=True, blank=True)
    fix_amount = models.PositiveIntegerField(null=True, blank=True)
    civil = models.PositiveIntegerField(null=True, blank=True)
    other_cost_amount = models.PositiveIntegerField(null=True, blank=True)
    unit_count = models.IntegerField(null=True, blank=True)
    payment_deadline = models.DateField(null=True, blank=True)
    payment_penalty_amount = models.PositiveIntegerField(null=True, blank=True)  # درصد جریمه
    details = models.CharField(max_length=4000, null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)  # تاریخ پرداخت واقعی
    unified_charges = GenericRelation('UnifiedCharge', related_query_name='fix_charge')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return str(self.name)

    charge_type = 'fix'

    def calculate_charge(self, unit):
        from services.calculators import CALCULATORS

        calculator = CALCULATORS.get(self.charge_type)
        if not calculator:
            return 0

        base_total = calculator.calculate(unit, self)
        penalty = calculator.calculate_penalty(self, base_total)
        return base_total + penalty

class AreaCharge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='areaCharge')
    name = models.CharField(max_length=300, verbose_name='', null=True, blank=True)
    area_amount = models.PositiveIntegerField(verbose_name='مبلغ', null=True, blank=True)
    civil = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)
    other_cost_amount = models.PositiveIntegerField(verbose_name='سایر هزینه ها', null=True, blank=True)
    payment_deadline = models.DateField(null=True, blank=True)
    unit_count = models.IntegerField(null=True, blank=True)
    total_area = models.IntegerField(null=True, blank=True)
    payment_penalty_amount = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    unified_charges = GenericRelation('UnifiedCharge', related_query_name='area_charge')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.name)

    charge_type = 'area'

    def calculate_charge(self, unit):
        from services.calculators import CALCULATORS

        calculator = CALCULATORS.get(self.charge_type)
        if not calculator:
            return 0

        base_total = calculator.calculate(unit, self)
        penalty = calculator.calculate_penalty(self, base_total)
        return base_total + penalty


class PersonCharge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chargePerson')
    name = models.CharField(max_length=300, verbose_name='', null=True, blank=True)
    person_amount = models.PositiveIntegerField(verbose_name='مبلغ', null=True, blank=True)
    civil = models.PositiveIntegerField(verbose_name='شارژ عمرانی', default=0, null=True, blank=True)
    other_cost_amount = models.PositiveIntegerField(verbose_name='سایر هزینه ها', null=True, blank=True)
    unit_count = models.IntegerField(null=True, blank=True)
    total_people = models.PositiveIntegerField(null=True, blank=True)
    payment_deadline = models.DateField(null=True, blank=True)
    payment_penalty_amount = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    unified_charges = GenericRelation('UnifiedCharge', related_query_name='person_charge')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.name)

    charge_type = 'person'

    def calculate_charge(self, unit):
        from services.calculators import CALCULATORS

        calculator = CALCULATORS.get(self.charge_type)
        if not calculator:
            return 0

        base_total = calculator.calculate(unit, self)
        penalty = calculator.calculate_penalty(self, base_total)
        return base_total + penalty


class FixPersonCharge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=300, verbose_name='', null=True, blank=True)
    fix_charge_amount = models.PositiveIntegerField(verbose_name='مبلغ ثابت', null=True, blank=True)
    person_amount = models.PositiveIntegerField(verbose_name='مبلغ', null=True, blank=True)
    total_people = models.PositiveIntegerField(null=True, blank=True)
    other_cost_amount = models.PositiveIntegerField(verbose_name='سایر هزینه ها', null=True, blank=True)
    unit_count = models.IntegerField(null=True, blank=True)
    payment_deadline = models.DateField(null=True, blank=True)
    payment_penalty_amount = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    civil = models.PositiveIntegerField(verbose_name='شارژ عمرانی', default=0, null=True, blank=True)
    unified_charges = GenericRelation('UnifiedCharge', related_query_name='area_charge')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.name)

    charge_type = 'fix_person'

    def calculate_charge(self, unit):
        from services.calculators import CALCULATORS

        calculator = CALCULATORS.get(self.charge_type)
        if not calculator:
            return 0

        base_total = calculator.calculate(unit, self)
        penalty = calculator.calculate_penalty(self, base_total)
        return base_total + penalty


class FixAreaCharge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charge_fixed_area')
    name = models.CharField(max_length=300, verbose_name='', null=True, blank=True)
    fix_charge_amount = models.PositiveIntegerField(verbose_name='مبلغ ثابت', null=True, blank=True)
    area_amount = models.PositiveIntegerField(verbose_name='مبلغ', null=True, blank=True)
    total_area = models.PositiveIntegerField(null=True, blank=True)
    other_cost_amount = models.PositiveIntegerField(verbose_name='سایر هزینه ها', null=True, blank=True)
    unit_count = models.IntegerField(null=True, blank=True)
    total_people = models.PositiveIntegerField(null=True, blank=True)
    payment_deadline = models.DateField(null=True, blank=True)
    payment_penalty_amount = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    civil = models.PositiveIntegerField(verbose_name='شارژ عمرانی', default=0, null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    unified_charges = GenericRelation('UnifiedCharge', related_query_name='area_charge')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.name)

    charge_type = 'fix_area'

    def calculate_charge(self, unit):
        from services.calculators import CALCULATORS

        calculator = CALCULATORS.get(self.charge_type)
        if not calculator:
            return 0

        base_total = calculator.calculate(unit, self)
        penalty = calculator.calculate_penalty(self, base_total)
        return base_total + penalty


class ChargeByPersonArea(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=300, verbose_name='', null=True, blank=True)
    area_amount = models.PositiveIntegerField(verbose_name='مبلغ', null=True, blank=True)
    person_amount = models.PositiveIntegerField(verbose_name='مبلغ', null=True, blank=True)
    total_area = models.PositiveIntegerField(null=True, blank=True)
    total_people = models.PositiveIntegerField(null=True, blank=True)
    other_cost_amount = models.PositiveIntegerField(verbose_name='سایر هزینه ها', null=True, blank=True)
    payment_deadline = models.DateField(null=True, blank=True)
    payment_penalty_amount = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    unit_count = models.IntegerField(null=True, blank=True)
    civil = models.PositiveIntegerField(verbose_name='شارژ عمرانی', default=0, null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    unified_charges = GenericRelation('UnifiedCharge', related_query_name='area_charge')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return self.name

    charge_type = 'person_area'

    def calculate_charge(self, unit):
        from services.calculators import CALCULATORS

        calculator = CALCULATORS.get(self.charge_type)
        if not calculator:
            return 0

        base_total = calculator.calculate(unit, self)
        penalty = calculator.calculate_penalty(self, base_total)
        return base_total + penalty


class ChargeByFixPersonArea(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=500, verbose_name='', null=True, blank=True)
    fix_charge_amount = models.PositiveIntegerField(verbose_name='')
    area_amount = models.PositiveIntegerField(verbose_name='مبلغ', null=True, blank=True)
    person_amount = models.PositiveIntegerField(verbose_name='مبلغ', null=True, blank=True)
    total_area = models.PositiveIntegerField(null=True, blank=True)
    total_people = models.PositiveIntegerField(null=True, blank=True)
    other_cost_amount = models.PositiveIntegerField(verbose_name='سایر هزینه ها', null=True, blank=True)
    payment_deadline = models.DateField(null=True, blank=True)
    payment_penalty_amount = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    unit_count = models.IntegerField(null=True, blank=True)
    parking_count = models.PositiveIntegerField(verbose_name='تعداد پارکینگ اضافه', null=True, blank=True)
    civil = models.PositiveIntegerField(verbose_name='شارژ عمرانی', default=0, null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    unified_charges = GenericRelation('UnifiedCharge', related_query_name='area_charge')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return self.name

    charge_type = 'fix_person_area'

    def calculate_charge(self, unit):
        from services.calculators import CALCULATORS

        calculator = CALCULATORS.get(self.charge_type)
        if not calculator:
            return 0

        base_total = calculator.calculate(unit, self)
        penalty = calculator.calculate_penalty(self, base_total)
        return base_total + penalty


class ChargeFixVariable(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=300, verbose_name='', null=True, blank=True)
    extra_parking_amount = models.PositiveIntegerField(verbose_name='هزینه پارکینگ اضافه', null=True, blank=True)
    total_area = models.PositiveIntegerField(null=True, blank=True)
    total_people = models.PositiveIntegerField(null=True, blank=True)
    unit_fix_amount = models.PositiveIntegerField(verbose_name='مبلغ شارژ ثابت', null=True, blank=True)
    unit_variable_person_amount = models.PositiveIntegerField(verbose_name='مبلغ شارژ متغیر هر نفر', null=True,
                                                              blank=True)
    unit_variable_area_amount = models.PositiveIntegerField(verbose_name='مبلغ شارژ متغیر هر متر', null=True,
                                                            blank=True)
    other_cost_amount = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    civil = models.PositiveIntegerField(verbose_name='شارژ عمرانی', default=0, null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    payment_deadline = models.DateField(null=True, blank=True)
    payment_penalty_amount = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    unit_count = models.IntegerField(null=True, blank=True)
    unified_charges = GenericRelation('UnifiedCharge', related_query_name='area_charge')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return self.name

    charge_type = 'fix_variable'

    def calculate_charge(self, unit):
        from services.calculators import CALCULATORS

        calculator = CALCULATORS.get(self.charge_type)
        if not calculator:
            return 0

        base_total = calculator.calculate(unit, self)
        penalty = calculator.calculate_penalty(self, base_total)
        return base_total + penalty


class UnifiedCharge(models.Model):
    class ChargeType(models.TextChoices):
        FIXED = 'fixed', 'Fixed Charge'
        AREA = 'area', 'Area Charge'
        PERSON = 'person', 'Person Charge'
        FIX_PERSON = 'fix_person', 'Fixed Person Charge'
        FIX_AREA = 'fix_area', 'Fixed Area Charge'
        PERSON_AREA = 'person_area', 'Person Area Charge'
        FIX_PERSON_AREA = 'fix_person_area', 'Fixed Person Area'
        FIX_VARIABLE = 'fix_variable', 'Variable Fixed Charge'

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
    fix_amount = models.IntegerField(null=True, blank=True)
    charge_by_person_amount = models.IntegerField(null=True, blank=True)
    charge_by_area_amount = models.IntegerField(null=True, blank=True)
    fix_person_variable_amount = models.IntegerField(null=True, blank=True)
    fix_area_variable_amount = models.IntegerField(null=True, blank=True)

    # مبلغ نهایی
    base_charge = models.IntegerField(null=True, blank=True)

    penalty_percent = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    penalty_amount = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    other_cost_amount = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    civil = models.PositiveIntegerField(verbose_name='شارژ عمرانی', default=0, null=True, blank=True)

    total_charge_month = models.PositiveIntegerField(verbose_name='', null=True, blank=True)

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
    related_object = GenericForeignKey('content_type', 'object_id')

    # تاریخ ایجاد
    created_at = models.DateTimeField(auto_now_add=True)


    def update_penalty(self, save=True):
        """
        محاسبه و بروزرسانی جریمه دیرکرد
        """

        base_total = self.base_charge or 0
        today = timezone.now().date()

        # ---------- ۱: اگر پرداخت شده → جریمه صفر ----------
        if self.is_paid:
            if self.penalty_amount != 0:
                self.penalty_amount = 0
                self.total_charge_month = (
                        base_total
                        + (self.other_cost_amount or 0)
                        + (self.civil or 0)
                )
                if save:
                    self.save(update_fields=['penalty_amount', 'total_charge_month'])
            return

        # ---------- ۲: اگر deadline یا درصد جریمه ندارد ----------
        if not self.payment_deadline_date or not self.penalty_percent:
            return

        # ---------- ۳: اگر هنوز مهلت نگذشته ----------
        if today <= self.payment_deadline_date:
            if self.penalty_amount != 0:
                self.penalty_amount = 0
                self.total_charge_month = (
                        base_total
                        + (self.other_cost_amount or 0)
                        + (self.civil or 0)
                )
                if save:
                    self.save(update_fields=['penalty_amount', 'total_charge_month'])
            return

        # ---------- ۴: محاسبه جریمه ----------
        delay_days = (today - self.payment_deadline_date).days
        new_penalty = int(base_total * self.penalty_percent / 100 * delay_days)

        # ---------- ۵: ذخیره فقط در صورت تغییر ----------
        if new_penalty != (self.penalty_amount or 0):
            self.penalty_amount = new_penalty
            self.total_charge_month = (
                    base_total
                    + new_penalty
                    + (self.other_cost_amount or 0)
                    + (self.civil or 0)
            )
            if save:
                self.save(update_fields=['penalty_amount', 'total_charge_month'])


class Fund(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True)
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='شماره حساب', null=True, blank=True)
    doc_number = models.PositiveIntegerField(unique=True, editable=False, null=True, blank=True)
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
    is_received = models.BooleanField(default=False)
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


class SmsManagement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='sms_unit', blank=True, null=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    send_notification = models.BooleanField(default=False)
    send_notification_date = models.DateField(null=True, blank=True, verbose_name='اعلام شارژ به کاربر')
    notified_units = models.ManyToManyField('user_app.Unit', blank=True)  # اضافه کردن رابطه با واحدها
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.subject

    @property
    def notified_units_count(self):
        return self.notified_units.count()


