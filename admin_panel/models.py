import json

from django.db import models
from django.utils.safestring import mark_safe

from user_app.models import MyHouse, Unit, User


class Announcement(models.Model):
    title = models.CharField(max_length=270, verbose_name='عنوان')
    slug = models.SlugField(db_index=True, default='', null=True, max_length=200, verbose_name='عنوان در url')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return self.title


class ExpenseCategory(models.Model):
    title = models.CharField(max_length=100, verbose_name='نام')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return self.title


class Expense(models.Model):
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
    subject = models.CharField(max_length=100, verbose_name='نام')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return self.subject


class Income(models.Model):
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
    bank = models.ForeignKey(MyHouse, on_delete=models.CASCADE, verbose_name='شماره حساب')
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
    bank = models.ForeignKey(MyHouse, on_delete=models.CASCADE, verbose_name='شماره حساب')
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


# =========================== property Views ====================
class Property(models.Model):
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
class FixedChargeCalc(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charge_fix')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='charge_fix')
    charge_name = models.CharField(max_length=100, verbose_name='عنوان شارژ', null=True, blank=True)
    amount = models.PositiveIntegerField(verbose_name='مبلغ')
    unit_count = models.PositiveIntegerField(verbose_name='تعداد واحدها', null=True, blank=True)
    civil_charge = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)
    total_charge_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل ماهانه')
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    send_notification = models.BooleanField(default=False, verbose_name='اعلام شارژ به کاربر', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return f"{self.charge_name or 'شارژ'} - {self.amount} تومان"


class AreaChargeCalc(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charge_area')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='charge_area')
    charge_name = models.CharField(max_length=100, verbose_name='عنوان شارژ', null=True, blank=True)
    area_amount = models.PositiveIntegerField(verbose_name='مبلغ')
    unit_count = models.PositiveIntegerField(verbose_name='تعداد واحدها', null=True, blank=True)
    total_area = models.PositiveIntegerField(verbose_name='متراژ کل', null=True, blank=True)
    final_area_amount = models.PositiveIntegerField(verbose_name='مبلغ شارژ نهایی', null=True, blank=True)
    civil_charge = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)
    total_charge_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل ماهانه')
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.area_amount)


class PersonChargeCalc(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charge_person')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='charge_person')
    charge_name = models.CharField(max_length=100, verbose_name='عنوان شارژ', null=True, blank=True)
    person_amount = models.PositiveIntegerField(verbose_name='مبلغ')
    final_person_amount = models.PositiveIntegerField(verbose_name='مبلغ شارژ نهایی', null=True, blank=True)
    civil_charge = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)
    unit_count = models.PositiveIntegerField(null=True, blank=True, verbose_name='تعداد واحدها')
    total_people = models.PositiveIntegerField(null=True, blank=True, verbose_name='تعداد نفرات')
    total_charge_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل ماهانه')
    total_charge_year = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل سالیانه')
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.person_amount)


class FixPersonChargeCalc(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charge_fix_person')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='charge_fix_person')
    charge_name = models.CharField(max_length=100, verbose_name='عنوان شارژ', null=True, blank=True)
    fix_charge = models.PositiveIntegerField(verbose_name='شارژ ثابت', null=True, blank=True)
    person_amount = models.PositiveIntegerField(verbose_name='شارژ به ازای نفرات', null=True, blank=True)
    final_person_amount = models.PositiveIntegerField(verbose_name='مبلغ شارژ نهایی', null=True, blank=True)
    unit_count = models.PositiveIntegerField(null=True, blank=True, verbose_name='تعداد واحدها')
    total_people = models.PositiveIntegerField(null=True, blank=True, verbose_name='تعداد نفرات')
    civil_charge = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)
    total_charge_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل ماهانه')
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.charge_name)


class FixAreaChargeCalc(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charge_fix_area')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='charge_fix_area')
    charge_name = models.CharField(max_length=100, verbose_name='عنوان شارژ', null=True, blank=True)
    fix_charge = models.PositiveIntegerField(verbose_name='شارژ ثابت', null=True, blank=True)
    area_amount = models.PositiveIntegerField(verbose_name='شارژ به ازای متراژ', null=True, blank=True)
    unit_count = models.PositiveIntegerField(verbose_name='تعداد واحدها', null=True, blank=True)
    total_area = models.PositiveIntegerField(verbose_name='متراژ کل', null=True, blank=True)
    final_person_amount = models.PositiveIntegerField(verbose_name='مبلغ شارژ نهایی', null=True, blank=True)
    civil_charge = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)
    total_charge_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل ماهانه')
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.charge_name)


class ChargeByPersonArea(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charge_by_person_area')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='charge_by_person_area')
    charge_name = models.CharField(max_length=100, verbose_name='عنوان شارژ', null=True, blank=True)
    person_charge = models.PositiveIntegerField(verbose_name='شارژ به ازای نفرات')
    area_charge = models.PositiveIntegerField(verbose_name='شارژ به ازای متراژ')
    unit_count = models.PositiveIntegerField(verbose_name='تعداد واحدها', null=True, blank=True)
    total_people = models.PositiveIntegerField(verbose_name=' کل نفرات', null=True, blank=True)
    total_area = models.PositiveIntegerField(verbose_name='متراژ کل', null=True, blank=True)
    final_person_amount = models.PositiveIntegerField(verbose_name='مبلغ شارژ نهایی', null=True, blank=True)
    total_charge_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل ماهانه')
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    civil_charge = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return str(self.charge_name)


class ChargeByFixPersonArea(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charge_by_fix_person_area')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='charge_by_fix_person_area')
    charge_name = models.CharField(max_length=100, verbose_name='عنوان شارژ', null=True, blank=True)
    fix_charge = models.PositiveIntegerField(verbose_name='شارژ ثابت', null=True, blank=True)
    person_charge = models.PositiveIntegerField(verbose_name='شارژ به ازای نفرات')
    area_charge = models.PositiveIntegerField(verbose_name='شارژ به ازای متراژ')
    unit_count = models.PositiveIntegerField(verbose_name='تعداد واحدها', null=True, blank=True)
    total_people = models.PositiveIntegerField(verbose_name=' کل نفرات', null=True, blank=True)
    total_area = models.PositiveIntegerField(verbose_name='متراژ کل', null=True, blank=True)
    final_person_amount = models.PositiveIntegerField(verbose_name='مبلغ شارژ نهایی', null=True, blank=True)
    total_charge_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل ماهانه')
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)
    civil_charge = models.PositiveIntegerField(verbose_name='شارژ عمرانی', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return str(self.charge_name)


class ChargeCalcFixVariable(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charge_calc', null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='charge_calc_fix', null=True, blank=True)
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='expense_charge', null=True, blank=True)
    charge_name = models.CharField(max_length=100, verbose_name='نام شارژ', null=True, blank=True)
    fix_charge = models.PositiveIntegerField(verbose_name='شارژ ثابت', null=True, blank=True)
    unit_count = models.PositiveIntegerField(verbose_name='تعداد واحدها', null=True, blank=True)
    total_people = models.PositiveIntegerField(verbose_name=' کل نفرات', null=True, blank=True)
    total_area = models.PositiveIntegerField(verbose_name='متراژ کل', null=True, blank=True)
    unit_fix_amount = models.PositiveIntegerField(verbose_name='مبلغ شارژ ثابت', null=True, blank=True)
    unit_variable_amount_person = models.PositiveIntegerField(verbose_name='مبلغ شارژ متغیر هر نفر', null=True, blank=True)
    unit_variable_amount_area = models.PositiveIntegerField(verbose_name='مبلغ شارژ متغیر هر متر', null=True, blank=True)
    elevator_fix_cost = models.PositiveIntegerField(verbose_name='هزینه 60% آسانسور', null=True, blank=True)
    elevator_variable_cost = models.PositiveIntegerField(verbose_name='هزینه 40% آسانسور', null=True, blank=True)
    total_charge_month = models.PositiveIntegerField(null=True, blank=True, verbose_name='شارژ کل ماهانه')

    # Variable Charge
    salary = models.PositiveIntegerField(verbose_name='هزینه حقوق و دستمزد', null=True, blank=True)
    elevator_cost = models.PositiveIntegerField(verbose_name='هزینه  آسانسور', null=True, blank=True)
    public_electricity = models.PositiveIntegerField(verbose_name='هزینه برق عمومی', null=True, blank=True)
    common_expenses = models.PositiveIntegerField(verbose_name='هزینه های سالیانه عمومی(روشنایی،نظافت و ...)', null=True, blank=True)
    facility_cost = models.PositiveIntegerField(verbose_name='هزینه سالیانه تاسیسات', null=True, blank=True)
    extinguished_cost = models.PositiveIntegerField(verbose_name='هزینه سالیانه آتش نشانس', null=True, blank=True)
    camera_cost = models.PositiveIntegerField(verbose_name='هزینه سالیانه دوربین', null=True, blank=True)
    insurance_cost = models.PositiveIntegerField(verbose_name='هزینه سالیانه بیمه', null=True, blank=True)
    office_cost = models.PositiveIntegerField(verbose_name='هزینه اداری و دفتری', null=True, blank=True)
    green_space_cost = models.PositiveIntegerField(verbose_name='هزینه فضای سبز', null=True, blank=True)
    # Fix Charge

    public_water = models.PositiveIntegerField(verbose_name='هزینه آب مشاع', null=True, blank=True)
    public_gas = models.PositiveIntegerField(verbose_name='هزینه گاز مشاع', null=True, blank=True)

    civil_charge = models.PositiveIntegerField(verbose_name='هزینه عمرانی', null=True, blank=True)
    details = models.CharField(max_length=4000, verbose_name='', null=True, blank=True)

    # payment_deadline = models.DateField(verbose_name='مهلت پرداخت')
    # surcharge = models.PositiveIntegerField(verbose_name='جریمه عدم پرداخت')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return str(self.charge_name)
