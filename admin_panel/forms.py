from datetime import datetime

import jdatetime
from django import forms
from jalali_date import widgets
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget

from admin_panel.models import (Announcement, Expense, ExpenseCategory, Income, IncomeCategory, ReceiveMoney, PayMoney, \
                                Property, Maintenance, ChargeByPersonArea, ChargeByFixPersonArea, FixCharge, AreaCharge,
                                PersonCharge,
                                FixPersonCharge, FixAreaCharge, ChargeFixVariable)

from user_app.models import Unit, Bank, MyHouse

attr = {'class': 'form-control border-1 py-2 mb-4 '}
attr1 = {'class': 'form-control border-1 py-1 mb-4 '}
attr3 = {'class': 'form-control form-control-sm border-1'}
attr2 = {'class': 'form-control border-1 my-2 mb-4 ', 'placeholder': 'لطفا واحد را انتخاب کنید'}

error_message = {
    'required': "تکمیل این فیلد ضروری است!",
    'min_length': 'تعداد کاراکترهای وارد شده کمتر از حد مجاز است!',
    'max_length': 'تعداد کاراکترهای وارد شده بیشتر از حد مجاز است!',
}

CHOICES = {
    'True': 'فعال',
    'False': 'غیرفعال'
}


class announcementForm(forms.ModelForm):
    title = forms.CharField(error_messages=error_message, required=True, widget=forms.Textarea(attrs=attr),
                            label='عنوان اطلاعیه')

    slug = forms.SlugField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr),
                           label='عنوان در Url')
    is_active = forms.ChoiceField(label='فعال /غیرفعال نمودن اطلاعیه', required=True,
                                  error_messages=error_message, choices=CHOICES, widget=forms.Select(attrs=attr))

    class Meta:
        model = Announcement
        fields = ['title', 'slug', 'is_active']


RESIDENCE_STATUS_CHOICES = {
    '': '--- انتخاب کنید ---',
    'پر': 'پر',
    'خالی': 'خالی'
}

BEDROOMS_COUNT_CHOICES = {
    '': '--- انتخاب کنید ---', '1': '1', '2': '2', '3': '3', '4': '4',
}

FLOOR_CHOICES = {
    '': '--- انتخاب کنید ---', '1': '1', '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9',
    '10': '10',
}

AREA_CHOICES = {
    '': '--- انتخاب کنید ---', '90': '90', '120': '120', '130': '130', '150': '150',
}

PARKING_PLACE_CHOICES = {
    '': '--- انتخاب کنید ---', 'همکف': 'همکف', 'طبقه -1': 'طبقه -1', 'طبقه -2': 'طبقه -2', 'طبقه -3': 'طبقه -3',
}

PARKING_NUMBER_CHOICES = {
    ('', '--- انتخاب کنید ---'),
    ('B45', 'B45'),
    ('B52', 'B52'),
    ('B47', 'B47'),
}

PARKING_COUNT_CHOICES = {
    '': '--- انتخاب کنید ---', '1': '1', '2': '2', '3': '3',
}

BANK_CHOICES = {
    '': '--- انتخاب کنید ---', 'ملی': 'ملی', 'ملت': 'ملت', 'تجارت': 'تجارت', 'صادرات': 'صادرات', 'رسالت': 'رسالت',
    'صنعت و معدن': 'صنعت و معدن', 'کشاورزی': 'کشاورزی', 'مسکن': 'مسکن', 'رفاه': 'رفاه', 'سپه': 'سپه', 'سینا': 'سینا',
    'توسعه صادرات': 'توسعه صادرات', 'پست بانک': 'پست بانک', 'پاسارگاد': 'پاسارگاد', 'اقتصاد نوین': 'اقتصاد نوین',
    'پارسیان': 'پارسیان',
    'سامان': 'سامان', 'گردشگری': 'گردشگری', 'کارآفرین': 'کارآفرین', 'دی': 'دی', 'شهر': 'شهر',
    'ایران زمین': 'ایران زمین',
    'مهر ایران': 'مهر ایران',
}


class BankForm(forms.ModelForm):
    bank_name = forms.ChoiceField(error_messages=error_message, required=True, choices=BANK_CHOICES,
                                  widget=forms.Select(attrs=attr3), label='نام بانک')

    account_holder_name = forms.CharField(error_messages=error_message, required=True,
                                          widget=forms.TextInput(attrs=attr),
                                          label='نام صاحب حساب')
    account_no = forms.CharField(error_messages=error_message, required=True, widget=forms.NumberInput(attrs=attr),
                                 label='شماره حساب')
    sheba_number = forms.CharField(error_messages=error_message,
                                   max_length=24,
                                   min_length=24,
                                   required=False, widget=forms.TextInput(attrs=attr),
                                   label='شماره شبا')
    cart_number = forms.CharField(error_messages=error_message,
                                  max_length=16,
                                  min_length=16,
                                  required=False, widget=forms.NumberInput(attrs=attr),
                                  label='شماره کارت')
    initial_fund = forms.CharField(error_messages=error_message, required=True, widget=forms.NumberInput(attrs=attr),
                                   label='موجودی اولیه')

    class Meta:
        model = Bank
        fields = ('bank_name', 'account_holder_name', 'account_no', 'sheba_number', 'cart_number', 'initial_fund')


class MyHouseForm(forms.ModelForm):
    name = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr),
                           label='نام ساختمان')
    address = forms.CharField(error_messages=error_message, required=True,
                              widget=forms.TextInput(attrs=attr),
                              label='آدرس')
    account_number = forms.ModelChoiceField(queryset=Bank.objects.all(), widget=forms.Select(attrs=attr2),
                                            label="شماره حساب")
    is_active = forms.BooleanField(initial=True, required=False, label='فعال/غیرفعال')

    class Meta:
        model = MyHouse
        fields = ['name', 'address', 'account_number', 'is_active']


class UnitForm(forms.ModelForm):
    unit = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr1),
                           label='شماره واحد')
    unit_phone = forms.CharField(error_messages=error_message,
                                 max_length=8,
                                 min_length=8,
                                 required=False, widget=forms.TextInput(attrs=attr),
                                 label='شماره تلفن واحد')
    floor_number = forms.ChoiceField(error_messages=error_message, choices=FLOOR_CHOICES, required=True,
                                     widget=forms.Select(attrs=attr),
                                     label='شماره طبقه')
    area = forms.ChoiceField(error_messages=error_message, required=True, choices=AREA_CHOICES,
                             widget=forms.Select(attrs=attr),
                             label='متراژ')
    bedrooms_count = forms.ChoiceField(error_messages=error_message, choices=BEDROOMS_COUNT_CHOICES, required=True,
                                       widget=forms.Select(attrs=attr),
                                       label='تعداد خواب')

    parking_place = forms.ChoiceField(error_messages=error_message, choices=PARKING_PLACE_CHOICES, required=False,
                                      widget=forms.Select(attrs=attr),
                                      label='موقعیت پارکینگ اصلی')
    extra_parking_first = forms.CharField(error_messages=error_message, required=False,
                                      widget=forms.TextInput(attrs=attr),
                                      label=' پارکینگ اضافه اول')
    extra_parking_second = forms.CharField(error_messages=error_message, required=False,
                                      widget=forms.TextInput(attrs=attr),
                                      label=' پارکینگ اضافه دوم')

    parking_number = forms.CharField(
        error_messages=error_message,
        required=False,
        widget=forms.TextInput(attrs=attr),
        label='شماره پارکینگ'
    )
    parking_count = forms.ChoiceField(error_messages=error_message, choices=PARKING_COUNT_CHOICES, required=True,
                                      widget=forms.Select(attrs=attr),
                                      label='تعداد پارکینگ')
    unit_details = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'rows': 8}), required=False,
                                   label='توضیحات')
    owner_name = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr),
                                 label='نام ')
    owner_mobile = forms.CharField(error_messages=error_message,
                                   max_length=11,
                                   min_length=11,
                                   required=True, widget=forms.TextInput(attrs=attr),
                                   label='شماره تلفن ')
    owner_national_code = forms.CharField(error_messages=error_message, required=True,
                                          max_length=10,
                                          min_length=10,
                                          widget=forms.TextInput(attrs=attr),
                                          label='کد ملی ')
    owner_people_count = forms.CharField(error_messages=error_message, required=True,
                                         widget=forms.TextInput(attrs=attr),
                                         label='تعداد نفرات مالک')
    purchase_date = JalaliDateField(error_messages=error_message, widget=AdminJalaliDateWidget(attrs=attr),
                                    required=True,
                                    label='تاریخ خرید')

    status_residence = forms.ChoiceField(error_messages=error_message, choices=RESIDENCE_STATUS_CHOICES, required=True,
                                         widget=forms.Select(attrs=attr),
                                         label='وضعیت سکونت')
    is_owner = forms.ChoiceField(
        choices=[('', '--- انتخاب کنید ---'), ('True', 'بله'), ('False', 'خیر')],
        widget=forms.Select(attrs={'id': 'id_is_owner', 'class': 'form-control'}),
        label='واحد دارای مستاجر است؟'
    )
    owner_details = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'rows': 8}), required=False,
                                    label='توضیحات')
    renter_name = forms.CharField(error_messages=error_message, required=False, widget=forms.TextInput(attrs=attr),
                                  label='نام مستاجر')
    renter_mobile = forms.CharField(error_messages=error_message,
                                    required=False,
                                    max_length=11,
                                    min_length=11,
                                    widget=forms.TextInput(attrs=attr),
                                    label='شماره تلفن مستاجر')
    renter_national_code = forms.CharField(error_messages=error_message, required=False,
                                           max_length=10,
                                           min_length=10,
                                           widget=forms.TextInput(attrs=attr), label='کد ملی مستاجر')
    renter_people_count = forms.CharField(error_messages=error_message, required=False,
                                          widget=forms.TextInput(attrs=attr),
                                          label='تعداد نفرات')

    start_date = JalaliDateField(
        label='تاریخ شروع اجاره',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=False
    )
    end_date = JalaliDateField(
        label='تاریخ پایان اجاره',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=False
    )
    contract_number = forms.CharField(error_messages=error_message, required=False, widget=forms.TextInput(attrs=attr),
                                      label='شماره قرارداد')
    estate_name = forms.CharField(error_messages=error_message, required=False, widget=forms.TextInput(attrs=attr),
                                  label='نام اجاره دهنده')
    first_charge = forms.CharField(error_messages=error_message, required=False, widget=forms.TextInput(attrs=attr),
                                   label='شارژ اولیه')
    renter_details = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'rows': 8}), required=False,
                                     label='توضیحات')
    is_active = forms.BooleanField(required=False, initial=True, label='فعال/غیرفعال نمودن')
    mobile = forms.CharField(
        required=True,
        max_length=11,
        min_length=11,
        error_messages=error_message,
        label='نام کاربری',
        widget=forms.TextInput(attrs=attr)
    )
    password = forms.CharField(
        required=False,
        label='رمز عبور',
        widget=forms.PasswordInput(attrs=attr),
        help_text='رمز عبور باید شامل اعداد و حروف باشد'
    )
    confirm_password = forms.CharField(
        required=False,
        label='تایید رمز عبور',
        widget=forms.PasswordInput(attrs=attr),
        help_text='رمز عبور باید شامل اعداد و حروف باشد'
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "کلمه عبور و تکرار آن باید یکسان باشند.")

        is_owner = cleaned_data.get('is_owner')

        if cleaned_data.get('start_date') and cleaned_data.get('end_date'):
            start_date = cleaned_data.get('start_date')
            end_date = cleaned_data.get('end_date')

            if start_date > end_date:
                self.add_error('start_date', 'تاریخ شروع اجاره نباید از تاریخ پایان بزرگتر باشد.')

        if str(is_owner).lower() == 'true':
            required_fields_if_rented = [
                'renter_name', 'renter_mobile', 'renter_national_code', 'estate_name',
                'renter_people_count', 'start_date', 'end_date', 'contract_number', 'first_charge'
            ]
            for field in required_fields_if_rented:
                if not cleaned_data.get(field):
                    self.add_error(field, 'این فیلد الزامی است.')
        return cleaned_data

    class Meta:
        model = Unit
        fields = ['unit', 'floor_number', 'area', 'unit_details',
                  'bedrooms_count', 'parking_place', 'owner_name', 'owner_mobile',
                  'owner_national_code', 'unit_phone', 'owner_details',
                  'parking_number', 'parking_count', 'status_residence', 'purchase_date', 'renter_name',
                  'renter_national_code', 'renter_details','extra_parking_first', 'extra_parking_second',
                  'renter_mobile', 'is_owner', 'owner_people_count',
                  'renter_people_count', 'start_date', 'end_date', 'first_charge', 'contract_number',
                  'estate_name', 'is_active', 'mobile', 'password', 'confirm_password']

    def save(self, commit=True):
        instance = super().save(commit=False)

        is_owner = self.cleaned_data.get('is_owner') == 'False'

        if is_owner:
            # Owner is resident, clear renter fields
            instance.renter_name = ''
            instance.renter_mobile = ''
            instance.renter_national_code = ''
            instance.renter_people_count = ''
            instance.start_date = None
            instance.end_date = None
            instance.contract_number = ''
            instance.first_charge = 0
            instance.renter_details = ''
            # Set people_count from owner's info
            instance.people_count = self.cleaned_data.get('owner_people_count') or 0
        else:
            # We'll assign renter_people_count later
            instance.people_count = 0  # default for now

        if commit:
            instance.save()  # ✅ Save first so instance has a PK

            # ✅ Now you can access related renters
            if not is_owner:
                active_renter = instance.renters.filter(renter_is_active=True).last()
                if active_renter:
                    instance.people_count = active_renter.renter_people_count or 0
                    instance.save(update_fields=['people_count'])  # update only this field

        return instance


# ======================== Expense Forms =============================

class ExpenseForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=ExpenseCategory.objects.filter(is_active=True),
        widget=forms.Select(attrs=attr),
        empty_label="یک گروه انتخاب کنید",
        error_messages=error_message,
        required=True,
        label='موضوع هزینه'
    )
    # category = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr),
    #                            label='موضوع هزینه')
    amount = forms.CharField(error_messages=error_message, max_length=20, required=True,
                             widget=forms.TextInput(attrs=attr),
                             label='مبلغ')
    description = forms.CharField(error_messages=error_message, widget=forms.TextInput(attrs=attr), required=True,
                                  label='شرح سند')
    date = JalaliDateField(
        label='تاریخ ثبت سند',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=False
    )
    doc_no = forms.CharField(error_messages=error_message, max_length=10, widget=forms.TextInput(attrs=attr),
                             required=True,
                             label='شماره سند')
    document = forms.FileField(
        required=False,
        error_messages=error_message,
        widget=forms.ClearableFileInput(attrs=attr),
        label='تصویر سند'
    )
    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                              label='توضیحات ')

    class Meta:
        model = Expense
        fields = ['category', 'amount', 'date', 'description', 'doc_no', 'details', 'document']


class ExpenseCategoryForm(forms.ModelForm):
    title = forms.CharField(error_messages=error_message, widget=forms.TextInput(attrs=attr), required=True,
                            label='موضوع')
    is_active = forms.BooleanField(required=False, initial=True, label='فعال/غیرفعال')

    class Meta:
        model = ExpenseCategory
        fields = ['title', 'is_active']


class SearchExpenseForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=ExpenseCategory.objects.all(), required=False, label='گروه هزینه'
    )
    description = forms.CharField(
        max_length=200, required=False, label='شرح هزینه', widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    amount = forms.IntegerField(
        required=False, label=' مبلغ', widget=forms.TextInput(attrs=attr)
    )
    details = forms.CharField(
        required=False, label=' توضیحات', widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    date_from = JalaliDateField(
        label='از تاریخ',
        widget=AdminJalaliDateWidget(),
        error_messages=error_message, required=False
    )
    date_to = JalaliDateField(
        required=False,
        label='تا تاریخ',
        widget=AdminJalaliDateWidget()
    )
    doc_no = forms.IntegerField(
        required=False, label='شماره سند', widget=forms.TextInput(attrs={'class': 'form-control'})
    )


# =============================== Income Forms ===================================

class IncomeForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=IncomeCategory.objects.filter(is_active=True),
        widget=forms.Select(attrs=attr),
        empty_label="یک گروه انتخاب کنید",
        error_messages=error_message,
        required=True,
        label='موضوع درآمد'
    )
    # category = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr),
    #                            label='موضوع هزینه')
    amount = forms.CharField(error_messages=error_message, max_length=20, required=True,
                             widget=forms.TextInput(attrs=attr),
                             label='مبلغ')
    description = forms.CharField(error_messages=error_message, widget=forms.TextInput(attrs=attr), required=True,
                                  label='شرح سند')
    doc_date = JalaliDateField(
        label='تاریخ ثبت سند',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=False
    )
    doc_number = forms.CharField(error_messages=error_message, max_length=10, widget=forms.TextInput(attrs=attr),
                                 required=True,
                                 label='شماره سند')
    document = forms.FileField(
        required=False,
        error_messages=error_message,
        widget=forms.ClearableFileInput(attrs=attr),
        label='تصویر سند'
    )
    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                              label='توضیحات ')

    class Meta:
        model = Income
        fields = ['category', 'amount', 'doc_date', 'description', 'doc_number', 'details', 'document']


class IncomeCategoryForm(forms.ModelForm):
    subject = forms.CharField(error_messages=error_message, widget=forms.TextInput(attrs=attr), required=True,
                              label='موضوع درآمد')
    is_active = forms.BooleanField(required=False, initial=True, label='فعال/غیرفعال')

    class Meta:
        model = IncomeCategory
        fields = ['subject', 'is_active']


class SearchIncomeForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=ExpenseCategory.objects.all(), required=False, label='گروه درآمد'
    )
    description = forms.CharField(
        max_length=200, required=False, label='شرح درآمد', widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    amount = forms.IntegerField(
        required=False, label=' مبلغ', widget=forms.TextInput(attrs=attr)
    )
    details = forms.CharField(
        required=False, label=' توضیحات', widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    date_from = JalaliDateField(
        label='از تاریخ',
        widget=AdminJalaliDateWidget(),
        error_messages=error_message, required=False
    )
    date_to = JalaliDateField(
        required=False,
        label='تا تاریخ',
        widget=AdminJalaliDateWidget()
    )
    doc_number = forms.IntegerField(
        required=False, label='شماره سند', widget=forms.TextInput(attrs={'class': 'form-control'})
    )


# ================================ Receive Forms ======================

class ReceiveMoneyForm(forms.ModelForm):
    bank = forms.ModelChoiceField(
        queryset=MyHouse.objects.filter(is_active=True),
        widget=forms.Select(attrs=attr),
        empty_label="شماره حساب را انتخاب کنید",
        error_messages=error_message,
        required=True,
        label='شماره حساب بانکی'
    )
    payer_name = forms.CharField(
        max_length=200, required=False, label='پرداخت کننده ', widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    amount = forms.CharField(error_messages=error_message, max_length=20, required=True,
                             widget=forms.TextInput(attrs=attr),
                             label='مبلغ')
    description = forms.CharField(error_messages=error_message, widget=forms.TextInput(attrs=attr), required=True,
                                  label='شرح سند')
    doc_date = JalaliDateField(
        label='تاریخ ثبت سند',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=False
    )
    doc_number = forms.CharField(error_messages=error_message, max_length=10, widget=forms.TextInput(attrs=attr),
                                 required=True,
                                 label='شماره سند')
    document = forms.FileField(
        required=False,
        error_messages=error_message,
        widget=forms.ClearableFileInput(attrs=attr),
        label='تصویر سند'
    )
    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                              label='توضیحات ')
    is_active = forms.BooleanField(required=False)

    class Meta:
        model = ReceiveMoney
        fields = ['bank', 'amount', 'doc_date', 'description', 'doc_number',
                  'details', 'document', 'is_active', 'payer_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bank'].queryset = MyHouse.objects.filter(is_active=True)


class PayerMoneyForm(forms.ModelForm):
    bank = forms.ModelChoiceField(
        queryset=MyHouse.objects.filter(is_active=True),
        widget=forms.Select(attrs=attr),
        empty_label="یک گروه انتخاب کنید",
        error_messages=error_message,
        required=True,
        label='شماره حساب بانکی'
    )
    receiver_name = forms.CharField(
        max_length=200, required=False, label='شخص دریافت کننده',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    amount = forms.CharField(error_messages=error_message, max_length=20, required=True,
                             widget=forms.TextInput(attrs=attr),
                             label='مبلغ')
    description = forms.CharField(error_messages=error_message, widget=forms.TextInput(attrs=attr), required=True,
                                  label='شرح سند')
    document_date = JalaliDateField(
        label='تاریخ ثبت سند',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=False
    )
    document_number = forms.CharField(error_messages=error_message, max_length=10, widget=forms.TextInput(attrs=attr),
                                      required=True,
                                      label='شماره سند')
    document = forms.FileField(
        required=False,
        error_messages=error_message,
        widget=forms.ClearableFileInput(attrs=attr),
        label='تصویر سند'
    )
    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                              label='توضیحات ')
    is_active = forms.BooleanField(required=False)

    class Meta:
        model = PayMoney
        fields = ['bank', 'amount', 'document_date', 'description', 'document_number',
                  'details', 'document', 'is_active', 'receiver_name']


PROPERTY_CHOICES = {
    '': '--- انتخاب کنید ---', 'عدد': 'عدد', 'دستگاه': 'دستگاه', 'تخته': 'تخته', 'کپسول': 'کپسول',
}


class PropertyForm(forms.ModelForm):
    property_name = forms.CharField(
        max_length=200, required=True, label='نام اموال', widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    property_unit = forms.ChoiceField(error_messages=error_message, required=True, choices=PROPERTY_CHOICES,
                                      widget=forms.Select(attrs=attr3),
                                      label='واحد')
    property_location = forms.CharField(error_messages=error_message, widget=forms.TextInput(attrs=attr), required=True,
                                        label='موقعیت')
    property_purchase_date = JalaliDateField(
        label='تاریخ خرید',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=True
    )
    property_code = forms.CharField(error_messages=error_message, max_length=10, widget=forms.TextInput(attrs=attr),
                                    required=True,
                                    label='کد اموال')
    property_price = forms.IntegerField(error_messages=error_message, widget=forms.NumberInput(attrs=attr),
                                        required=True,
                                        label='ارزش')
    document = forms.FileField(
        required=False,
        error_messages=error_message,
        widget=forms.ClearableFileInput(attrs=attr),
        label='تصویر اموال'
    )
    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                              label='توضیحات ')

    class Meta:
        model = Property
        fields = ['property_name', 'property_code', 'property_unit', 'property_price', 'property_location',
                  'property_purchase_date', 'details', 'document']


MAINTENANCE_CHOICES = {
    ' ': '--- انتخاب کنید ---', 'تکمیل شده': 'تکمیل شده', 'در حال انجام': 'در حال انجام', 'تکمیل ناقص': 'تکمیل ناقص'
}


class MaintenanceForm(forms.ModelForm):
    maintenance_description = forms.CharField(
        max_length=200, required=True, label='شرح کار', widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    maintenance_start_date = JalaliDateField(
        label='تاریخ شروع',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=True
    )
    maintenance_end_date = JalaliDateField(
        label='تاریخ پایان',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=True
    )

    maintenance_price = forms.CharField(error_messages=error_message, max_length=20, widget=forms.TextInput(attrs=attr),
                                        required=True,
                                        label='اجرت و دستمزد')
    service_company = forms.CharField(error_messages=error_message, max_length=100,
                                      widget=forms.TextInput(attrs=attr),
                                      required=True,
                                      label='شرکت خدماتی')
    maintenance_document_no = forms.CharField(error_messages=error_message, max_length=20,
                                              widget=forms.TextInput(attrs=attr),
                                              required=True,
                                              label='شماره فاکتور')
    maintenance_status = forms.ChoiceField(error_messages=error_message, required=True, choices=MAINTENANCE_CHOICES,
                                           widget=forms.Select(attrs=attr3),
                                           label='آخرین وضعیت')
    document = forms.FileField(
        required=False,
        error_messages=error_message,
        widget=forms.ClearableFileInput(attrs=attr),
        label='تصویر سند'
    )
    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                              label='توضیحات ')

    class Meta:
        model = Maintenance
        fields = ['maintenance_description', 'maintenance_start_date', 'maintenance_end_date', 'maintenance_price',
                  'maintenance_status', 'service_company', 'details', 'document', 'maintenance_document_no']


# ============================== Charge Forms ===================================

class FixChargeForm(forms.ModelForm):
    name = forms.CharField(error_messages=error_message, max_length=20, widget=forms.TextInput(attrs=attr),
                           required=True,
                           label='عنوان شارژ ')
    fix_amount = forms.IntegerField(error_messages=error_message,
                                    widget=forms.TextInput(attrs=attr),
                                    required=True,
                                    label='مبلغ شارژ به ازای هر واحد')
    civil = forms.IntegerField(error_messages=error_message,
                               widget=forms.TextInput(attrs=attr),
                               required=False, min_value=0,
                               label='شارژ عمرانی')
    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                              label='توضیحات ')

    def clean_civil_charge(self):
        value = self.cleaned_data.get('civil')
        if value in [None, '']:  # empty string or None
            return 0
        return value

    class Meta:
        model = FixCharge
        fields = ['name', 'fix_amount', 'details', 'civil']


class AreaChargeForm(forms.ModelForm):
    name = forms.CharField(error_messages=error_message, max_length=20, widget=forms.TextInput(attrs=attr),
                           required=True,
                           label='عنوان شارژ ')
    area_amount = forms.IntegerField(error_messages=error_message,
                                     widget=forms.TextInput(attrs=attr),
                                     required=True,
                                     label='مبلغ شارژ به اساس متراژ')
    civil = forms.IntegerField(error_messages=error_message,
                               widget=forms.TextInput(attrs=attr),
                               required=False, min_value=0,
                               label='شارژ عمرانی')
    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                              label='توضیحات ')

    def clean_civil_charge(self):
        value = self.cleaned_data.get('civil')
        if value in [None, '']:  # empty string or None
            return 0
        return value

    class Meta:
        model = AreaCharge
        fields = ['name', 'area_amount', 'details', 'civil']


class PersonChargeForm(forms.ModelForm):
    name = forms.CharField(error_messages=error_message, max_length=20, widget=forms.TextInput(attrs=attr),
                           required=True,
                           label='عنوان شارژ ')
    person_amount = forms.IntegerField(error_messages=error_message,
                                       widget=forms.TextInput(attrs=attr),
                                       required=True,
                                       label='مبلغ شارژ به ازای هر نفر')
    civil = forms.IntegerField(error_messages=error_message,
                               widget=forms.TextInput(attrs=attr),
                               required=False, min_value=0,
                               label='شارژ عمرانی')
    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                              label='توضیحات ')

    def clean_civil_charge(self):
        value = self.cleaned_data.get('civil')
        if value in [None, '']:  # empty string or None
            return 0
        return value

    class Meta:
        model = PersonCharge
        fields = ['name', 'person_amount', 'details', 'civil']


class FixAreaChargeForm(forms.ModelForm):
    name = forms.CharField(error_messages=error_message, max_length=20, widget=forms.TextInput(attrs=attr),
                           required=True,
                           label='عنوان شارژ ')
    fix_charge_amount = forms.IntegerField(error_messages=error_message,
                                           widget=forms.TextInput(attrs=attr),
                                           required=True,
                                           label=' شارژ ثابت')
    area_amount = forms.IntegerField(error_messages=error_message,
                                     widget=forms.TextInput(attrs=attr),
                                     required=True,
                                     label='مبلغ شارژ به اساس متراژ')
    civil = forms.IntegerField(error_messages=error_message,
                               widget=forms.TextInput(attrs=attr),
                               required=False, min_value=0,
                               label='شارژ عمرانی')
    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                              label='توضیحات ')

    def clean_civil_charge(self):
        value = self.cleaned_data.get('civil_charge')
        if value in [None, '']:  # empty string or None
            return 0
        return value

    class Meta:
        model = FixAreaCharge
        fields = ['name', 'area_amount', 'details', 'civil', 'fix_charge_amount']


class FixPersonChargeForm(forms.ModelForm):
    name = forms.CharField(error_messages=error_message, max_length=20, widget=forms.TextInput(attrs=attr),
                           required=True,
                           label='عنوان شارژ ')
    fix_charge_amount = forms.IntegerField(error_messages=error_message,
                                           widget=forms.TextInput(attrs=attr),
                                           required=True,
                                           label=' شارژ ثابت')
    person_amount = forms.IntegerField(error_messages=error_message,
                                       widget=forms.TextInput(attrs=attr),
                                       required=True,
                                       label='مبلغ شارژ به ازای هر نفر')
    civil = forms.IntegerField(error_messages=error_message,
                               widget=forms.TextInput(attrs=attr),
                               required=False, min_value=0,
                               label='شارژ عمرانی')
    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                              label='توضیحات ')

    def clean_civil_charge(self):
        value = self.cleaned_data.get('civil_charge')
        if value in [None, '']:  # empty string or None
            return 0
        return value

    class Meta:
        model = FixPersonCharge
        fields = ['name', 'person_amount', 'details', 'civil', 'fix_charge_amount']


class PersonAreaChargeForm(forms.ModelForm):
    name = forms.CharField(error_messages=error_message, max_length=20, widget=forms.TextInput(attrs=attr),
                           required=True,
                           label='عنوان شارژ ')
    person_amount = forms.IntegerField(error_messages=error_message,
                                       widget=forms.TextInput(attrs=attr),
                                       required=True,
                                       label='مبلغ شارژ نفر')
    area_amount = forms.IntegerField(error_messages=error_message,
                                     widget=forms.TextInput(attrs=attr),
                                     required=True,
                                     label='مبلغ شارژ هر متر')
    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                              label='توضیحات ')
    civil = forms.IntegerField(error_messages=error_message,
                               widget=forms.TextInput(attrs=attr),
                               required=False,
                               label='شارژ عمرانی(تومان)')

    # def clean_civil_charge(self):
    #     value = self.cleaned_data.get('civil_charge')
    #     if value in [None, '']:  # empty string or None
    #         return 0
    #     return value

    class Meta:
        model = ChargeByPersonArea
        fields = ['name', 'area_amount', 'details', 'person_amount', 'civil']


class PersonAreaFixChargeForm(forms.ModelForm):
    name = forms.CharField(error_messages=error_message, max_length=20, widget=forms.TextInput(attrs=attr),
                           required=True,
                           label='عنوان شارژ ')
    fix_charge_amount = forms.IntegerField(error_messages=error_message,
                                           widget=forms.TextInput(attrs=attr),
                                           required=True,
                                           label=' شارژ ثابت')
    person_amount = forms.IntegerField(error_messages=error_message,
                                       widget=forms.TextInput(attrs=attr),
                                       required=True,
                                       label='مبلغ شارژ نفر')
    area_amount = forms.IntegerField(error_messages=error_message,
                                     widget=forms.TextInput(attrs=attr),
                                     required=True,
                                     label='مبلغ شارژ هر متر')
    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                              label='توضیحات ')
    civil = forms.IntegerField(error_messages=error_message,
                               widget=forms.TextInput(attrs=attr),
                               required=False, min_value=0,
                               label='شارژ عمرانی')

    class Meta:
        model = ChargeByFixPersonArea
        fields = ['name', 'area_amount', 'details', 'person_amount', 'civil', 'fix_charge_amount']


class VariableFixChargeForm(forms.ModelForm):
    name = forms.CharField(error_messages=error_message, max_length=20, widget=forms.TextInput(attrs=attr),
                           required=True,
                           label='عنوان شارژ ')

    unit_fix_amount = forms.IntegerField(error_messages=error_message,
                                       widget=forms.TextInput(attrs=attr),
                                       required=True,
                                       label='شارژ ثابت به ازای هر واحد')
    extra_parking_amount = forms.IntegerField(error_messages=error_message,
                                              widget=forms.TextInput(attrs=attr),
                                              required=False,
                                              label='هزینه اجاره پارکینگ ')
    unit_variable_person_amount = forms.IntegerField(error_messages=error_message,
                                              widget=forms.TextInput(attrs=attr),
                                              required=True,
                                              label='شارژ متغیر به ازای هر نفر')
    unit_variable_area_amount = forms.IntegerField(error_messages=error_message,
                                                   widget=forms.TextInput(attrs=attr),
                                                   required=True,
                                                   label='شارژ متغیر به ازای هر متر')

    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                              label='توضیحات ')
    civil = forms.IntegerField(error_messages=error_message,
                               widget=forms.TextInput(attrs=attr),
                               required=False, min_value=0,
                               label='سایر هزینه ها')

    other_cost_amount = forms.IntegerField(error_messages=error_message,
                               widget=forms.TextInput(attrs=attr),
                               required=False, min_value=0,
                               label='شارژ عمرانی')

    class Meta:
        model = ChargeFixVariable
        fields = ['name',  'extra_parking_amount', 'unit_fix_amount', 'unit_variable_area_amount',
                  'unit_variable_person_amount', 'civil', 'details', 'other_cost_amount']

