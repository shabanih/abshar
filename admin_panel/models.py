from django.db import models


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
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, verbose_name='گروه')
    date = models.DateField(verbose_name='تاریخ سند')
    doc_no = models.IntegerField(verbose_name='شماره سند')
    description = models.CharField(max_length=4000, verbose_name='شرح')
    amount = models.PositiveIntegerField(verbose_name='قیمت', null=True, blank=True, default='0')
    details = models.TextField(verbose_name='توضیحات', null=True, blank=True)
    document = models.FileField(upload_to='images/expense', verbose_name='تصاویر هزینه', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return self.doc_no
