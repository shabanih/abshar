from django import forms
from jalali_date import widgets
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget

from admin_panel.models import Announcement
from user_app.models import Unit, Renter

attr = {'class': 'form-control border-1 py-2 mb-4 '}
attr1 = {'class': 'form-control border-1 py-1 mb-4 '}
attr2 = {'class': 'form-control border-1 my-2 mb-4 ', 'placeholder': 'لطفا واحد را انتخاب گنید'}


error_message = {
    'required': "تکمیل کردن این فیلد ضروری است!"
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


STATUS_CHOICES = {
    'True': 'پر',
    'False': 'خالی'
}

BEDROOMS_COUNT_CHOICES = {
    '1': '1', '2': '2', '3': '3', '4': '4',
}

FLOOR_CHOICES = {
    '1': '1', '2': '2', '3': '3', '4': '4',  '5': '5', '6': '6', '7': '7', '8': '8',  '9': '9', '10': '10',
}

AREA_CHOICES = {
    '1': '90', '2': '120', '3': '130', '4': '150',
}

PARKING_PLACE_CHOICES = {
  '1': 'همکف', '2': 'طبقه -1', '3': 'طبقه -2', '4': 'طبقه -3',
}

PARKING_NUMBER_CHOICES = {
    '1': 'B45', '2': 'B52', '3': 'B47',
}

PARKING_COUNT_CHOICES = {
    '1': '1', '2': '2', '3': '3',
}


class UnitForm(forms.ModelForm):
    unit = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr1),
                           label='شماره واحد')
    unit_phone = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr1),
                                 label='شماره تلفن واحد')
    floor_number = forms.ChoiceField(error_messages=error_message, choices=FLOOR_CHOICES, required=True, widget=forms.Select(attrs=attr),
                                   label='شماره طبقه')
    area = forms.ChoiceField(error_messages=error_message, required=True, choices=AREA_CHOICES, widget=forms.Select(attrs=attr),
                           label='متراژ')
    bedrooms_count = forms.ChoiceField(error_messages=error_message, choices=BEDROOMS_COUNT_CHOICES, required=True, widget=forms.Select(attrs=attr),
                                     label='تعداد خواب')

    parking_place = forms.ChoiceField(error_messages=error_message, choices=PARKING_PLACE_CHOICES, required=True, widget=forms.Select(attrs=attr),
                                    label='موقعیت پارکینگ')
    parking_number = forms.ChoiceField(error_messages=error_message, choices=PARKING_NUMBER_CHOICES, required=True, widget=forms.Select(attrs=attr),
                                     label='شماره پارکینگ')
    parking_count = forms.ChoiceField(error_messages=error_message, choices=PARKING_COUNT_CHOICES, required=True, widget=forms.Select(attrs=attr),
                                    label='تعداد پارکینگ')
    owner_name = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr),
                                 label='نام ')
    owner_mobile = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr),
                                   label='شماره تلفن ')
    owner_national_code = forms.CharField(error_messages=error_message, required=True,
                                          widget=forms.TextInput(attrs=attr),
                                          label='کد ملی ')
    purchase_date = forms.DateField(error_messages=error_message, widget=forms.DateInput(attrs=attr),required=True,
                                    label='تاریخ خرید')
    status = forms.ChoiceField(error_messages=error_message,choices=CHOICES, required=True,
                               widget=forms.Select(attrs=attr),
                               label='وضعیت واحد')

    class Meta:
        model = Unit
        fields = ['unit', 'floor_number', 'area',
                  'bedrooms_count', 'parking_place', 'owner_name', 'owner_mobile',
                  'owner_national_code', 'unit_phone',
                  'parking_number', 'parking_count', 'status', 'purchase_date']


class RenterForm(forms.ModelForm):
    unit = forms.ModelChoiceField(queryset=Unit.objects.all(), required=True, widget=forms.Select(attrs=attr2), label='انتخاب واحد')
    renter_name = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr),
                                  label='نام مستاجر')
    renter_mobile = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr),
                                    label='شماره تلفن مستاجر')
    renter_national_code = forms.CharField(error_messages=error_message, required=False,
                                           widget=forms.TextInput(attrs=attr), label='کد ملی مستاجر')
    people_count = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr),
                                   label='تعداد نفرات')

    start_date = JalaliDateField(
        label='تاریخ شروع اجاره',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message
    )
    end_date = JalaliDateField(
        label='تاریخ پایان اجاره',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message
    )
    contract_number = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr),
                                      label='شماره قرارداد')
    estate_name = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr),
                                  label='نام اجاره دهنده')
    first_charge = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr),
                                   label='شارژ اولیه')

    class Meta:
        model = Renter
        fields = ['unit', 'renter_name', 'renter_national_code', 'renter_mobile',
                  'people_count', 'start_date', 'end_date', 'first_charge', 'contract_number',
                  'estate_name']
