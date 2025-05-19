from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from user_app import helper
from admin_panel.models import Announcement, FixedChargeCalc
from user_app.forms import LoginForm, MobileLoginForm
from user_app.models import User, Unit


def index(request):
    announcements = Announcement.objects.filter(is_active=True).order_by('-created_at')[:4]
    form = LoginForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            mobile = form.cleaned_data['mobile']
            password = form.cleaned_data['password']
            user = authenticate(request, username=mobile, password=password)
            if user is not None:
                login(request, user)
                if user.is_superuser:
                    return redirect(reverse('admin_dashboard'))  # Superuser route
                else:
                    return redirect(reverse('user_panel'))  # Regular user route (change as needed)

        messages.error(request, 'شماره موبایل یا کلمه عبور نادرست است!')
        return redirect(reverse('index'))

    return render(request, 'index.html', {
        'announcements': announcements,
        'form': form,
    })


def mobile_login(request):
    form = MobileLoginForm(request.POST or None)
    if request.method == 'POST':
        mobile = request.POST.get('mobile')
        if mobile:
            user = User.objects.filter(mobile=mobile).first()
            if user:
                otp = helper.get_random_otp()
                # helper.send_otp(mobile, otp)  # Uncomment to send OTP
                print("OTP1:", otp)
                user.otp = otp
                user.otp_create_time = timezone.now()
                user.save()

                request.session['user_mobile'] = user.mobile
                return HttpResponseRedirect(reverse('verify_otp'))
            else:
                messages.error(request, 'کاربر با این شماره همراه یافت نشد!')
                return redirect(reverse('mobile_login'))
    return render(request, 'mobile_Login.html', {'form': form})


def verify_otp(request):
    mobile = request.session.get('user_mobile')

    if not mobile:
        return redirect('mobile_login')

    try:
        user = User.objects.get(mobile=mobile)

        if request.method == "POST":
            # Combine OTP inputs from multiple fields
            otp_input = ''.join([request.POST.get(f'otp{i}', '') for i in range(1, 6)])

            # Check OTP expiration
            if not helper.check_otp_expiration(user.mobile):
                messages.error(request, "رمز یکبار مصرف منقضی شده است. تلاش مجدد!")
                return redirect('mobile_login')

            # Validate OTP
            if str(user.otp) != otp_input:
                messages.error(request, "رمز یکبار مصرف وارد شده اشتباه است!")
                return redirect('verify_otp')
            else:
                login(request, user)
                messages.success(request, "ورود موفق")
                return redirect('admin_dashboard')

        return render(
            request,
            'verify_login.html',
            {
                "mobile": mobile,
                "user": user,
            }
        )

    except User.DoesNotExist:
        messages.error(request, "کاربری با این شماره موبایل یافت نشد.")
        return redirect('mobile_login')


def resend_otp(request):
    try:
        mobile = request.session.get('user_mobile')
        user = User.objects.get(mobile=mobile)

        new_otp = helper.get_random_otp()
        # helper.send_otp(mobile, new_otp)
        print(f' new_otp: {new_otp}')
        user.otp = new_otp
        user.otp_create_time = timezone.now()
        user.save()
        messages.add_message(request, messages.SUCCESS, "رمز یکبار مصرف جدید ارسال شد!")

        # Redirect back to the verification page
        return HttpResponseRedirect(reverse('verify_otp'))

    except User.DoesNotExist:
        messages.error(request, 'User does not exist.')
        return HttpResponseRedirect(reverse('index'))


def site_header_component(request):
    context = {
        'user': request.user,
        # اگر اعلان داری می‌توانی اعلان‌ها را هم اضافه کنی مثلا:
        # 'notifications': Notification.objects.filter(user=request.user, is_read=False),
    }
    return render(request, 'partials/notification_template.html', context)


def user_panel(request):
    units = Unit.objects.filter(user=request.user, is_active=True).prefetch_related('renters')

    units_with_active_renter = []
    for unit in units:
        active_renter = unit.renters.filter(renter_is_active=True).first()
        units_with_active_renter.append((unit, active_renter))

    context = {
        'user': request.user,
        'units': units
    }
    return render(request, 'partials/home_template.html', context)


# def fetch_user_fixed_charges(request):
#     charges = FixedChargeCalc.objects.filter(user=request.user, send_notification=True).select_related('unit').order_by(
#         '-created_at')
#     return render(request, 'fixed_charges.html', {'charges': charges})

@login_required
def fetch_user_fixed_charges(request):
    unit = Unit.objects.filter(user=request.user, is_active=True).first()
    charges = FixedChargeCalc.objects.filter(
        user=request.user,
        send_notification=True
    ).select_related('unit').order_by('-created_at')

    return render(request, 'fixed_charges.html', {
        'charges': charges,
        'unit': unit
    })
