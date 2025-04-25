from django import forms
from jalali_date import widgets
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget

from admin_panel.models import Announcement, Expense, ExpenseCategory
from user_app.models import Unit

attr = {'class': 'form-control border-1 py-2 mb-4 '}
attr1 = {'class': 'form-control border-1 py-1 mb-4 '}
attr2 = {'class': 'form-control border-1 my-2 mb-4 ', 'placeholder': 'لطفا واحد را انتخاب گنید'}

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

    parking_place = forms.ChoiceField(error_messages=error_message, choices=PARKING_PLACE_CHOICES, required=True,
                                      widget=forms.Select(attrs=attr),
                                      label='موقعیت پارکینگ')

    parking_number = forms.CharField(
        error_messages=error_message,
        required=True,
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
                                    max_length=11,
                                    min_length=11,
                                    required=False, widget=forms.TextInput(attrs=attr),
                                    label='شماره تلفن مستاجر')
    renter_national_code = forms.CharField(error_messages=error_message, required=False,
                                           max_length=10,
                                           min_length=10,
                                           widget=forms.TextInput(attrs=attr), label='کد ملی مستاجر')
    people_count = forms.CharField(error_messages=error_message, required=False, widget=forms.TextInput(attrs=attr),
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
    is_active = forms.BooleanField(required=False, label='فعال/غیرفعال نمودن')

    def clean(self):
        cleaned_data = super().clean()
        is_owner = cleaned_data.get('is_owner')

        if is_owner == 'True':
            required_fields_if_rented = [
                'renter_name', 'renter_mobile', 'renter_national_code', 'estate_name',
                'people_count', 'start_date', 'end_date', 'contract_number', 'first_charge'
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
                  'renter_national_code', 'renter_details',
                  'renter_mobile', 'is_owner',
                  'people_count', 'start_date', 'end_date', 'first_charge', 'contract_number',
                  'estate_name', 'is_active']

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.cleaned_data.get('is_owner') == 'False':
            # Exclude renter fields when owner is 'True'
            instance.renter_name = ''
            instance.renter_mobile = ''
            instance.renter_national_code = ''
            instance.people_count = ''
            instance.start_date = None
            instance.end_date = None
            instance.contract_number = ''
            instance.first_charge = 0
            instance.renter_details = ''
        if commit:
            instance.save()  # Commit the changes to the DB
        return instance


# ======================== Expense Forms =============================

class ExpenseForm(forms.ModelForm):
    category = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr),
                               label='موضوع هزینه')
    amount = forms.CharField(error_messages=error_message, max_length=20, required=True,
                             widget=forms.TextInput(attrs=attr),
                             label='مبلغ')
    description = forms.CharField(error_messages=error_message, widget=forms.TextInput(attrs=attr), required=False,
                                  label='شرح سند')
    date = JalaliDateField(
        label='تاریخ ثبت سند',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=True
    )
    doc_no = forms.CharField(error_messages=error_message, widget=forms.TextInput(attrs=attr), required=True,
                             label='شماره سند')
    document = forms.FileField(required=True, error_messages=error_message, label='تصویر سند')
    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
                              label='توضیحات ')

    class Meta:
        model = Expense
        fields = ['category', 'amount', 'date', 'description', 'doc_no', 'details', 'document']


class ExpenseCategoryForm(forms.ModelForm):
    title = forms.CharField(error_messages=error_message, widget=forms.TextInput(attrs=attr), required=True,
                            label='موضوع')
    is_active = forms.BooleanField(required=True, widget=forms.CheckboxInput(attrs=attr), label='فعال/غیرفعال')

    class Meta:
        model = ExpenseCategory
        fields = ['title', 'is_active']
