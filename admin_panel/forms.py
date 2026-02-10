import jdatetime
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from django_select2.forms import ModelSelect2MultipleWidget
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget
from admin_panel.models import (Announcement, Expense, ExpenseCategory, Income, IncomeCategory, ReceiveMoney, PayMoney, \
                                Property, Maintenance, ChargeByPersonArea, ChargeByFixPersonArea, FixCharge, AreaCharge,
                                PersonCharge,
                                FixPersonCharge, FixAreaCharge, ChargeFixVariable, SmsManagement, UnifiedCharge,
                                MessageToUser, SmsCredit, AdminMessageToMiddle, AdminSmsManagement)

from user_app.models import Unit, Bank, User, MyHouse, ChargeMethod, Renter

attr = {'class': 'form-control border-1 py-2 mb-4 '}
attr0 = {'class': 'form-control form-control-sm border-1 py-1 mb-4 '}
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
MARQUEE_CHOICES = {
    'True': 'بله',
    'False': 'خیر'
}

MIDDLE_CHOICES = (
    (1, 'بله'),
    (0, 'خیر'),
)


class announcementForm(forms.ModelForm):
    # title = forms.CharField(widget=CKEditorUploadingWidget())
    title = forms.CharField(
        error_messages=error_message,
        required=True,
        widget=forms.Textarea(attrs=attr),
        label='متن اطلاعیه '
    )
    # slug = forms.SlugField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr),
    #                        label='عنوان در Url')
    is_active = forms.ChoiceField(label='فعال /غیرفعال نمودن اطلاعیه', required=True,
                                  error_messages=error_message, choices=CHOICES, widget=forms.Select(attrs=attr))
    show_in_marquee = forms.ChoiceField(label='نمایش در اخبار مهم ساختمان', required=True, initial=False,
                                        error_messages=error_message, choices=MARQUEE_CHOICES,
                                        widget=forms.Select(attrs=attr))

    class Meta:
        model = Announcement
        fields = ['title', 'is_active', 'show_in_marquee']


class MessageToUserForm(forms.ModelForm):
    title = forms.CharField(
        error_messages=error_message,
        required=True,
        widget=forms.TextInput(attrs=attr),
        label='عنوان پیام'
    )
    message = forms.CharField(
        error_messages=error_message,
        required=True,
        widget=forms.Textarea(attrs=attr),
        label='متن پیام'
    )

    is_active = forms.ChoiceField(
        label='فعال / غیرفعال نمودن',
        required=True,
        error_messages=error_message,
        choices=CHOICES,
        widget=forms.Select(attrs=attr)
    )

    class Meta:
        model = MessageToUser
        fields = ['title', 'message', 'is_active']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            # تمام کاربران تحت مدیریت این مدیر + خودش
            managed_users = User.objects.filter(Q(manager=user) | Q(pk=user.pk))
            self.fields['unit'].queryset = Unit.objects.filter(
                is_active=True,
                user__in=managed_users
            ).select_related('user')

        # # نمایش نام مستاجر فعال یا مالک
        # self.fields['unit'].label_from_instance = lambda obj: (
        #     f"واحد {obj.unit} - {obj.get_active_renter().renter_name}"
        #     if obj.get_active_renter() else
        #     f"واحد {obj.unit} - {obj.owner_name}"
        # )

class AdminMessageToMiddleForm(forms.ModelForm):
    title = forms.CharField(
        error_messages=error_message,
        required=True,
        widget=forms.TextInput(attrs=attr),
        label='عنوان پیام'
    )
    message = forms.CharField(
        error_messages=error_message,
        required=True,
        widget=forms.Textarea(attrs=attr),
        label='متن پیام'
    )

    is_active = forms.ChoiceField(
        label='فعال / غیرفعال نمودن',
        required=True,
        error_messages=error_message,
        choices=CHOICES,
        widget=forms.Select(attrs=attr)
    )

    class Meta:
        model = AdminMessageToMiddle
        fields = ['title', 'message', 'is_active']

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)






RESIDENCE_STATUS_CHOICES = {
    '': '--- انتخاب کنید ---',
    'occupied': 'ساکن',
    'empty': 'خالی'
}

BEDROOMS_COUNT_CHOICES = {
    '': '--- انتخاب کنید ---', '1': '1', '2': '2', '3': '3', '4': '4',
}

AREA_CHOICES = {
    '': '--- انتخاب کنید ---', '90': '90', '120': '120', '130': '130', '150': '150',
}

PARKING_PLACE_CHOICES = {
    '': '--- انتخاب کنید ---', 'همکف': 'همکف', 'طبقه -1': 'طبقه -1', 'طبقه -2': 'طبقه -2', 'طبقه -3': 'طبقه -3',
    'طبقه -4': 'طبقه -4', 'طبقه -5': 'طبقه -5',
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


class ChargeCategoryForm(forms.ModelForm):
    name = forms.CharField(error_messages=error_message, required=True,
                           widget=forms.TextInput(attrs=attr),
                           label='روش شارژ')

    is_active = forms.ChoiceField(label='فعال /غیرفعال  ', required=True,
                                  error_messages=error_message, choices=CHOICES, widget=forms.Select(attrs=attr))

    class Meta:
        model = ChargeMethod
        fields = ['name', 'is_active']


class UserRegistrationForm(forms.ModelForm):
    mobile = forms.CharField(error_messages=error_message,
                             required=True,
                             max_length=11,
                             min_length=11,
                             widget=forms.TextInput(attrs=attr),
                             label='شماره تلفن ')
    full_name = forms.CharField(error_messages=error_message, required=True,
                                widget=forms.TextInput(attrs=attr3), label='نام ')
    username = forms.CharField(error_messages=error_message, required=True,
                               widget=forms.TextInput(attrs=attr3), label='نام کاربری ')

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
    charge_methods = forms.ModelMultipleChoiceField(
        queryset=ChargeMethod.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='روش‌های شارژ قابل دسترسی'
    )

    is_active = forms.ChoiceField(choices=MIDDLE_CHOICES, label='فعال باشد؟', widget=forms.Select(attrs=attr))

    is_resident = forms.ChoiceField(choices=MIDDLE_CHOICES, label='ساکن ساختمان میباشد؟',
                                    widget=forms.Select(attrs=attr))

    class Meta:
        model = User
        fields = ['full_name', 'mobile', 'username', 'password', 'is_active', 'charge_methods', 'is_resident']

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        if User.objects.filter(mobile=mobile).exclude(pk=self.instance.pk).exists():
            raise ValidationError("شماره موبایل قبلاً ثبت شده است.")
        return mobile

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError("نام کاربری قبلاً ثبت شده است.")
        return username

    def clean_password2(self):
        password = self.cleaned_data.get("password")
        confirm_password = self.cleaned_data.get("password")

        if password and confirm_password and password != confirm_password:
            raise ValidationError("رمزهای عبور با هم مطابقت ندارند!")

        return confirm_password

    # def clean_is_active(self):
    #     return self.cleaned_data.get('is_active', False)

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        else:
            user.password = self.instance.password

        if commit:
            user.save()

            # ذخیره روش‌های شارژ برای مدیر سطح میانی
            if user.is_middle_admin:
                selected_methods = self.cleaned_data.get('charge_methods')
                if hasattr(user, 'charge_access'):
                    # اگر دسترسی قبلا وجود داشت، آپدیت کن
                    user.charge_access.charge_methods.set(selected_methods)
                else:
                    # اگر دسترسی وجود نداشت، بساز
                    from .models import MiddleAdminChargeAccess
                    access = MiddleAdminChargeAccess.objects.create(manager=user)
                    access.charge_methods.set(selected_methods)

        return user


IS_CHOICES = (
    ('', '--- انتخاب کنید ---'),
    (1, 'بله'),
    (0, 'خیر'),
)
IS_CHOICES_Active = (
    ('', '--- انتخاب کنید ---'),
    (1, 'بله'),
    (0, 'خیر'),
)


class BankForm(forms.ModelForm):
    house = forms.ModelChoiceField(
        queryset=MyHouse.objects.none(),
        required=True,
        widget=forms.Select(attrs=attr3),
        label='نام ساختمان'
    )
    bank_name = forms.ChoiceField(error_messages=error_message, required=True, choices=BANK_CHOICES,
                                  widget=forms.Select(attrs=attr3), label='نام بانک')

    account_holder_name = forms.CharField(error_messages=error_message, required=True,
                                          widget=forms.TextInput(attrs=attr),
                                          label='نام صاحب حساب')
    account_no = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr),
                                 label='شماره حساب')
    sheba_number = forms.CharField(error_messages=error_message,
                                   max_length=24,
                                   min_length=24,
                                   required=False, widget=forms.TextInput(attrs=attr),
                                   label='شماره شبا')
    cart_number = forms.CharField(error_messages=error_message,
                                  max_length=16,
                                  min_length=16,
                                  required=False, widget=forms.TextInput(attrs=attr),
                                  label='شماره کارت')
    initial_fund = forms.CharField(error_messages=error_message, required=False, widget=forms.NumberInput(attrs=attr),
                                   label='موجودی اولیه', initial=0)
    is_default = forms.ChoiceField(choices=IS_CHOICES, label='حساب پیش فرض باشد', widget=forms.Select(attrs=attr))
    is_gateway = forms.ChoiceField(choices=IS_CHOICES, label='حساب پیش فرض درگاه اینترنتی باشد',
                                   widget=forms.Select(attrs=attr))
    is_active = forms.ChoiceField(choices=IS_CHOICES_Active, label='حساب فعال باشد', widget=forms.Select(attrs=attr))

    class Meta:
        model = Bank
        fields = (
            'house', 'bank_name', 'account_holder_name', 'account_no', 'sheba_number', 'cart_number',
            'initial_fund', 'is_active', 'is_default', 'is_gateway')

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and user.is_middle_admin:
            self.fields['house'].queryset = MyHouse.objects.filter(
                Q(user=user) | Q(user__manager=user),
                is_active=True
            )
        else:
            self.fields['house'].queryset = MyHouse.objects.none()

    def clean_sheba_number(self):
        sheba = self.cleaned_data.get('sheba_number')
        if sheba:
            sheba = sheba.replace(' ', '').upper()
            if not sheba.startswith('IR'):
                raise forms.ValidationError('شماره شبا باید با IR شروع شود')
            if len(sheba) != 24:
                raise forms.ValidationError('شماره شبا باید ۲۴ کاراکتر باشد')
        return sheba


USER_TYPE_CHOICES = [
    ('', '--- انتخاب کنید ---'),
    ('مسکونی', 'مسکونی'),
    ('اداری', 'اداری'),
    ('تجاری', 'تجاری'),
    ('سایر', 'سایر'),
]

CITY_CHOICES = [
    ('', '--- انتخاب کنید ---'),
    ('تهران', 'تهران'),
    ('مشهد', 'مشهد'),
    ('شیراز', 'شیراز'),
    ('اصفهان', 'اصفهان'),
    ('کرج', 'کرج'),
    ('قم', 'قم'),
    ('رشت', 'رشت'),
    ('اهواز', 'اهواز'),
    ('تبریز', 'تبریز'),
    ('یزد', 'یزد'),
    ('کرمان', 'کرمان'),
    ('گرگان', 'گرگان'),
    ('سنندج', 'سنندج'),
    ('بندرعباس', 'بندرعباس'),
    ('زاهدان', 'زاهدان'),
    ('اردبیل', 'اردبیل'),
    ('بوشهر', 'بوشهر'),
    ('قزوین', 'قزوین'),
    ('ارومیه', 'ارومیه'),
    ('ساری', 'ساری'),
]


class MyHouseForm(forms.ModelForm):
    name = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr),
                           label='نام ساختمان')
    user_type = forms.ChoiceField(error_messages=error_message, choices=USER_TYPE_CHOICES, required=True,
                                  widget=forms.Select(attrs=attr3),
                                  label='نوع کاربری')
    floor_counts = forms.IntegerField(error_messages=error_message, required=True,
                                      widget=forms.NumberInput(attrs=attr),
                                      label='تعداد طبقات')
    unit_counts = forms.IntegerField(error_messages=error_message, required=True,
                                     widget=forms.NumberInput(attrs=attr),
                                     label='تعداد واحدها')

    city = forms.ChoiceField(error_messages=error_message, choices=CITY_CHOICES, required=True,
                             widget=forms.Select(attrs=attr3),
                             label='شهر')
    address = forms.CharField(error_messages=error_message, required=True,
                              widget=forms.TextInput(attrs=attr),
                              label='آدرس')
    is_active = forms.BooleanField(initial=True, required=False, label='فعال/غیرفعال')

    class Meta:
        model = MyHouse
        fields = ['name', 'address', 'user_type', 'city', 'is_active', 'floor_counts', 'unit_counts']


class UnitForm(forms.ModelForm):
    unit = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr0),
                           label='شماره واحد')
    owner_bank = forms.ModelChoiceField(
        queryset=Bank.objects.none(),
        empty_label="شماره حساب را انتخاب کنید",
        error_messages=error_message,
        required=False,
        label=' حساب بانکی جهت واریز شارژ',
        widget=forms.Select(
            attrs={
                'class': 'form-control-sm ',
                'style': 'width:100%',
                # 'data-placeholder': 'واحد / مالک یا مستاجر را انتخاب کنید1'
            }
        )
    )
    renter_bank = forms.ModelChoiceField(
        queryset=Bank.objects.none(),
        empty_label="شماره حساب را انتخاب کنید",
        error_messages=error_message,
        required=False,
        label=' حساب بانکی جهت واریز شارژ',
        widget=forms.Select(
            attrs={
                'class': 'form-control-sm ',
                'style': 'width:100%',
                # 'data-placeholder': 'واحد / مالک یا مستاجر را انتخاب کنید1'
            }
        )
    )
    unit_phone = forms.CharField(error_messages=error_message,
                                 max_length=8,
                                 min_length=8,
                                 required=False, widget=forms.TextInput(attrs=attr0),
                                 label='شماره تلفن واحد')
    floor_number = forms.IntegerField(error_messages=error_message, required=True,
                                      widget=forms.NumberInput(attrs=attr0),
                                      label='شماره طبقه')
    area = forms.IntegerField(error_messages=error_message, required=True,
                              widget=forms.NumberInput(attrs=attr0),
                              label='متراژ')
    bedrooms_count = forms.ChoiceField(error_messages=error_message, choices=BEDROOMS_COUNT_CHOICES, required=True,
                                       widget=forms.Select(attrs=attr0),
                                       label='تعداد خواب')

    parking_place = forms.ChoiceField(error_messages=error_message, choices=PARKING_PLACE_CHOICES, required=False,
                                      widget=forms.Select(attrs=attr0),
                                      label='موقعیت پارکینگ اصلی')
    extra_parking_first = forms.CharField(error_messages=error_message, required=False,
                                          widget=forms.TextInput(attrs=attr0),
                                          label=' پارکینگ اضافه اول')
    extra_parking_second = forms.CharField(error_messages=error_message, required=False,
                                           widget=forms.TextInput(attrs=attr0),
                                           label=' پارکینگ اضافه دوم')

    parking_number = forms.CharField(
        error_messages=error_message,
        required=False,
        widget=forms.TextInput(attrs=attr0),
        label='شماره پارکینگ'
    )
    owner_transaction_no = forms.IntegerField(error_messages=error_message,
                                              widget=forms.TextInput(attrs=attr),
                                              required=False, min_value=0,
                                              label='کد پیگیری')
    owner_payment_date = JalaliDateField(
        label='تاریخ پرداخت',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=False
    )
    renter_transaction_no = forms.IntegerField(error_messages=error_message,
                                               widget=forms.TextInput(attrs=attr),
                                               required=False, min_value=0,
                                               label='کد پیگیری')
    renter_payment_date = JalaliDateField(
        label='تاریخ پرداخت',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=False
    )
    parking_count = forms.ChoiceField(error_messages=error_message, choices=PARKING_COUNT_CHOICES, required=True,
                                      widget=forms.Select(attrs=attr0),
                                      label='تعداد پارکینگ')
    unit_details = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'rows': 8}), required=False,
                                   label='توضیحات واحد')
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
                                         widget=forms.Select(attrs=attr0),
                                         label='وضعیت سکونت')
    is_renter = forms.ChoiceField(
        choices=[('', '--- انتخاب کنید ---'), ('True', 'بله'), ('False', 'خیر')],
        widget=forms.Select(attrs={'id': 'id_is_renter', 'class': 'form-control'}),
        label='واحد دارای مستاجر است؟'
    )
    owner_details = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'rows': 8}), required=False,
                                    label='توضیحات مالک')
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
    first_charge_owner = forms.CharField(error_messages=error_message, required=False,
                                         widget=forms.TextInput(attrs=attr),
                                         label='شارژ اولیه مالک', initial=0)
    first_charge_renter = forms.CharField(error_messages=error_message, required=False,
                                          widget=forms.TextInput(attrs=attr),
                                          label='شارژ اولیه مستاجر', initial=0)
    renter_details = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'rows': 8}), required=False,
                                     label='توضیحات مستاجر')
    is_active = forms.BooleanField(required=False, initial=True, label='فعال/غیرفعال نمودن')
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

        if password or confirm_password:
            if password != confirm_password:
                self.add_error('confirm_password', "کلمه عبور و تکرار آن باید یکسان باشند.")

        is_renter = cleaned_data.get('is_renter')

        if cleaned_data.get('start_date') and cleaned_data.get('end_date'):
            start_date = cleaned_data.get('start_date')
            end_date = cleaned_data.get('end_date')

            if start_date > end_date:
                self.add_error('start_date', 'تاریخ شروع اجاره نباید از تاریخ پایان بزرگتر باشد.')

        if str(is_renter).lower() == 'true':
            required_fields_if_rented = [
                'renter_name', 'renter_mobile', 'renter_national_code',
                'renter_people_count', 'start_date', 'end_date',
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
                  'renter_national_code', 'renter_details', 'extra_parking_first', 'extra_parking_second',
                  'renter_mobile', 'is_renter', 'owner_people_count', 'renter_bank',
                  'renter_people_count', 'start_date', 'end_date', 'first_charge_owner', 'first_charge_renter',
                  'contract_number', 'owner_bank', 'owner_transaction_no', 'owner_payment_date', 'renter_payment_date',
                  'estate_name', 'is_active', 'password', 'confirm_password', 'renter_transaction_no']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # بانک‌ها
        if user:
            banks = Bank.objects.filter(is_active=True, user=user)
            self.fields['owner_bank'].queryset = banks
            self.fields['renter_bank'].queryset = banks
            self.fields['owner_bank'].label_from_instance = lambda obj: f"{obj.bank_name} - {obj.account_no}" + (
                " (پیش‌فرض)" if obj.is_default else "")
            self.fields['renter_bank'].label_from_instance = lambda obj: f"{obj.bank_name} - {obj.account_no}" + (
                " (پیش‌فرض)" if obj.is_default else "")

        # مقداردهی مستاجر از instance
        if self.instance.pk:
            active_renter = self.instance.get_active_renter()
            if active_renter:
                self.fields['renter_name'].initial = active_renter.renter_name
                self.fields['renter_mobile'].initial = active_renter.renter_mobile
                self.fields['renter_national_code'].initial = active_renter.renter_national_code
                self.fields['renter_people_count'].initial = active_renter.renter_people_count
                self.fields['renter_bank'].initial = active_renter.renter_bank
                self.fields['start_date'].initial = active_renter.start_date
                self.fields['end_date'].initial = active_renter.end_date
                self.fields['contract_number'].initial = active_renter.contract_number
                self.fields['estate_name'].initial = active_renter.estate_name
                self.fields['first_charge_renter'].initial = active_renter.first_charge_renter
                self.fields['renter_details'].initial = active_renter.renter_details
                self.fields['renter_payment_date'].initial = active_renter.renter_payment_date
                self.fields['renter_transaction_no'].initial = active_renter.renter_transaction_no
                self.fields['is_renter'].initial = True
            else:
                self.fields['is_renter'].initial = False

    def save(self, commit=True):
        instance = super().save(commit=False)

        is_renter = str(self.cleaned_data.get('is_renter')).lower() == 'true'

        if not is_renter:
            # Owner is resident, clear renter fields
            instance.renter_name = ''
            instance.renter_mobile = ''
            instance.renter_national_code = ''
            instance.renter_people_count = ''
            instance.start_date = None
            instance.end_date = None
            instance.contract_number = ''
            instance.first_charge_renter = None or 0
            instance.renter_details = ''
            instance.renter_transaction_no = None
            instance.renter_payment_date = None

            # Set people_count from owner's info
            instance.people_count = int(self.cleaned_data.get('owner_people_count')) or 0
        else:
            # We'll assign renter_people_count later
            instance.people_count = 0  # default for now

        if commit:
            instance.save()  # ✅ Save first so instance has a PK

            # ✅ Now you can access related renters
            if not is_renter:
                active_renter = instance.renters.filter(renter_is_active=True).last()
                if active_renter:
                    instance.people_count = active_renter.renter_people_count or 0
                    instance.save(update_fields=['people_count'])  # update only this field

        return instance


class RenterAddForm(forms.ModelForm):
    renter_bank = forms.ModelChoiceField(
        queryset=Bank.objects.none(),
        empty_label="شماره حساب را انتخاب کنید",
        error_messages=error_message,
        required=False,
        label=' حساب بانکی جهت واریز شارژ',
        widget=forms.Select(
            attrs={
                'class': 'form-control-sm ',
                'style': 'width:100%',
                # 'data-placeholder': 'واحد / مالک یا مستاجر را انتخاب کنید1'
            }
        )
    )
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
    first_charge_owner = forms.CharField(error_messages=error_message, required=False,
                                         widget=forms.TextInput(attrs=attr),
                                         label='شارژ اولیه مالک', initial=0)
    first_charge_renter = forms.CharField(error_messages=error_message, required=False,
                                          widget=forms.TextInput(attrs=attr),
                                          label='شارژ اولیه مستاجر', initial=0)
    renter_details = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'rows': 8}), required=False,
                                     label='توضیحات مستاجر')

    renter_is_active = forms.BooleanField(required=False, initial=True, label='فعال')
    renter_transaction_no = forms.IntegerField(error_messages=error_message,
                                               widget=forms.TextInput(attrs=attr),
                                               required=False, min_value=0,
                                               label='کد پیگیری')
    renter_payment_date = JalaliDateField(
        label='تاریخ پرداخت',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=False
    )
    # mobile = forms.CharField(
    #     required=True,
    #     max_length=11,
    #     min_length=11,
    #     error_messages=error_message,
    #     label='نام کاربری',
    #     widget=forms.TextInput(attrs=attr)
    # )
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

    class Meta:
        model = Renter
        fields = [
            'renter_name',
            'renter_mobile',
            'renter_national_code',
            'renter_people_count',
            'start_date',
            'end_date',
            'contract_number',
            'estate_name',
            'first_charge_renter',
            'renter_details',
            'renter_is_active',
            'renter_transaction_no',
            'renter_payment_date',
            'renter_bank',
            'password',
            'confirm_password'
        ]

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password or confirm_password:
            if password != confirm_password:
                self.add_error('confirm_password', "کلمه عبور و تکرار آن باید یکسان باشند.")
        return cleaned_data

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            banks = Bank.objects.filter(is_active=True, user=user)
            self.fields['renter_bank'].queryset = banks
            self.fields['renter_bank'].label_from_instance = lambda obj: f"{obj.bank_name} - {obj.account_no}" + (
                " (پیش‌فرض)" if obj.is_default else "")


# ======================== Expense Forms =============================

class ExpenseForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=ExpenseCategory.objects.none(),
        widget=forms.Select(attrs=attr),
        empty_label="یک گروه انتخاب کنید",
        error_messages=error_message,
        required=True,
        label='موضوع هزینه'
    )
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
                             label='شماره فاکتور')
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

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        default_categories = ['هزینه آب', 'هزینه برق', 'هزینه گاز']  # آیتم های پیش‌فرض
        if user:
            # ابتدا مطمئن می‌شویم که آیتم‌های پیش‌فرض وجود دارند
            for title in default_categories:
                obj, created = ExpenseCategory.objects.get_or_create(
                    title=title,
                    defaults={'is_active': True, 'user': user}
                )

            # سپس queryset فرم را تعریف می‌کنیم
            self.fields['category'].queryset = ExpenseCategory.objects.filter(
                is_active=True,
                user=user
            )

    # def __init__(self, *args, **kwargs):
    #     user = kwargs.pop('user', None)
    #     super().__init__(*args, **kwargs)
    #
    #     if user:
    #         self.fields['category'].queryset = ExpenseCategory.objects.filter(
    #             is_active=True,
    #             user=user
    #         )

    def clean_amount(self):
        """
        تبدیل مبلغ به عدد + حذف کاما
        """
        amount = self.cleaned_data.get('amount')
        try:
            amount = int(str(amount).replace(',', ''))
            if amount <= 0:
                raise ValidationError('مبلغ باید بزرگتر از صفر باشد')
            return amount
        except ValueError:
            raise ValidationError('مبلغ وارد شده معتبر نیست')

    def clean_date(self):
        """
        اگر تاریخ وارد نشده بود → امروز
        """
        date = self.cleaned_data.get('date')
        if not date:
            return timezone.now().date()
        return date


class ExpensePayForm(forms.ModelForm):
    bank = forms.ModelChoiceField(
        queryset=Bank.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'}),
        empty_label="شماره حساب را انتخاب کنید",
        error_messages=error_message,
        required=True,
        label='شماره حساب بانکی'
    )
    payment_date = JalaliDateField(
        label='تاریخ پرداخت',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=True
    )
    transaction_reference = forms.IntegerField(error_messages=error_message,
                                               widget=forms.TextInput(attrs=attr),
                                               required=False, min_value=0,
                                               label='کد پیگیری')
    unit = forms.ModelChoiceField(
        queryset=Unit.objects.none(),
        required=False,
        label='دریافت کننده توسط ساکنین',
        widget=forms.Select(
            attrs={
                'class': 'form-control-sm ',
                'style': 'width:100%',
            }
        )
    )
    receiver_name = forms.CharField(
        max_length=200, required=False, label='دریافت کننده غیر از ساکنین ',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Expense
        fields = ['bank', 'transaction_reference', 'payment_date', 'receiver_name', 'unit']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            managed_users = User.objects.filter(Q(manager=user) | Q(pk=user.pk))
            self.fields['unit'].queryset = Unit.objects.filter(
                is_active=True,
                user__in=managed_users
            ).select_related('user').order_by('unit')

            banks = Bank.objects.filter(is_active=True, user=user)
            self.fields['bank'].queryset = banks

            # پیدا کردن بانک پیش‌فرض
            default_bank = banks.filter(is_default=True).first()
            if default_bank:
                self.fields['bank'].initial = default_bank

            # تغییر label برای نمایش "(پیش‌فرض)" کنار نام بانک
            self.fields['bank'].label_from_instance = lambda obj: f"{obj.bank_name} - {obj.account_no}" + (
                " (پیش‌فرض)" if obj.is_default else "")

            def get_unit_label(obj):
                renter = obj.get_active_renter()
                if renter and getattr(renter, 'renter_name', None):
                    return f"واحد {obj.unit} - {renter.renter_name}"
                elif obj.owner_name:
                    return f"واحد {obj.unit} - {obj.owner_name}"
                else:
                    return f"واحد {obj.unit} - نام نامشخص"

            self.fields['unit'].label_from_instance = get_unit_label

    def clean(self):
        cleaned_data = super().clean()
        unit = cleaned_data.get('unit')
        payer_name = cleaned_data.get('receiver_name')

        if not unit and not payer_name:
            raise forms.ValidationError("لطفا یا واحد را انتخاب کنید یا نام دریافت کننده را وارد نمایید.")

        return cleaned_data


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
        error_messages=error_message, required=True
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
        queryset=IncomeCategory.objects.none(),
        widget=forms.Select(attrs=attr),
        empty_label="یک گروه انتخاب کنید",
        error_messages=error_message,
        required=True,
        label='موضوع درآمد'
    )
    unit = forms.ModelChoiceField(
        queryset=Unit.objects.none(),
        required=False,
        label='پرداخت کننده توسط ساکنین',
        widget=forms.Select(
            attrs={
                'class': 'form-control-sm ',
                'style': 'width:100%',
            }
        )
    )
    payer_name = forms.CharField(
        max_length=200, required=False, label='پرداخت کننده غیر از ساکنین ',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    amount = forms.CharField(error_messages=error_message, max_length=20, required=True,
                             widget=forms.TextInput(attrs=attr),
                             label='مبلغ')
    description = forms.CharField(error_messages=error_message, widget=forms.TextInput(attrs=attr), required=True,
                                  label='شرح سند')
    doc_date = JalaliDateField(
        label='تاریخ ثبت سند',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=True
    )
    doc_number = forms.CharField(error_messages=error_message, max_length=10, widget=forms.TextInput(attrs=attr),
                                 required=True,
                                 label='شماره فاکتور')
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
        fields = ['category', 'amount', 'doc_date', 'description', 'doc_number', 'details',
                  'document']

    def clean_amount(self):
        """
        تبدیل مبلغ به عدد + حذف کاما
        """
        amount = self.cleaned_data.get('amount')
        try:
            amount = int(str(amount).replace(',', ''))
            if amount <= 0:
                raise ValidationError('مبلغ باید بزرگتر از صفر باشد')
            return amount
        except ValueError:
            raise ValidationError('مبلغ وارد شده معتبر نیست')

    def clean_date(self):
        """
        اگر تاریخ وارد نشده بود → امروز
        """
        doc_date = self.cleaned_data.get('doc_date')
        if not doc_date:
            return timezone.now().date()
        return doc_date

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields['category'].queryset = IncomeCategory.objects.filter(is_active=True, user=user)


class IncomePayForm(forms.ModelForm):
    bank = forms.ModelChoiceField(
        queryset=Bank.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'}),
        empty_label="شماره حساب را انتخاب کنید",
        error_messages=error_message,
        required=True,
        label='شماره حساب بانکی'
    )
    payment_date = JalaliDateField(
        label='تاریخ پرداخت',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=False
    )
    transaction_reference = forms.IntegerField(error_messages=error_message,
                                               widget=forms.TextInput(attrs=attr),
                                               required=False, min_value=0,
                                               label='کد پیگیری')
    unit = forms.ModelChoiceField(
        queryset=Unit.objects.none(),
        required=False,
        label='پرداخت کننده توسط ساکنین',
        widget=forms.Select(
            attrs={
                'class': 'form-control-sm ',
                'style': 'width:100%',
            }
        )
    )
    payer_name = forms.CharField(
        max_length=200, required=False, label='پرداخت کننده غیر از ساکنین ',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Income
        fields = ['bank', 'transaction_reference', 'payment_date', 'payer_name', 'unit']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            managed_users = User.objects.filter(Q(manager=user) | Q(pk=user.pk))
            self.fields['unit'].queryset = Unit.objects.filter(
                is_active=True,
                user__in=managed_users
            ).select_related('user').order_by('unit')

            banks = Bank.objects.filter(is_active=True, user=user)
            self.fields['bank'].queryset = banks

            # پیدا کردن بانک پیش‌فرض
            default_bank = banks.filter(is_default=True).first()
            if default_bank:
                self.fields['bank'].initial = default_bank

            # تغییر label برای نمایش "(پیش‌فرض)" کنار نام بانک
            self.fields['bank'].label_from_instance = lambda obj: f"{obj.bank_name} - {obj.account_no}" + (
                " (پیش‌فرض)" if obj.is_default else "")

            def get_unit_label(obj):
                renter = obj.get_active_renter()
                if renter and getattr(renter, 'renter_name', None):
                    return f"واحد {obj.unit} - {renter.renter_name}"
                elif obj.owner_name:
                    return f"واحد {obj.unit} - {obj.owner_name}"
                else:
                    return f"واحد {obj.unit} - نام نامشخص"

            self.fields['unit'].label_from_instance = get_unit_label

    def clean(self):
        cleaned_data = super().clean()
        unit = cleaned_data.get('unit')
        payer_name = cleaned_data.get('payer_name')

        if not unit and not payer_name:
            raise forms.ValidationError("لطفا یا واحد را انتخاب کنید یا نام پرداخت کننده را وارد نمایید.")

        return cleaned_data


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
        queryset=Bank.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="شماره حساب را انتخاب کنید",
        required=True,
        label='حساب بانکی'
    )

    unit = forms.ModelChoiceField(
        queryset=Unit.objects.none(),
        required=False,
        label='انتخاب واحد',
        widget=forms.Select(attrs={'class': 'form-control-sm', 'style': 'width:100%'})
    )

    payer_name = forms.CharField(
        max_length=200, required=False, label='پرداخت کننده',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    amount = forms.IntegerField(
        required=True, label='مبلغ',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    description = forms.CharField(
        required=True, label='شرح سند',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    doc_date = JalaliDateField(
        label='تاریخ ثبت سند',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        required=False
    )

    doc_number = forms.CharField(
        max_length=10, required=True, label='شماره سند',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    document = forms.FileField(
        required=False, label='تصویر سند',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    details = forms.CharField(
        required=False, label='توضیحات',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

    payment_date = JalaliDateField(
        label='تاریخ پرداخت',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        required=False
    )

    transaction_reference = forms.IntegerField(
        required=False, min_value=0, initial=0,
        label='شماره پیگیری',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = ReceiveMoney
        fields = [
            'bank', 'amount', 'doc_date', 'description', 'doc_number',
            'details', 'document', 'unit', 'payer_name', 'payment_date', 'transaction_reference'
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            # بانک‌ها
            banks = Bank.objects.filter(is_active=True, user=user)
            self.fields['bank'].queryset = banks
            default_bank = banks.filter(is_default=True).first()
            if default_bank:
                self.fields['bank'].initial = default_bank

            # واحدها: کاربران تحت مدیریت + خودش
            managed_users = User.objects.filter(Q(manager=user) | Q(pk=user.pk))
            self.fields['unit'].queryset = Unit.objects.filter(
                is_active=True,
                user__in=managed_users
            ).select_related('user').order_by('unit')

            # label امن برای unit (مستاجر یا مالک)
            def get_unit_label(obj):
                renter = obj.get_active_renter()
                if renter and getattr(renter, 'renter_name', None):
                    return f"واحد {obj.unit} - {renter.renter_name}"
                elif obj.owner_name:
                    return f"واحد {obj.unit} - {obj.owner_name}"
                else:
                    return f"واحد {obj.unit} - نام نامشخص"

            self.fields['unit'].label_from_instance = get_unit_label


# =========================================================
class PayerMoneyForm(forms.ModelForm):
    bank = forms.ModelChoiceField(
        queryset=Bank.objects.none(),
        widget=forms.Select(attrs=attr),
        empty_label="شماره حساب انتخاب کنید",
        error_messages=error_message,
        required=True,
        label='شماره حساب بانکی'
    )
    unit = forms.ModelChoiceField(
        queryset=Unit.objects.none(),  # خالی → ajax پرش می‌کنه
        required=False,
        label='انتخاب واحد',
        widget=forms.Select(
            attrs={
                'class': 'form-control-sm ',
                'style': 'width:100%',
                # 'data-placeholder': 'واحد / مالک یا مستاجر را انتخاب کنید1'
            }
        )
    )
    receiver_name = forms.CharField(
        max_length=200, required=False, label=' دریافت کننده',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    amount = forms.IntegerField(error_messages=error_message, required=True,
                             widget=forms.NumberInput(attrs=attr),
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
    payment_date = JalaliDateField(
        label='تاریخ پرداخت',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=False
    )
    transaction_reference = forms.IntegerField(error_messages=error_message,
                                               widget=forms.TextInput(attrs=attr),
                                               required=False, min_value=0, initial=0, label='شماره پیگیری')

    class Meta:
        model = PayMoney
        fields = ['bank', 'amount', 'document_date', 'description', 'document_number',
                  'details', 'document', 'is_active', 'receiver_name', 'unit', 'payment_date', 'transaction_reference']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            # بانک‌ها
            banks = Bank.objects.filter(is_active=True, user=user)
            self.fields['bank'].queryset = banks
            default_bank = banks.filter(is_default=True).first()
            if default_bank:
                self.fields['bank'].initial = default_bank

            # واحدها: کاربران تحت مدیریت + خودش
            managed_users = User.objects.filter(Q(manager=user) | Q(pk=user.pk))
            self.fields['unit'].queryset = Unit.objects.filter(
                is_active=True,
                user__in=managed_users
            ).select_related('user').order_by('unit')

            # label امن برای unit (مستاجر یا مالک)
            def get_unit_label(obj):
                renter = obj.get_active_renter()
                if renter and getattr(renter, 'renter_name', None):
                    return f"واحد {obj.unit} - {renter.renter_name}"
                elif obj.owner_name:
                    return f"واحد {obj.unit} - {obj.owner_name}"
                else:
                    return f"واحد {obj.unit} - نام نامشخص"

            self.fields['unit'].label_from_instance = get_unit_label

    # def clean(self):
    #     cleaned_data = super().clean()
    #     unit = cleaned_data.get('unit')
    #     receiver_name = cleaned_data.get('receiver_name')
    #
    #     if not unit and not receiver_name:
    #         raise forms.ValidationError("لطفا یا واحد را انتخاب کنید یا نام دریافت کننده را وارد نمایید.")
    #
    #     return cleaned_data


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
    name = forms.CharField(error_messages=error_message, max_length=100, widget=forms.TextInput(attrs=attr),
                           required=True,
                           label='عنوان شارژ ')
    fix_amount = forms.IntegerField(error_messages=error_message,
                                    widget=forms.TextInput(attrs=attr),
                                    required=True,
                                    label='مبلغ شارژ به ازای هر واحد')
    civil = forms.IntegerField(error_messages=error_message,
                               widget=forms.TextInput(attrs=attr),
                               required=False, initial=0,
                               label='شارژ عمرانی')
    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                              label='توضیحات ')

    payment_penalty_amount = forms.IntegerField(error_messages=error_message,
                                                widget=forms.TextInput(attrs=attr),
                                                required=False, initial=0,
                                                label='جریمه دیرکرد به درصد')

    payment_deadline = JalaliDateField(
        label='مهلت پرداخت',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=True
    )
    other_cost_amount = forms.IntegerField(error_messages=error_message,
                                           widget=forms.TextInput(attrs=attr),
                                           required=False, initial=0,
                                           label='سایر هزینه ها')

    class Meta:
        model = FixCharge
        fields = ['name', 'fix_amount', 'details', 'civil', 'payment_deadline', 'payment_penalty_amount',
                  'other_cost_amount']

    def clean_payment_deadline(self):
        deadline = self.cleaned_data.get('payment_deadline')

        if deadline:
            today = jdatetime.date.today()

            if deadline < today:
                raise forms.ValidationError('مهلت پرداخت نمی‌تواند قبل از امروز باشد')

        return deadline


class AreaChargeForm(forms.ModelForm):
    name = forms.CharField(error_messages=error_message, max_length=100, widget=forms.TextInput(attrs=attr),
                           required=True,
                           label='عنوان شارژ ')
    area_amount = forms.IntegerField(error_messages=error_message,
                                     widget=forms.TextInput(attrs=attr),
                                     required=True,
                                     label='مبلغ شارژ به اساس متراژ')
    civil = forms.IntegerField(error_messages=error_message,
                               widget=forms.TextInput(attrs=attr),
                               required=False, initial=0,
                               label='شارژ عمرانی')
    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                              label='توضیحات ')
    payment_penalty_amount = forms.IntegerField(error_messages=error_message,
                                                widget=forms.TextInput(attrs=attr),
                                                required=False, initial=0,
                                                label='جریمه دیرکرد به درصد')

    payment_deadline = JalaliDateField(
        label='مهلت پرداخت',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=True
    )
    other_cost_amount = forms.IntegerField(error_messages=error_message,
                                           widget=forms.TextInput(attrs=attr),
                                           required=False, initial=0,
                                           label='سایر هزینه ها')

    def clean_civil_charge(self):
        value = self.cleaned_data.get('civil')
        if value in [None, '']:  # empty string or None
            return 0
        return value

    class Meta:
        model = AreaCharge
        fields = ['name', 'area_amount', 'details', 'civil', 'payment_deadline', 'payment_penalty_amount',
                  'other_cost_amount']

    def clean_payment_deadline(self):
        deadline = self.cleaned_data.get('payment_deadline')

        if deadline:
            today = jdatetime.date.today()

            if deadline < today:
                raise forms.ValidationError('مهلت پرداخت نمی‌تواند قبل از امروز باشد')

        return deadline


class PersonChargeForm(forms.ModelForm):
    name = forms.CharField(error_messages=error_message, max_length=100, widget=forms.TextInput(attrs=attr),
                           required=True,
                           label='عنوان شارژ ')
    person_amount = forms.IntegerField(error_messages=error_message,
                                       widget=forms.TextInput(attrs=attr),
                                       required=True,
                                       label='مبلغ شارژ به ازای هر نفر')
    civil = forms.IntegerField(error_messages=error_message,
                               widget=forms.TextInput(attrs=attr),
                               required=False, initial=0,
                               label='شارژ عمرانی')
    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                              label='توضیحات ')
    payment_penalty_amount = forms.IntegerField(error_messages=error_message,
                                                widget=forms.TextInput(attrs=attr),
                                                required=False, initial=0,
                                                label='جریمه دیرکرد به درصد')

    payment_deadline = JalaliDateField(
        label='مهلت پرداخت',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=True
    )
    other_cost_amount = forms.IntegerField(error_messages=error_message,
                                           widget=forms.TextInput(attrs=attr),
                                           required=False, initial=0,
                                           label='سایر هزینه ها')

    class Meta:
        model = PersonCharge
        fields = ['name', 'person_amount', 'details', 'civil', 'payment_deadline', 'payment_penalty_amount',
                  'other_cost_amount']

    def clean_payment_deadline(self):
        deadline = self.cleaned_data.get('payment_deadline')

        if deadline:
            today = jdatetime.date.today()

            if deadline < today:
                raise forms.ValidationError('مهلت پرداخت نمی‌تواند قبل از امروز باشد')

        return deadline


class FixAreaChargeForm(forms.ModelForm):
    name = forms.CharField(error_messages=error_message, max_length=100, widget=forms.TextInput(attrs=attr),
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
                               required=False, initial=0,
                               label='شارژ عمرانی')
    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                              label='توضیحات ')
    payment_penalty_amount = forms.IntegerField(error_messages=error_message,
                                                widget=forms.TextInput(attrs=attr),
                                                required=False, initial=0,
                                                label='جریمه دیرکرد به درصد')

    payment_deadline = JalaliDateField(
        label='مهلت پرداخت',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=True
    )
    other_cost_amount = forms.IntegerField(error_messages=error_message,
                                           widget=forms.TextInput(attrs=attr),
                                           required=False, initial=0,
                                           label='سایر هزینه ها')

    class Meta:
        model = FixAreaCharge
        fields = ['name', 'area_amount', 'details', 'civil', 'fix_charge_amount', 'payment_deadline',
                  'payment_penalty_amount',
                  'other_cost_amount']

    def clean_payment_deadline(self):
        deadline = self.cleaned_data.get('payment_deadline')

        if deadline:
            today = jdatetime.date.today()

            if deadline < today:
                raise forms.ValidationError('مهلت پرداخت نمی‌تواند قبل از امروز باشد')

        return deadline


class FixPersonChargeForm(forms.ModelForm):
    name = forms.CharField(error_messages=error_message, max_length=100, widget=forms.TextInput(attrs=attr),
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
                               required=False, initial=0,
                               label='شارژ عمرانی')
    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                              label='توضیحات ')

    payment_penalty_amount = forms.IntegerField(error_messages=error_message,
                                                widget=forms.TextInput(attrs=attr),
                                                required=False, initial=0,
                                                label='جریمه دیرکرد به درصد')

    payment_deadline = JalaliDateField(
        label='مهلت پرداخت',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=True
    )
    other_cost_amount = forms.IntegerField(error_messages=error_message,
                                           widget=forms.TextInput(attrs=attr),
                                           required=False, initial=0,
                                           label='سایر هزینه ها')

    class Meta:
        model = FixPersonCharge
        fields = ['name', 'person_amount', 'details', 'civil', 'fix_charge_amount', 'payment_deadline'
            , 'payment_penalty_amount', 'other_cost_amount']

    def clean_payment_deadline(self):
        deadline = self.cleaned_data.get('payment_deadline')

        if deadline:
            today = jdatetime.date.today()

            if deadline < today:
                raise forms.ValidationError('مهلت پرداخت نمی‌تواند قبل از امروز باشد')

        return deadline


class PersonAreaChargeForm(forms.ModelForm):
    name = forms.CharField(error_messages=error_message, max_length=100, widget=forms.TextInput(attrs=attr),
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
                               required=False, initial=0,
                               label='شارژ عمرانی(تومان)')
    payment_penalty_amount = forms.IntegerField(error_messages=error_message,
                                                widget=forms.TextInput(attrs=attr),
                                                required=False, initial=0,
                                                label='جریمه دیرکرد به درصد')

    payment_deadline = JalaliDateField(
        label='مهلت پرداخت',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=True
    )
    other_cost_amount = forms.IntegerField(error_messages=error_message,
                                           widget=forms.TextInput(attrs=attr),
                                           required=False, initial=0,
                                           label='سایر هزینه ها')

    class Meta:
        model = ChargeByPersonArea
        fields = ['name', 'area_amount', 'details', 'person_amount', 'civil', 'payment_deadline',
                  'payment_penalty_amount', 'other_cost_amount']

    def clean_payment_deadline(self):
        deadline = self.cleaned_data.get('payment_deadline')

        if deadline:
            today = jdatetime.date.today()

            if deadline < today:
                raise forms.ValidationError('مهلت پرداخت نمی‌تواند قبل از امروز باشد')

        return deadline


class PersonAreaFixChargeForm(forms.ModelForm):
    name = forms.CharField(error_messages=error_message, max_length=100, widget=forms.TextInput(attrs=attr),
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
                               required=False, initial=0,
                               label='شارژ عمرانی')
    payment_penalty_amount = forms.IntegerField(error_messages=error_message,
                                                widget=forms.TextInput(attrs=attr),
                                                required=False, initial=0,
                                                label='جریمه دیرکرد به درصد')

    payment_deadline = JalaliDateField(
        label='مهلت پرداخت',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=True
    )
    other_cost_amount = forms.IntegerField(error_messages=error_message,
                                           widget=forms.TextInput(attrs=attr),
                                           required=False, initial=0,
                                           label='سایر هزینه ها')

    class Meta:
        model = ChargeByFixPersonArea
        fields = ['name', 'area_amount', 'details', 'person_amount', 'civil', 'fix_charge_amount', 'payment_deadline',
                  'payment_penalty_amount', 'other_cost_amount']

    def clean_payment_deadline(self):
        deadline = self.cleaned_data.get('payment_deadline')

        if deadline:
            today = jdatetime.date.today()

            if deadline < today:
                raise forms.ValidationError('مهلت پرداخت نمی‌تواند قبل از امروز باشد')

        return deadline


class VariableFixChargeForm(forms.ModelForm):
    name = forms.CharField(error_messages=error_message, max_length=200, widget=forms.TextInput(attrs=attr),
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
                               required=False, initial=0,
                               label='سایر هزینه ها')

    other_cost_amount = forms.IntegerField(error_messages=error_message,
                                           widget=forms.TextInput(attrs=attr),
                                           required=False, initial=0,
                                           label='شارژ عمرانی')
    payment_penalty_amount = forms.IntegerField(error_messages=error_message,
                                                widget=forms.TextInput(attrs=attr),
                                                required=False, initial=0,
                                                label='جریمه دیرکرد به درصد')

    payment_deadline = JalaliDateField(
        label='مهلت پرداخت',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=True
    )

    class Meta:
        model = ChargeFixVariable
        fields = ['name', 'extra_parking_amount', 'unit_fix_amount', 'unit_variable_area_amount',
                  'unit_variable_person_amount', 'civil', 'details', 'other_cost_amount',
                  'payment_penalty_amount', 'payment_deadline']

    def clean_payment_deadline(self):
        deadline = self.cleaned_data.get('payment_deadline')

        if deadline:
            today = jdatetime.date.today()

            if deadline < today:
                raise forms.ValidationError('مهلت پرداخت نمی‌تواند قبل از امروز باشد')

        return deadline


# class ExpenseChargeForm(forms.ModelForm):
#     name = forms.CharField(error_messages=error_message, max_length=200, widget=forms.TextInput(attrs=attr),
#                            required=True,
#                            label='عنوان شارژ ')
#     unit_power_amount = forms.IntegerField(error_messages=error_message,
#                                            widget=forms.TextInput(attrs=attr),
#                                            required=True,
#                                            label='جمع کل هزینه برق')
#     unit_water_amount = forms.IntegerField(error_messages=error_message,
#                                            widget=forms.TextInput(attrs=attr),
#                                            required=True,
#                                            label='جمع کل هزینه آب')
#     unit_gas_amount = forms.IntegerField(error_messages=error_message,
#                                          widget=forms.TextInput(attrs=attr),
#                                          required=True,
#                                          label='جمع کل هزینه گاز')
#
#     details = forms.CharField(error_messages=error_message, required=False,
#                               widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
#                               label='توضیحات ')
#     civil = forms.IntegerField(error_messages=error_message,
#                                widget=forms.TextInput(attrs=attr),
#                                required=False, min_value=0,
#                                label='سایر هزینه ها')
#
#     other_cost_amount = forms.IntegerField(error_messages=error_message,
#                                            widget=forms.TextInput(attrs=attr),
#                                            required=False, min_value=0,
#                                            label='شارژ عمرانی')
#     payment_penalty_amount = forms.IntegerField(error_messages=error_message,
#                                                 widget=forms.TextInput(attrs=attr),
#                                                 required=False, min_value=0,
#                                                 label='جریمه دیرکرد به درصد')
#
#     payment_deadline = JalaliDateField(
#         label='مهلت پرداخت',
#         widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
#         error_messages=error_message, required=False
#     )
#
#     class Meta:
#         model = ChargeFixVariable
#         fields = ['name', 'civil', 'details', 'other_cost_amount', 'payment_penalty_amount', 'payment_deadline']
#
#     def clean_payment_deadline(self):
#         deadline = self.cleaned_data.get('payment_deadline')
#
#         if deadline:
#             today = jdatetime.date.today()
#
#             if deadline < today:
#                 raise forms.ValidationError('مهلت پرداخت نمی‌تواند قبل از امروز باشد')
#
#         return deadline


class UnifiedChargePaymentForm(forms.ModelForm):
    payment_date = JalaliDateField(
        label='تاریخ پرداخت',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=False
    )
    transaction_reference = forms.IntegerField(error_messages=error_message,
                                               widget=forms.TextInput(attrs=attr),
                                               required=False, min_value=0,
                                               label='کد پیگیری')

    bank = forms.ModelChoiceField(
        queryset=Bank.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'}),
        empty_label="شماره کارت را انتخاب کنید",
        error_messages=error_message,
        required=True,
        label=' شماره کارت'
    )

    class Meta:
        model = UnifiedCharge
        fields = ['payment_date', 'transaction_reference', 'bank']

    def __init__(self, *args, **kwargs):
        charge = kwargs.pop('charge', None)
        super().__init__(*args, **kwargs)

        charge = self.instance

        # پیش‌فرض خالی
        self.fields['bank'].queryset = Bank.objects.none()

        if charge and charge.unit and charge.unit.myhouse:
            house = charge.unit.myhouse

            banks = Bank.objects.filter(
                is_active=True,
                house=house
            ).order_by('-is_default', 'bank_name')

            self.fields['bank'].queryset = banks

            # بانک پیش‌فرض
            default_bank = banks.filter(is_default=True).first()
            if default_bank:
                self.fields['bank'].initial = default_bank

            # label زیبا
            self.fields['bank'].label_from_instance = (
                lambda obj: f"{obj.bank_name} - {obj.cart_number}"
                + (" (پیش‌فرض)" if obj.is_default else "")
            )

    def clean_payment_date(self):
        date = self.cleaned_data.get('payment_date')
        if date:
            # تبدیل Jalali به Gregorian
            gregorian_date = date.togregorian().date() if isinstance(date, jdatetime.date) else date

            today = timezone.now().date()
            if gregorian_date > today:
                raise ValidationError("تاریخ پرداخت نمی‌تواند از امروز بیشتر باشد.")
        return date


class SmsForm(forms.ModelForm):
    subject = forms.CharField(error_messages=error_message, max_length=20, widget=forms.TextInput(attrs=attr),
                              required=True,
                              label='عنوان پیامک ')
    message = forms.CharField(error_messages=error_message, required=True, widget=forms.Textarea(
        attrs={'class': 'form-control', 'rows': 2}),
                              label='متن پیامک')

    is_active = forms.ChoiceField(label='فعال /غیرفعال نمودن پیامک', required=True,
                                  error_messages=error_message, choices=CHOICES, widget=forms.Select(attrs=attr))

    class Meta:
        model = SmsManagement
        fields = ['subject', 'message', 'is_active']


class AdminSmsForm(forms.ModelForm):
    subject = forms.CharField(error_messages=error_message, max_length=20, widget=forms.TextInput(attrs=attr),
                              required=True,
                              label='عنوان پیامک ')
    message = forms.CharField(
        error_messages=error_message,
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'id': 'sms_message',
            'placeholder': 'متن پیامک را وارد کنید...'
        }),
        label='متن پیامک'
    )

    is_active = forms.ChoiceField(label='فعال /غیرفعال نمودن پیامک', required=True,
                                  error_messages=error_message, choices=CHOICES, widget=forms.Select(attrs=attr))

    class Meta:
        model = AdminSmsManagement
        fields = ['subject', 'message', 'is_active']


class SmsCreditForm(forms.ModelForm):
    class Meta:
        model = SmsCredit
        fields = ['amount']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'مبلغ را وارد کنید'})
        }
