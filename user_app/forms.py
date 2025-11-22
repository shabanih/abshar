from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.core.validators import RegexValidator

from notifications.models import SupportUser, SupportMessage, AdminTicket, AdminTicketMessage
from user_app.models import User

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
            'style': 'font-size: 13px;'  # Inline style for placeholder font size
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
