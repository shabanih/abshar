from django import forms

from admin_panel.models import Announcement

attr = {'class': 'form-control border-1 py-2 mb-4 '}
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
