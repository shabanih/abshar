import json

from django.db import models
from django.utils.safestring import mark_safe

from user_app.models import MyHouse


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
# class ReceiveMoney(models.Model):
#     bank = models.ForeignKey(MyHouse, on_delete=models.CASCADE, related_name='شماره حساب')
#     receiver_name = models.CharField(max_length=200, verbose_name='پرداخت کننده')
#     doc_date = models.DateField(verbose_name='تاریخ سند')
#     doc_number = models.IntegerField(verbose_name='شماره سند')
#     description = models.CharField(max_length=4000, verbose_name='شرح')
#     amount = models.PositiveIntegerField(verbose_name='قیمت', null=True, blank=True, default=0)
#     details = models.TextField(verbose_name='توضیحات', null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
#     is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')
#
#     def __str__(self):
#         return str(self.receiver_name)
