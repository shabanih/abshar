from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import TemplateView

from admin_panel.models import Announcement
from user_app.forms import LoginForm


# Create your views here.

class AdminPanelView(TemplateView):
    pass


def index(request):
    announcements = Announcement.objects.filter(is_active=True).order_by('-created_at')[:4]
    form = LoginForm(request.POST or None)
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            mobile = form.cleaned_data['mobile']
            password = form.cleaned_data['password']
            user = authenticate(request, username=mobile, password=password)
            if user is not None:
                login(request, user)
                return redirect(reverse('dashboard'))
            else:
                messages.error(request, 'شماره موبایل یا کلمه عبور نادرست است!')
                return redirect(reverse('index'))
        else:
            messages.error(request, 'شماره موبایل یا کلمه عبور نادرست است!')
            return redirect(reverse('index'))

    context = {
        'announcements': announcements,
        'form': form

    }
    return render(request, 'index.html', context)


def mobile_login(request):
    return render(request, 'mobile_Login.html')


