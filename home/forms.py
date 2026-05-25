from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms

from home.models import FreeRequest, ContactUs, Articles

error_message = {
    'required': "تکمیل این فیلد ضروری است!",
    'min_length': 'تعداد کاراکترهای وارد شده کمتر از حد مجاز است!',
    'max_length': 'تعداد کاراکترهای وارد شده بیشتر از حد مجاز است!',
}
attr = {'class': 'form-control border-1 py-2 mb-4 '}
attr0 = {'class': 'form-control form-control-sm border-1 py-1 mb-4 '}
attr1 = {'class': 'form-control border-1 py-1 mb-4 '}
attr3 = {'class': 'form-control form-control-sm border-1'}
attr2 = {'class': 'form-control gray-placeholder', 'placeholder': 'نام و نام خانوادگی '}
attr4 = {'class': 'form-control gray-placeholder', 'placeholder': 'شماره همراه'}


class FreeRequestForm(forms.ModelForm):
    name = forms.CharField(error_messages=error_message, max_length=20, widget=forms.TextInput(attrs=attr2),
                           required=True,
                           label='نام و نام خانوادگی ')
    mobile = forms.CharField(error_messages=error_message, required=True, widget=forms.NumberInput(
        attrs=attr4), label='شماره تماس')

    class Meta:
        model = FreeRequest
        fields = ['name', 'mobile']


class ContactUsForm(forms.ModelForm):
    name = forms.CharField(required=True, error_messages=error_message,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام و نام خانوادگی'}))
    subject = forms.CharField(required=True, error_messages=error_message,
                              widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'موضوع'}))
    mobile = forms.CharField(required=True, error_messages=error_message,
                             widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'شماره همراه یا ایمیل (درصورت نیاز به تماس شماره همراه را وارد نمایید)'}))
    message = forms.CharField(required=True, error_messages=error_message,
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': '6', 'cols': '10', 'placeholder': 'پیام شما'}))

    class Meta:
        model = ContactUs
        fields = ['name', 'subject', 'mobile', 'message']


class ArticleForm(forms.ModelForm):
    title = forms.CharField(required=True, error_messages=error_message, widget=forms.TextInput(attrs=attr),
                            label='عنوان ')
    description = forms.CharField(widget=CKEditorUploadingWidget())

    # template_name = forms.CharField(required=False, error_messages=error_message, widget=forms.TextInput(attrs=attr2),
    #                                 label='نام قالب')
    short_description = forms.CharField(required=False, error_messages=error_message,
                                        widget=forms.Textarea(attrs=attr4), label='شرح کوتاه')
    keywords = forms.CharField(required=False, error_messages=error_message,
                                        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': '6', 'cols': '10'}), label='کلمات کلیدی')
    image = forms.ImageField(required=True, error_messages=error_message, label='تصویر ')
    is_active = forms.BooleanField(required=False, error_messages=error_message, label='فعال/غیر فعال')

    class Meta:
        model = Articles
        fields = ['title', 'short_description', 'image', 'is_active', 'description', 'keywords']
