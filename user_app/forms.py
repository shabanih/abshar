from django import forms
from django.core.validators import RegexValidator

from user_app.models import User

attr = {'class': 'form-control border-1 py-2 mb-4 placeholder-gray', }


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

