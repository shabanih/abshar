import json

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.safestring import mark_safe
from datetime import date

from user_app.models import Unit, User, Bank


class Announcement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=270, verbose_name='عنوان')
    slug = models.SlugField(db_index=True, default='', null=True, max_length=200, verbose_name='عنوان در url')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return self.title


class ExpenseCategory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100, verbose_name='نام')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return self.title


class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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
    category = models.ForeignKey(IncomeCategory, on_delete=models.CASCADE, verbose_name='گروه', related_name='incomes')
    doc_date = models.DateField(verbose_name='تاریخ سند')
    doc_number = models.IntegerField(verbose_name='شماره سند')
    description = models.CharField(max_length=4000, verbose_name='شرح')
    amount = models.PositiveIntegerField(verbose_name='قیمت', null=True, blank=True, default=0)
    details = models.TextField(verbose_name='توضیحات', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return str(self.doc_no)

    def get_document_urls_json(self):
        # Use the correct attribute to access the file URL in the related `ExpenseDocument` model
        image_urls = [doc.document.url for doc in self.documents.all() if doc.document]
        print(image_urls)
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
    payer_name = models.CharField(max_length=200, verbose_name='پرداخت کننده')
    doc_date = models.DateField(verbose_name='تاریخ سند')
    doc_number = models.IntegerField(verbose_name='شماره سند')
    description = models.CharField(max_length=4000, verbose_name='شرح')
    amount = models.PositiveIntegerField(verbose_name='مبلغ', null=True, blank=True, default=0)
    details = models.TextField(verbose_name='توضیحات', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return str(self.payer_name)

    def get_document_json(self):
        # Use the correct attribute to access the file URL in the related `ExpenseDocument` model
        image_urls = [doc.document.url for doc in self.documents.all() if doc.document]
        print(image_urls)
        return mark_safe(json.dumps(image_urls))


class ReceiveDocument(models.Model):
    receive = models.ForeignKey(ReceiveMoney, on_delete=models.CASCADE, related_name='documents')
    document = models.FileField(upload_to='images/receive/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.receive.payer_name)


class PayMoney(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='شماره حساب')
    receiver_name = models.CharField(max_length=200, verbose_name='دریافت کننده')
    document_date = models.DateField(verbose_name='تاریخ سند')
    document_number = models.IntegerField(verbose_name='شماره سند')
    description = models.CharField(max_length=4000, verbose_name='شرح')
    amount = models.PositiveIntegerField(verbose_name='مبلغ', null=True, blank=True, default=0)
    details = models.TextField(verbose_name='توضیحات', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

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
    name = models.CharField(max_length=300, verbose_name='', null=True, blank=True)
    fix_amount = models.PositiveIntegerField(verbose_name='مبلغ', null=True, blank=True)
    civil = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)
    other_cost_amount = models.PositiveIntegerField(verbose_name='سایر هزینه ها', null=True, blank=True)
    unit_count = models.IntegerField(null=True, blank=True)
    payment_deadline = models.DateField(null=True, blank=True)
    payment_penalty_amount = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.name)


class FixedChargeCalc(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charge_fix')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='charge_fix')
    fix_charge = models.ForeignKey(FixCharge, on_delete=models.CASCADE, related_name='fix_charge_amount')
    charge_name = models.CharField(max_length=100, verbose_name='عنوان شارژ', null=True, blank=True)
    amount = models.PositiveIntegerField(verbose_name='مبلغ')
    unit_count = models.PositiveIntegerField(verbose_name='تعداد واحدها', null=True, blank=True)
    civil_charge = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)
    total_charge_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل ماهانه')
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    send_notification = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر')
    send_notification_date = models.DateField(verbose_name='اعلام شارژ به کاربر')
    send_sms = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر با پیامک')
    is_paid = models.BooleanField(default=False, verbose_name='وضعیت پرداخت')
    payment_date = models.DateField(verbose_name='', null=True, blank=True)
    payment_deadline_date = models.DateField(null=True, blank=True)
    other_cost = models.PositiveIntegerField(verbose_name='سایر هزینه ها', null=True, blank=True)
    payment_penalty = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    transaction_reference = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return f"{self.charge_name or 'شارژ'} - {self.amount} تومان"

    def save(self, *args, **kwargs):
        amount = max(self.amount or 0, 0)
        units = max(self.unit_count or 1, 1)
        civil = self.civil_charge or 0
        other_cost = max(self.other_cost or 0, 0)

        self.total_charge_month = (amount * units) + civil + other_cost

        super().save(*args, **kwargs)


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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.name)


class AreaChargeCalc(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charge_area')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='charge_area')
    area_charge = models.ForeignKey(AreaCharge, on_delete=models.CASCADE, related_name='area_charge_amount')
    charge_name = models.CharField(max_length=100, verbose_name='عنوان شارژ', null=True, blank=True)
    amount = models.PositiveIntegerField(verbose_name='مبلغ')
    unit_count = models.PositiveIntegerField(verbose_name='تعداد واحدها', null=True, blank=True)
    total_area = models.PositiveIntegerField(verbose_name='متراژ کل', null=True, blank=True)
    final_area_amount = models.PositiveIntegerField(verbose_name='مبلغ شارژ هر واحئ', null=True, blank=True)

    civil_charge = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)
    payment_deadline_date = models.DateField(null=True, blank=True)
    payment_penalty = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    other_cost = models.PositiveIntegerField(verbose_name='سایر هزینه ها', null=True, blank=True)

    total_charge_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل ماهانه هر واحد')
    send_notification = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر')
    send_notification_date = models.DateField(null=True, blank=True, verbose_name='اعلام شارژ به کاربر')
    send_sms = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر با پیامک')
    is_paid = models.BooleanField(default=False, verbose_name='وضعیت پرداخت')
    payment_date = models.DateField(verbose_name='', null=True, blank=True)

    transaction_reference = models.CharField(max_length=20, null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return f"{self.charge_name or 'شارژ'} - {self.amount} تومان"

    def save(self, *args, **kwargs):
        if self.total_area and self.amount:
            self.final_area_amount = self.unit.area * self.amount

        if self.final_area_amount is not None and self.civil_charge is not None and self.other_cost is not None:
            self.total_charge_month = (
                    self.final_area_amount + self.civil_charge + self.other_cost
            )

        super().save(*args, **kwargs)


class PersonCharge(models.Model):
    name = models.CharField(max_length=300, verbose_name='', null=True, blank=True)
    person_amount = models.PositiveIntegerField(verbose_name='مبلغ', null=True, blank=True)
    civil = models.PositiveIntegerField(verbose_name='شارژ عمرانی', default=0, null=True, blank=True)
    other_cost_amount = models.PositiveIntegerField(verbose_name='سایر هزینه ها', null=True, blank=True)
    unit_count = models.IntegerField(null=True, blank=True)
    total_people = models.PositiveIntegerField(null=True, blank=True)
    payment_deadline = models.DateField(null=True, blank=True)
    payment_penalty_amount = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.name)


class PersonChargeCalc(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charge_person')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='charge_person')
    person_charge = models.ForeignKey(PersonCharge, on_delete=models.CASCADE, related_name='person_charge_amount')
    charge_name = models.CharField(max_length=100, verbose_name='عنوان شارژ', null=True, blank=True)
    amount = models.PositiveIntegerField(verbose_name='مبلغ')
    final_person_amount = models.PositiveIntegerField(verbose_name='مبلغ شارژ نهایی', null=True, blank=True)

    civil_charge = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)
    payment_deadline_date = models.DateField(null=True, blank=True)
    payment_penalty = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    other_cost = models.PositiveIntegerField(verbose_name='سایر هزینه ها', null=True, blank=True)

    unit_count = models.PositiveIntegerField(null=True, blank=True, verbose_name='تعداد واحدها')
    total_people = models.PositiveIntegerField(null=True, blank=True, verbose_name='تعداد نفرات')
    total_charge_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل ماهانه')
    total_charge_year = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل سالیانه')
    send_notification = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر')
    send_notification_date = models.DateField(null=True, blank=True, verbose_name='اعلام شارژ به کاربر')
    send_sms = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر با پیامک')
    is_paid = models.BooleanField(default=False, verbose_name='وضعیت پرداخت')
    payment_date = models.DateField(verbose_name='', null=True, blank=True)
    transaction_reference = models.CharField(max_length=20, null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.amount)

    def save(self, *args, **kwargs):
        if self.total_people is not None and self.amount is not None:
            self.final_person_amount = self.unit.people_count * self.amount

        final = self.final_person_amount or 0
        civil = self.civil_charge or 0
        other_cost = self.other_cost or 0

        self.total_charge_month = final + civil + other_cost

        super().save(*args, **kwargs)


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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.name)


class FixPersonChargeCalc(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charge_fix_person')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='charge_fix_person')
    fix_person = models.ForeignKey(FixPersonCharge, on_delete=models.CASCADE, related_name='fix_person_charge')
    charge_name = models.CharField(max_length=100, verbose_name='عنوان شارژ', null=True, blank=True)
    fix_charge = models.PositiveIntegerField(verbose_name='شارژ ثابت', null=True, blank=True)
    amount = models.PositiveIntegerField(verbose_name='شارژ به ازای نفرات', null=True, blank=True)
    final_person_amount = models.PositiveIntegerField(verbose_name='مبلغ شارژ نهایی', null=True, blank=True)
    unit_count = models.PositiveIntegerField(null=True, blank=True, verbose_name='تعداد واحدها')
    total_people = models.PositiveIntegerField(null=True, blank=True, verbose_name='تعداد نفرات')

    civil_charge = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)
    payment_deadline_date = models.DateField(null=True, blank=True)
    payment_penalty = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    other_cost = models.PositiveIntegerField(verbose_name='سایر هزینه ها', null=True, blank=True)

    total_charge_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل ماهانه')
    send_notification = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر')
    send_notification_date = models.DateField(null=True, blank=True, verbose_name='اعلام شارژ به کاربر')
    send_sms = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر با پیامک')
    is_paid = models.BooleanField(default=False, verbose_name='وضعیت پرداخت')
    payment_date = models.DateField(verbose_name='', null=True, blank=True)
    transaction_reference = models.CharField(max_length=20, null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.charge_name)

    def save(self, *args, **kwargs):
        if self.unit.people_count and self.amount and self.fix_charge:
            self.final_person_amount = (self.unit.people_count * self.amount) + self.fix_charge

        if self.final_person_amount and self.civil_charge:
            self.total_charge_month = self.final_person_amount + self.civil_charge

        super().save(*args, **kwargs)


class FixAreaCharge(models.Model):
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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.name)


class FixAreaChargeCalc(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charge_fix_area')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='charge_fix_area')
    fix_area = models.ForeignKey(FixAreaCharge, on_delete=models.CASCADE, related_name='fix_area_charge')
    charge_name = models.CharField(max_length=100, verbose_name='عنوان شارژ', null=True, blank=True)
    fix_charge = models.PositiveIntegerField(verbose_name='شارژ ثابت', null=True, blank=True)
    amount = models.PositiveIntegerField(verbose_name='شارژ به ازای متراژ', null=True, blank=True)
    unit_count = models.PositiveIntegerField(verbose_name='تعداد واحدها', null=True, blank=True)
    total_area = models.PositiveIntegerField(verbose_name='متراژ کل', null=True, blank=True)
    final_person_amount = models.PositiveIntegerField(verbose_name='مبلغ شارژ نهایی', null=True, blank=True)
    civil_charge = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)
    payment_deadline_date = models.DateField(null=True, blank=True)
    payment_penalty = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    other_cost = models.PositiveIntegerField(verbose_name='سایر هزینه ها', null=True, blank=True)

    total_charge_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل ماهانه')
    send_notification = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر')
    send_notification_date = models.DateField(null=True, blank=True, verbose_name='اعلام شارژ به کاربر')

    send_sms = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر با پیامک')
    is_paid = models.BooleanField(default=False, verbose_name='وضعیت پرداخت')
    payment_date = models.DateField(verbose_name='', null=True, blank=True)
    transaction_reference = models.CharField(max_length=20, null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.charge_name)

    def save(self, *args, **kwargs):
        if self.unit.area and self.amount and self.fix_charge:
            self.final_person_amount = (self.unit.area * self.amount) + self.fix_charge

        if self.final_person_amount and self.civil_charge and self.other_cost:
            self.total_charge_month = self.final_person_amount + self.civil_charge + self.other_cost

        super().save(*args, **kwargs)


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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')


class ChargeByPersonAreaCalc(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charge_by_person_area')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='charge_by_person_area')
    person_area_charge = models.ForeignKey(ChargeByPersonArea, on_delete=models.CASCADE,
                                           related_name='person_area_charge', null=True, blank=True)
    charge_name = models.CharField(max_length=100, verbose_name='عنوان شارژ', null=True, blank=True)
    person_charge = models.PositiveIntegerField(verbose_name='شارژ به ازای نفرات')
    area_charge = models.PositiveIntegerField(verbose_name='شارژ به ازای متراژ')
    unit_count = models.PositiveIntegerField(verbose_name='تعداد واحدها', null=True, blank=True)
    total_people = models.PositiveIntegerField(verbose_name=' کل نفرات', null=True, blank=True)
    total_area = models.PositiveIntegerField(verbose_name='متراژ کل', null=True, blank=True)
    final_person_amount = models.PositiveIntegerField(verbose_name='مبلغ شارژ نهایی', null=True, blank=True)
    total_charge_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل ماهانه')
    payment_deadline_date = models.DateField(null=True, blank=True)
    payment_penalty = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    other_cost = models.PositiveIntegerField(verbose_name='سایر هزینه ها', null=True, blank=True)
    send_notification = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر')
    send_notification_date = models.DateField(null=True, blank=True, verbose_name='اعلام شارژ به کاربر')
    send_sms = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر با پیامک')
    is_paid = models.BooleanField(default=False, verbose_name='وضعیت پرداخت')
    payment_date = models.DateField(verbose_name='', null=True, blank=True)
    transaction_reference = models.CharField(max_length=20, null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    civil_charge = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return str(self.charge_name)

    def save(self, *args, **kwargs):
        if self.unit.area and self.area_charge and self.unit.people_count and self.person_charge:
            self.final_person_amount = (self.unit.area * self.area_charge) + (
                    self.unit.people_count * self.person_charge)

        if self.final_person_amount and self.civil_charge and self.other_cost:
            self.total_charge_month = self.final_person_amount + self.civil_charge + self.other_cost

        super().save(*args, **kwargs)


class ChargeByFixPersonArea(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=300, verbose_name='', null=True, blank=True)
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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return self.name


class ChargeByFixPersonAreaCalc(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charge_by_fix_person_area')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='charge_by_fix_person_area')
    fix_person_area = models.ForeignKey(ChargeByFixPersonArea, on_delete=models.CASCADE,
                                        related_name='fix_person_area', null=True, blank=True)
    charge_name = models.CharField(max_length=100, verbose_name='عنوان شارژ', null=True, blank=True)
    fix_charge = models.PositiveIntegerField(verbose_name='شارژ ثابت', null=True, blank=True)
    person_charge = models.PositiveIntegerField(verbose_name='شارژ به ازای نفرات')
    area_charge = models.PositiveIntegerField(verbose_name='شارژ به ازای متراژ')
    unit_count = models.PositiveIntegerField(verbose_name='تعداد واحدها', null=True, blank=True)
    total_people = models.PositiveIntegerField(verbose_name=' کل نفرات', null=True, blank=True)
    total_area = models.PositiveIntegerField(verbose_name='متراژ کل', null=True, blank=True)
    final_person_amount = models.PositiveIntegerField(verbose_name='مبلغ شارژ نهایی', null=True, blank=True)
    total_charge_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل ماهانه')
    payment_deadline_date = models.DateField(null=True, blank=True)
    payment_penalty = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    other_cost = models.PositiveIntegerField(verbose_name='سایر هزینه ها', null=True, blank=True)
    send_notification = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر')
    send_notification_date = models.DateField(null=True, blank=True, verbose_name='اعلام شارژ به کاربر')
    send_sms = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر با پیامک')
    is_paid = models.BooleanField(default=False, verbose_name='وضعیت پرداخت')
    payment_date = models.DateField(verbose_name='', null=True, blank=True)
    transaction_reference = models.CharField(max_length=20, null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    civil_charge = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return str(self.charge_name)

    def save(self, *args, **kwargs):
        if self.unit.area and self.area_charge and self.unit.people_count and self.person_charge and self.fix_charge:
            self.final_person_amount = (self.unit.area * self.area_charge) + (
                    self.unit.people_count * self.person_charge)

        if self.final_person_amount and self.civil_charge and self.other_cost:
            self.total_charge_month = self.final_person_amount + self.civil_charge + self.fix_charge + self.other_cost

        super().save(*args, **kwargs)


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

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')


class ChargeFixVariableCalc(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charge_calc', null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='charge_calc_fix', null=True, blank=True)
    fix_variable_charge = models.ForeignKey(ChargeFixVariable, on_delete=models.CASCADE,
                                            related_name='fix_variable_charge', null=True, blank=True)

    charge_name = models.CharField(max_length=100, verbose_name='نام شارژ', null=True, blank=True)
    extra_parking_charges = models.PositiveIntegerField(verbose_name='', null=True, blank=True)

    unit_count = models.PositiveIntegerField(verbose_name='تعداد واحدها', null=True, blank=True)
    total_people = models.PositiveIntegerField(verbose_name=' کل نفرات', null=True, blank=True)
    total_area = models.PositiveIntegerField(verbose_name='متراژ کل', null=True, blank=True)
    unit_fix_charge_per_unit = models.PositiveIntegerField(verbose_name='مبلغ شارژ ثابت', null=True, blank=True)
    unit_variable_person_charge = models.PositiveIntegerField(verbose_name='مبلغ شارژ متغیر هر نفر', null=True,
                                                              blank=True)
    unit_variable_area_charge = models.PositiveIntegerField(verbose_name='مبلغ شارژ متغیر هر متر', null=True,
                                                            blank=True)
    final_person_amount = models.PositiveIntegerField(verbose_name='مبلغ شارژ نهایی', null=True, blank=True)
    total_charge_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل ماهانه')

    payment_deadline_date = models.DateField(null=True, blank=True)
    payment_penalty = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    send_notification = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر')
    send_notification_date = models.DateField(null=True, blank=True, verbose_name='اعلام شارژ به کاربر')
    other_cost = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    send_sms = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر با پیامک')
    is_paid = models.BooleanField(default=False, verbose_name='وضعیت پرداخت')
    payment_date = models.DateField(verbose_name='', null=True, blank=True)
    transaction_reference = models.CharField(max_length=20, null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    civil_charge = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.charge_name)

    def save(self, *args, **kwargs):
        area = float(self.unit.area or 0)
        people = float(self.unit.people_count or 0)
        variable_area_charge = float(self.unit_variable_area_charge or 0)
        variable_person_charge = float(self.unit_variable_person_charge or 0)
        fix_charge = float(self.unit_fix_charge_per_unit or 0)
        civil_charge = float(self.civil_charge or 0)
        other_cost = float(self.other_cost)

        # Calculate extra parking middleCharge only if unit.parking_counts > 0
        parking_counts = float(self.unit.parking_counts or 0)
        extra_parking_amount = float(self.extra_parking_charges or 0)
        parking_charge = parking_counts * extra_parking_amount if parking_counts > 0 else 0

        # Calculate final person-based amount
        self.final_person_amount = (area * variable_area_charge) + (people * variable_person_charge)

        # Total monthly middleCharge = person/area + parking + civil
        self.total_charge_month = self.final_person_amount + fix_charge + civil_charge + parking_charge + other_cost

        print(f'self.final_person_amount', self.final_person_amount)

        super().save(*args, **kwargs)


class Fund(models.Model):
    doc_number = models.PositiveIntegerField(unique=True, editable=False, null=True, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    debtor_amount = models.DecimalField(max_digits=12, decimal_places=0)
    creditor_amount = models.DecimalField(max_digits=12, decimal_places=0)
    final_amount = models.PositiveIntegerField(default=0)

    payment_date = models.DateField()
    payment_description = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Fund: {self.payment_description} for {self.content_object}"

    def save(self, *args, **kwargs):
        if not self.doc_number:
            last_doc_number = Fund.objects.aggregate(models.Max('doc_number'))['doc_number__max']
            self.doc_number = (last_doc_number or 0) + 1

        # Get the last fund record (the most recent)
        last_fund = Fund.objects.order_by('-doc_number').first()

        if last_fund:
            previous_final = last_fund.final_amount
        else:
            # No fund records yet — sum all banks' initial funds
            from user_app.models import Bank  # import your Bank model
            total_initial = Bank.objects.aggregate(total=models.Sum('initial_fund'))['total'] or 0
            previous_final = total_initial

        self.final_amount = previous_final + (self.debtor_amount or 0) - (self.creditor_amount or 0)

        super().save(*args, **kwargs)
