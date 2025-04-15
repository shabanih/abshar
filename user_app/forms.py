from django import forms

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
