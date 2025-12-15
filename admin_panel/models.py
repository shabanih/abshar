import json

from ckeditor_uploader.fields import RichTextUploadingField
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
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
        return str(self.doc_number)

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
    total_charge_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل ماهانه')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.name)

    def save(self, *args, **kwargs):
        amount = max(self.fix_amount or 0, 0)
        civil = self.civil or 0
        other_cost = max(self.other_cost_amount or 0, 0)

        self.total_charge_month = amount + civil + other_cost

        super().save(*args, **kwargs)


class FixedChargeCalc(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charge_fix')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='charge_fix')
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='شماره حساب', null=True, blank=True)
    fix_charge = models.ForeignKey(FixCharge, on_delete=models.CASCADE, related_name='fix_charge_amount')
    charge_name = models.CharField(max_length=100, verbose_name='عنوان شارژ', null=True, blank=True)
    amount = models.PositiveIntegerField(verbose_name='مبلغ')
    unit_count = models.PositiveIntegerField(verbose_name='تعداد واحدها', null=True, blank=True)
    civil_charge = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)
    base_charge = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ')
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
    payment_penalty_price = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    transaction_reference = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return f"{self.charge_name or 'شارژ'} - {self.amount} تومان"

    def calculate_penalty(self, base_total):
        if not self.payment_deadline_date or self.is_paid:
            return 0

        today = timezone.now().date()
        deadline = self.payment_deadline_date

        if today <= deadline:
            return 0

        delay_days = (today - deadline).days
        penalty_percent = self.payment_penalty or 0

        # محاسبه جریمه فقط روی base_total
        penalty_amount = int((base_total * penalty_percent / 100) * delay_days)
        return penalty_amount

    def save(self, *args, **kwargs):
        amount = max(self.amount or 0, 0)
        civil = max(self.civil_charge or 0, 0)
        other_cost = max(self.other_cost or 0, 0)
        base_total = amount + civil + other_cost

        if not self.is_paid:  # فقط اگر پرداخت نشده است جریمه محاسبه شود
            penalty = self.calculate_penalty(base_total)
            self.payment_penalty_price = penalty
            self.total_charge_month = base_total + penalty
        else:  # اگر پرداخت شده، total_charge_month همان مقدار قبلی باقی بماند
            if self.total_charge_month is None:
                self.total_charge_month = base_total

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
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='شماره حساب', null=True, blank=True)
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
    base_charge = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ')
    total_charge_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل ماهانه هر واحد')
    send_notification = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر')
    send_notification_date = models.DateField(null=True, blank=True, verbose_name='اعلام شارژ به کاربر')
    send_sms = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر با پیامک')
    is_paid = models.BooleanField(default=False, verbose_name='وضعیت پرداخت')
    payment_date = models.DateField(verbose_name='', null=True, blank=True)
    payment_penalty_price = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    transaction_reference = models.CharField(max_length=20, null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return f"{self.charge_name or 'شارژ'} - {self.amount} تومان"

    def calculate_penalty(self, base_total):
        if not self.payment_deadline_date or self.is_paid:
            return 0

        today = timezone.now().date()
        deadline = self.payment_deadline_date

        if today <= deadline:
            return 0

        delay_days = (today - deadline).days
        penalty_percent = self.payment_penalty or 0

        # ⚡ محاسبه جریمه فقط روی پایه شارژ، نه total_charge_month
        penalty_amount = int(base_total * penalty_percent / 100 * delay_days)
        return penalty_amount

    def save(self, *args, **kwargs):
        # محاسبه مبلغ پایه
        base_total = (self.final_area_amount or 0) + (self.civil_charge or 0) + (self.other_cost or 0)

        # ⚡ جریمه فقط اگر پرداخت نشده و تاریخ سررسید گذشته باشد
        if not self.is_paid and self.payment_deadline_date and timezone.now().date() > self.payment_deadline_date:
            penalty = self.calculate_penalty(base_total)
            self.payment_penalty_price = penalty
            self.total_charge_month = base_total + penalty
        else:
            # اگر پرداخت شده یا هنوز سررسید نگذشته، فقط base_total بدون تغییر
            self.payment_penalty_price = self.payment_penalty_price or 0
            self.total_charge_month = base_total + (self.payment_penalty_price or 0)

        super().save(*args, **kwargs)


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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.name)


class PersonChargeCalc(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charge_person')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='charge_person')
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='شماره حساب', null=True, blank=True)
    person_charge = models.ForeignKey(PersonCharge, on_delete=models.CASCADE, related_name='person_charge_amount')
    charge_name = models.CharField(max_length=100, verbose_name='عنوان شارژ', null=True, blank=True)
    amount = models.PositiveIntegerField(verbose_name='مبلغ')
    final_person_amount = models.PositiveIntegerField(verbose_name='مبلغ شارژ نهایی', null=True, blank=True)
    base_charge = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ')

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
    payment_penalty_price = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    transaction_reference = models.CharField(max_length=20, null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.amount)

    def calculate_penalty(self):
        if not self.payment_deadline_date or self.is_paid:
            return 0

        today = timezone.now().date()
        deadline = self.payment_deadline_date

        if today <= deadline:
            return 0

        delay_days = (today - deadline).days
        penalty_percent = self.payment_penalty or 0

        # محاسبه مجموع پایه
        base_total = (self.final_person_amount or 0) + (self.civil_charge or 0) + (self.other_cost or 0)

        return int(base_total * penalty_percent / 100 * delay_days)

    def save(self, *args, recalc_penalty=True, **kwargs):

        base_total = (self.final_person_amount or 0) + \
                     (self.civil_charge or 0) + \
                     (self.other_cost or 0)

        if not self.is_paid:
            if recalc_penalty or self.payment_penalty_price is None:
                self.payment_penalty_price = self.calculate_penalty()

            self.total_charge_month = base_total + (self.payment_penalty_price or 0)

        else:  # اگر پرداخت شده باشد
            if self.total_charge_month is None:
                self.total_charge_month = base_total

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
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='شماره حساب', null=True, blank=True)
    fix_person = models.ForeignKey(FixPersonCharge, on_delete=models.CASCADE, related_name='fix_person_charge')
    charge_name = models.CharField(max_length=100, verbose_name='عنوان شارژ', null=True, blank=True)
    fix_charge = models.PositiveIntegerField(verbose_name='شارژ ثابت', null=True, blank=True)
    amount = models.PositiveIntegerField(verbose_name='شارژ به ازای نفرات', null=True, blank=True)
    final_person_amount = models.PositiveIntegerField(verbose_name='مبلغ شارژ نهایی', null=True, blank=True)
    unit_count = models.PositiveIntegerField(null=True, blank=True, verbose_name='تعداد واحدها')
    total_people = models.PositiveIntegerField(null=True, blank=True, verbose_name='تعداد نفرات')
    base_charge = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ')

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
    payment_penalty_price = models.PositiveIntegerField(verbose_name='', null=True, blank=True)

    transaction_reference = models.CharField(max_length=20, null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.charge_name)

    from django.utils import timezone

    def calculate_penalty(self):
        if not self.payment_deadline_date or self.is_paid:
            return 0

        today = timezone.now().date()
        deadline = self.payment_deadline_date

        if today <= deadline:
            return 0

        delay_days = (today - deadline).days
        penalty_percent = self.payment_penalty or 0

        # محاسبه جریمه بر اساس درصد و تعداد روزها
        base_amount = self.total_charge_month or 0
        penalty_amount = int(base_amount * penalty_percent / 100 * delay_days)
        return penalty_amount

    def save(self, *args, **kwargs):
        # محاسبه مبلغ نهایی بر اساس تعداد افراد و شارژ ثابت
        final = 0
        if self.unit.people_count and self.amount:
            final = self.unit.people_count * self.amount
        if getattr(self, 'fix_charge', 0):
            final += self.fix_charge
        self.final_person_amount = final

        civil = self.civil_charge or 0
        other = self.other_cost or 0

        # محاسبه شارژ کل ماهانه بدون جریمه
        self.total_charge_month = final + civil + other

        # اضافه کردن جریمه دیرکرد اگر پرداخت نشده
        if not self.is_paid:
            self.payment_penalty_price = self.calculate_penalty()
            if self.payment_penalty_price:
                self.total_charge_month += self.payment_penalty_price

        super().save(*args, **kwargs)


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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.name)


class FixAreaChargeCalc(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charge_fix_area')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='charge_fix_area')
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='شماره حساب', null=True, blank=True)
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
    base_charge = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ')

    total_charge_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل ماهانه')
    send_notification = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر')
    send_notification_date = models.DateField(null=True, blank=True, verbose_name='اعلام شارژ به کاربر')

    send_sms = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر با پیامک')
    is_paid = models.BooleanField(default=False, verbose_name='وضعیت پرداخت')
    payment_date = models.DateField(verbose_name='', null=True, blank=True)
    payment_penalty_price = models.PositiveIntegerField(verbose_name='', null=True, blank=True)

    transaction_reference = models.CharField(max_length=20, null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.charge_name)

    def calculate_penalty(self):
        if not self.payment_deadline_date or self.is_paid:
            return 0

        today = timezone.now().date()
        deadline = self.payment_deadline_date

        if today <= deadline:
            return 0

        delay_days = (today - deadline).days
        penalty_percent = self.payment_penalty or 0

        # محاسبه جریمه بر اساس درصد و تعداد روزها
        penalty_amount = int((self.total_charge_month or 0) * penalty_percent / 100 * delay_days)
        return penalty_amount

    def save(self, *args, **kwargs):
        # محاسبه مبلغ نهایی بر اساس متراژ واحد و شارژ ثابت
        final = 0
        if getattr(self.unit, 'area', 0) and getattr(self, 'amount', 0):
            final = self.unit.area * self.amount
        if getattr(self, 'fix_charge', 0):
            final += self.fix_charge

        self.final_person_amount = final

        civil = self.civil_charge or 0
        other = self.other_cost or 0

        # محاسبه شارژ کل ماهانه بدون جریمه
        self.total_charge_month = final + civil + other

        # اضافه کردن جریمه دیرکرد اگر پرداخت نشده
        if not self.is_paid:
            self.payment_penalty_price = self.calculate_penalty()
            if self.payment_penalty_price:
                self.total_charge_month += self.payment_penalty_price

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
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='شماره حساب', null=True, blank=True)
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
    payment_penalty_price = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    base_charge = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ')

    transaction_reference = models.CharField(max_length=20, null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    civil_charge = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return str(self.charge_name)

    def calculate_penalty(self):
        if not self.payment_deadline_date or self.is_paid:
            return 0

        today = timezone.now().date()
        deadline = self.payment_deadline_date

        if today <= deadline:
            return 0

        delay_days = (today - deadline).days
        penalty_percent = self.payment_penalty or 0

        # محاسبه جریمه بر اساس درصد و تعداد روزها
        base_amount = self.total_charge_month or 0
        penalty_amount = int(base_amount * penalty_percent / 100 * delay_days)
        return penalty_amount

    def save(self, *args, **kwargs):
        # محاسبه شارژ نهایی بر اساس متراژ و تعداد نفرات
        area = getattr(self.unit, 'area', 0)
        people = getattr(self.unit, 'people_count', 0)
        area_charge = self.area_charge or 0
        person_charge = self.person_charge or 0

        self.final_person_amount = (area * area_charge) + (people * person_charge)

        civil = self.civil_charge or 0
        other = self.other_cost or 0

        # محاسبه شارژ کل ماهانه بدون جریمه
        self.total_charge_month = self.final_person_amount + civil + other

        # اضافه کردن جریمه دیرکرد اگر پرداخت نشده
        if not self.is_paid:
            self.payment_penalty_price = self.calculate_penalty()
            if self.payment_penalty_price:
                self.total_charge_month += self.payment_penalty_price

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
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='شماره حساب', null=True, blank=True)
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
    payment_penalty_price = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    base_charge = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ')

    transaction_reference = models.CharField(max_length=20, null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    civil_charge = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return str(self.charge_name)

    def calculate_penalty(self):
        if not self.payment_deadline_date or self.is_paid:
            return 0

        today = timezone.now().date()
        deadline = self.payment_deadline_date

        if today <= deadline:
            return 0

        delay_days = (today - deadline).days
        penalty_percent = self.payment_penalty or 0

        # محاسبه جریمه بر اساس درصد و تعداد روزها
        base_amount = self.total_charge_month or 0
        penalty_amount = int(base_amount * penalty_percent / 100 * delay_days)
        return penalty_amount

    def save(self, *args, **kwargs):
        # محاسبه مبلغ نهایی بر اساس متراژ، تعداد نفرات و شارژ ثابت
        area = getattr(self.unit, 'area', 0)
        people = getattr(self.unit, 'people_count', 0)
        area_charge = self.area_charge or 0
        person_charge = self.person_charge or 0
        fix = self.fix_charge or 0

        self.final_person_amount = (area * area_charge) + (people * person_charge) + fix

        civil = self.civil_charge or 0
        other = self.other_cost or 0

        # محاسبه شارژ کل ماهانه بدون جریمه
        self.total_charge_month = self.final_person_amount + civil + other

        # اضافه کردن جریمه دیرکرد اگر پرداخت نشده
        if not self.is_paid:
            self.payment_penalty_price = self.calculate_penalty()
            if self.payment_penalty_price:
                self.total_charge_month += self.payment_penalty_price

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
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name='شماره حساب', null=True, blank=True)
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
    base_charge = models.PositiveIntegerField(null=True, blank=True, verbose_name='مبلغ')

    payment_deadline_date = models.DateField(null=True, blank=True)
    payment_penalty = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    send_notification = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر')
    send_notification_date = models.DateField(null=True, blank=True, verbose_name='اعلام شارژ به کاربر')
    other_cost = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    send_sms = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر با پیامک')
    is_paid = models.BooleanField(default=False, verbose_name='وضعیت پرداخت')
    payment_date = models.DateField(verbose_name='', null=True, blank=True)
    payment_penalty_price = models.PositiveIntegerField(verbose_name='', null=True, blank=True)

    transaction_reference = models.CharField(max_length=20, null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    civil_charge = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.charge_name)

    from django.utils import timezone

    def calculate_penalty(self):
        if not self.payment_deadline_date or self.is_paid:
            return 0

        today = timezone.now().date()
        deadline = self.payment_deadline_date

        if today <= deadline:
            return 0

        delay_days = (today - deadline).days
        penalty_percent = self.payment_penalty or 0

        # محاسبه جریمه بر اساس درصد و تعداد روزها
        base_amount = self.total_charge_month or 0
        penalty_amount = int(base_amount * penalty_percent / 100 * delay_days)
        return penalty_amount

    def save(self, *args, **kwargs):
        people_count = getattr(self.unit, 'people_count', 0)
        area = getattr(self.unit, 'area', 0)

        self.total_charge_month = (
                (self.unit_variable_person_charge or 0) * people_count +
                (self.unit_variable_area_charge or 0) * area +
                (self.unit_fix_charge_per_unit or 0) +
                (self.extra_parking_charges or 0) +
                (self.other_cost or 0) +
                (self.civil_charge or 0)
        )

        # اضافه کردن جریمه دیرکرد اگر پرداخت نشده
        if not self.is_paid:
            self.payment_penalty_price = self.calculate_penalty()
            if self.payment_penalty_price:
                self.total_charge_month += self.payment_penalty_price

        super().save(*args, **kwargs)


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

    # نوع شارژ (نوع محاسبات)
    charge_type = models.CharField(
        max_length=50,
        choices=ChargeType.choices
    )

    # مبلغ نهایی
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    penalty_amount = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    total_charge_month = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    other_cost_amount = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    civil = models.PositiveIntegerField(verbose_name='شارژ عمرانی', default=0, null=True, blank=True)
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

    def __str__(self):
        return f"{self.get_charge_type_display()} - {self.amount:,}"

    def update_penalty(self, save=True):
        """
        محاسبه جریمه دیرکرد دقیقاً مشابه FixedChargeCalc
        """

        today = timezone.now().date()

        # ---------- ۱: مبلغ پایه دقیقاً مثل FixedChargeCalc ----------
        amount = self.amount or 0
        base_total = amount

        # ---------- ۲: اگر پرداخت شده → جریمه صفر ----------
        # if self.is_paid:
        #     if self.penalty_amount != 0:
        #         self.penalty_amount = 0
        #         self.total_charge_month = base_total
        #         if save:
        #             self.save(update_fields=['penalty_amount', 'total_charge_month'])
        #     return

        # ---------- ۳: اگر deadline ندارد ----------
        if not self.payment_deadline_date:
            return

        deadline = self.payment_deadline_date

        # ---------- ۴: اگر هنوز مهلت نگذشته ----------
        if today <= deadline:
            if self.penalty_amount != 0:
                self.penalty_amount = 0
                self.total_charge_month = base_total
                if save:
                    self.save(update_fields=['penalty_amount', 'total_charge_month'])
            return

        # ---------- ۵: تعداد روزهای دیرکرد ----------
        delay_days = (today - deadline).days

        # ---------- ۶: درصد جریمه مانند FixedChargeCalc ----------
        penalty_percent = getattr(self.related_object, 'payment_penalty', 0) or 0

        new_penalty = int((base_total * penalty_percent / 100) * delay_days)

        # ---------- ۷: اگر تغییری رخ داده ذخیره کن ----------
        if new_penalty != (self.penalty_amount or 0):
            self.penalty_amount = new_penalty
            self.total_charge_month = base_total + new_penalty
            if save:
                self.save(update_fields=['penalty_amount', 'total_charge_month'])


class Fund(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    doc_number = models.PositiveIntegerField(unique=True, editable=False, null=True, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    amount = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    debtor_amount = models.DecimalField(max_digits=12, decimal_places=0)
    creditor_amount = models.DecimalField(max_digits=12, decimal_places=0)
    final_amount = models.PositiveIntegerField(default=0)
    payment_gateway = models.CharField(max_length=100, null=True, blank=True)

    payment_date = models.DateField()
    transaction_no = models.CharField(max_length=15, null=True, blank=True)
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
