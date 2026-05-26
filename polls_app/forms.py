from django import forms
from django.forms import modelformset_factory
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget

from .models import Poll, Choice, Question

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


class PollCreateForm(forms.ModelForm):
    title = forms.CharField(error_messages=error_message, widget=forms.TextInput(attrs=attr), required=True,
                            label='عنوان نظرسنجی')
    start_date = JalaliDateField(
        label='تاریخ شروع',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=True
    )
    end_date = JalaliDateField(
        label='تاریخ پایان',
        widget=AdminJalaliDateWidget(attrs={'class': 'form-control'}),
        error_messages=error_message, required=True
    )

    class Meta:
        model = Poll
        fields = [
            "title",
            "description",
            "start_date",
            "end_date",

        ]

        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "عنوان نظرسنجی"
            }),

            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "توضیحات"
            }),

            "start_date": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": "form-control",
                "placeholder": "تاریخ شروع"
            }),

            "end_date": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": "form-control",
                "placeholder": "تاریخ پایان"
            }),
        }



class QuestionForm(forms.ModelForm):

    class Meta:
        model = Question
        fields = [
            "title",
            "question_type",
            "order"
        ]

        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "متن سوال"
            }),

            "question_type": forms.Select(attrs={
                "class": "form-control"
            }),

            "order": forms.NumberInput(attrs={
                "class": "form-control"
            }),
        }



class ChoiceForm(forms.ModelForm):

    class Meta:
        model = Choice
        fields = ["title"]

        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "گزینه"
            })
        }

QuestionFormSet = modelformset_factory(
    Question,
    form=QuestionForm,
    extra=3,
    can_delete=True
)