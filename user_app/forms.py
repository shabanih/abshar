from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import Q
from django.utils import timezone
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget

from notifications.models import SupportUser, SupportMessage, AdminTicket, AdminTicketMessage
from user_app.models import User, Unit, UserPayMoney, Bank

attr = {'class': 'form-control border-1 py-2 mb-2 placeholder-gray', }
attr1 = {'class': 'form-control border-1 py-1 mb-2 '}
attr3 = {'class': 'form-control form-control-sm border-1'}
attr2 = {'class': 'form-control border-1 my-2 mb-2 ', 'placeholder': 'لطفا واحد را انتخاب کنید'}

error_message = {
    'required': "تکمیل این فیلد ضروری است!",
    'min_length': 'تعداد کاراکترهای وارد شده کمتر از حد مجاز است!',
    'max_length': 'تعداد کاراکترهای وارد شده بیشتر از حد مجاز است!',
}
CHOICES = {
    'True': 'فعال',
    'False': 'غیرفعال'
}


class LoginForm(forms.Form):
    mobile = forms.CharField(
        label='شماره موبایل:',
        widget=forms.TextInput(attrs=attr),
        # required=True,
        max_length=11,
        min_length=11,
        error_messages={
            'required': 'لطفا شماره موبایل را وارد نمایید',
            'min_length': 'تعداد کاراکترهای وارد شده کمتر از حد مجاز است!',
            'max_length': 'تعداد کاراکترهای وارد شده بیشتر از حد مجاز است!',
        },

    )
    password = forms.CharField(
        label='کلمه عبور',
        widget=forms.PasswordInput(attrs=attr),
        error_messages={
            'required': 'لطفا رمز عبور را وارد نمایید',
        }
    )

    class Meta:
        model = User
        fields = ['mobile', 'password']


class MobileLoginForm(forms.ModelForm):
    mobile = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control w-50 text-center border-1 mb-2',
            'placeholder': 'شماره همراه خود را وارد کنید',
            # 'style': 'font-size: 13px;'  # Inline style for placeholder font size
        }),
        required=True,
        max_length=11,
        min_length=11,
        error_messages={
            'required': 'لطفا شماره موبایل را وارد نمایید',
            'min_length': 'تعداد کاراکترهای وارد شده کمتر از حد مجاز است!',
            'max_length': 'تعداد کاراکترهای وارد شده بیشتر از حد مجاز است!',
        },
    )

    class Meta:
        model = User
        fields = ['mobile', ]


class VerifyForm(forms.ModelForm):
    otp = forms.CharField(
        widget=forms.NumberInput(attrs={'placeholder': 'رمز یکبار مصرف'})
    )

    class Meta:
        model = User
        fields = ['otp']


CALL_CHOICES = [
    (True, 'بله تمایل دارم'),
    (False, 'خیر تمایل ندارم'),
]


class SupportUserForm(forms.ModelForm):
    subject = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr),
                              label='موضوع')
    message = forms.CharField(widget=CKEditorUploadingWidget(),
                              error_messages=error_message, label='پیام')
    # is_closed = forms.ChoiceField(label='بستن تیکت', required=True,
    #                               error_messages=error_message, choices=CHOICES, widget=forms.Select(attrs=attr))
    is_call = forms.ChoiceField(
        label='در صورت نیاز، جهت تسریع در حل مشکلتان، مایل هستید با شما تماس بگیریم؟',
        choices=CALL_CHOICES,
        widget=forms.RadioSelect,  # نمایش به صورت رادیو باتن
        required=True,
        initial=False

    )

    class Meta:
        model = SupportUser
        fields = ['subject', 'message', 'is_call']


class SupportMessageForm(forms.ModelForm):
    message = forms.CharField(widget=CKEditorUploadingWidget(),
                              error_messages=error_message, label='پیام', required=True)

    attachments = forms.FileField(
        required=False, error_messages=error_message,
    )

    class Meta:
        model = SupportMessage
        fields = ['message', 'attachments']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }


# =========================================

class MiddleAdminTicketForm(forms.ModelForm):
    subject = forms.CharField(error_messages=error_message, required=True, widget=forms.TextInput(attrs=attr),
                              label='موضوع')
    message = forms.CharField(widget=CKEditorUploadingWidget(),
                              error_messages=error_message, label='پیام')
    # is_closed = forms.ChoiceField(label='بستن تیکت', required=True,
    #                               error_messages=error_message, choices=CHOICES, widget=forms.Select(attrs=attr))
    is_call = forms.ChoiceField(
        label='در صورت نیاز، جهت تسریع در حل مشکلتان، مایل هستید با شما تماس بگیریم؟',
        choices=CALL_CHOICES,
        widget=forms.RadioSelect,  # نمایش به صورت رادیو باتن
        required=True,
        initial=False

    )

    class Meta:
        model = AdminTicket
        fields = ['subject', 'message', 'is_call']


class MiddleAdminMessageForm(forms.ModelForm):
    message = forms.CharField(widget=CKEditorUploadingWidget(),
                              error_messages=error_message, label='پیام', required=True)

    attachments = forms.FileField(
        required=False, error_messages=error_message,
    )

    class Meta:
        model = AdminTicketMessage
        fields = ['message', 'attachments']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }


class UnitReportForm(forms.Form):
    unit = forms.ModelChoiceField(
        queryset=Unit.objects.none(),  # خالی → ajax پرش می‌کنه
        required=True,
        label='انتخاب واحد',
        widget=forms.Select(
            attrs={
                'class': 'form-control-sm select2-ajax rtl',
                'style': 'width:100%',
                # 'data-placeholder': 'واحد / مالک یا مستاجر را انتخاب کنید1'
            }
        )
    )

    class Meta:
        model = Unit
        fields = ['unit']

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

        # نمایش نام مستاجر فعال یا مالک
        self.fields['unit'].label_from_instance = lambda obj: (
            f"واحد {obj.unit} - {obj.get_active_renter().renter_name}"
            if obj.get_active_renter() else
            f"واحد {obj.unit} - {obj.owner_name}"
        )


class UserPayMoneyForm(forms.ModelForm):
    amount = forms.CharField(error_messages=error_message, max_length=20, required=True,
                             widget=forms.TextInput(attrs=attr),
                             label='مبلغ')
    description = forms.CharField(error_messages=error_message, widget=forms.TextInput(attrs=attr), required=True,
                                  label='شرح سند')
    document = forms.FileField(
        required=False,
        error_messages=error_message,
        widget=forms.ClearableFileInput(attrs=attr),
        label='تصویر سند'
    )
    register_date = JalaliDateField(
        label='تاریخ ثبت سند',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=False
    )
    details = forms.CharField(error_messages=error_message, required=False,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
                              label='توضیحات ')

    class Meta:
        model = UserPayMoney
        fields = ['amount', 'description', 'details', 'document', 'register_date']

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


class UserPayForm(forms.ModelForm):
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
        model = UserPayMoney
        fields = ['bank', 'transaction_reference', 'payment_date']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            banks = Bank.objects.filter(is_active=True, user=user)
            self.fields['bank'].queryset = banks

            # پیدا کردن بانک پیش‌فرض
            default_bank = banks.filter(is_default=True).first()
            if default_bank:
                self.fields['bank'].initial = default_bank

            # تغییر label برای نمایش "(پیش‌فرض)" کنار نام بانک
            self.fields['bank'].label_from_instance = lambda obj: f"{obj.bank_name} - {obj.account_no}" + (
                " (پیش‌فرض)" if obj.is_default else "")


class UserPayGateForm(forms.ModelForm):
    payment_date = JalaliDateField(
        label='تاریخ پرداخت',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        required=False
    )
    transaction_reference = forms.IntegerField(
        label='کد پیگیری',
        min_value=0,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    bank = forms.ModelChoiceField(
        queryset=Bank.objects.none(),
        label='شماره کارت',
        required=True,
        empty_label="شماره کارت را انتخاب کنید",
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'})
    )

    class Meta:
        model = UserPayMoney
        fields = ['payment_date', 'transaction_reference', 'bank']

    def __init__(self, *args, **kwargs):
        house = kwargs.pop('house', None)  # خانه را از view می‌گیریم
        super().__init__(*args, **kwargs)

        # بانک‌ها پیش‌فرض خالی
        self.fields['bank'].queryset = Bank.objects.none()

        if house:
            # همه بانک‌های فعال خانه
            banks = Bank.objects.filter(is_active=True, house=house).order_by('-is_default', 'bank_name')
            self.fields['bank'].queryset = banks

            # بانک پیش‌فرض خانه
            default_bank = banks.filter(is_default=True).first()
            if default_bank:
                self.fields['bank'].initial = default_bank

            # نمایش label با "(پیش‌فرض)"
            self.fields['bank'].label_from_instance = lambda obj: f"{obj.bank_name} - {obj.cart_number}" + (
                " (پیش‌فرض)" if obj.is_default else "")
