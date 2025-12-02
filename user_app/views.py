import io
import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Sum
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, CreateView, ListView, DetailView
from pypdf import PdfWriter
from weasyprint import CSS, HTML

from notifications.models import Notification, SupportUser
from user_app import helper
from admin_panel.models import Announcement, FixedChargeCalc, AreaChargeCalc, PersonCharge, PersonChargeCalc, \
    FixPersonChargeCalc, FixAreaChargeCalc, ChargeByPersonAreaCalc, ChargeByFixPersonAreaCalc, ChargeFixVariableCalc, \
    FixCharge, AreaCharge, FixPersonCharge, FixAreaCharge, ChargeByPersonArea, ChargeByFixPersonArea
from user_app.forms import LoginForm, MobileLoginForm
from user_app.models import User, Unit, Bank, MyHouse, CalendarNote


def index(request):
    form = LoginForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        mobile = form.cleaned_data['mobile']
        password = form.cleaned_data['password']

        user = authenticate(request, username=mobile, password=password)

        if user:
            if user.is_superuser:
                messages.error(request, 'شما مجوز ورود از این صفحه را ندارید.')
            elif not user.is_active:
                messages.error(request, 'حساب کاربری شما غیرفعال است.')
            else:
                login(request, user)

                if user.is_middle_admin:
                    # بررسی ثبت ساختمان
                    has_house = MyHouse.objects.filter(user=user).exists()
                    if has_house:
                        return redirect('middle_admin_dashboard')
                    else:
                        return redirect('middle_manage_house')

                return redirect('user_panel')
        else:
            messages.error(request, 'ورود ناموفق: شماره موبایل یا کلمه عبور نادرست است.')

    return render(request, 'index.html', {'form': form})

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


def logout_user(request):
    logout(request)
    return redirect('index')


def site_header_component(request):
    context = {
        'user': request.user,
    }
    return render(request, 'partials/notification_template.html', context)


def user_panel(request):
    user = request.user

    # --- TICKETS ---
    tickets = SupportUser.objects.filter(user=user).order_by('-created_at')[:5]
    ticket_count = SupportUser.objects.filter(user=user).count()

    # --- CALCULATIONS (one pass counts) ---
    calculation_models = [
        FixedChargeCalc,
        AreaChargeCalc,
        PersonChargeCalc,
        FixPersonChargeCalc,
        FixAreaChargeCalc,
        ChargeByPersonAreaCalc,
        ChargeByFixPersonAreaCalc,
        ChargeFixVariableCalc,
    ]

    total_charge = 0
    total_charge_unpaid = 0
    total_unpaid_amount = 0

    for model in calculation_models:
        qs = model.objects.filter(user=user)
        total_charge += qs.count()
        total_charge_unpaid += qs.filter(is_paid=False).count()

        result = model.objects.filter(
            user=request.user,
            is_paid=False
        ).aggregate(total=Sum("total_charge_month"))

        total_unpaid_amount += result["total"] or 0

    # --- UNITS & ANNOUNCEMENTS ---
    if user.is_middle_admin:
        units = Unit.objects.filter(user__manager=user, is_active=True).prefetch_related('renters')
        announcements = Announcement.objects.filter(user=user, is_active=True).order_by('-created_at')[:5]

    else:
        units = Unit.objects.filter(user=user, is_active=True).prefetch_related('renters')
        announcements = Announcement.objects.filter(
            is_active=True,
            user=user.manager
        ).order_by('-created_at')[:5]

    # --- ACTIVE RENTERS PER UNIT ---
    units_with_details = []
    for unit in units:
        active_renter = unit.renters.filter(renter_is_active=True).first()
        units_with_details.append({
            "unit": unit,
            "active_renter": active_renter
        })

    context = {
        "user": user,
        "units": units,
        "tickets": tickets,
        "ticket": ticket_count,
        "announcements": announcements,
        "units_with_details": units_with_details,
        "total_charge": total_charge,
        "total_charge_unpaid": total_charge_unpaid,
        'total_unpaid_amount': total_unpaid_amount
    }

    return render(request, 'partials/home_template.html', context)


# ==================================

def get_user_charges(model, user):
    return model.objects.filter(
        user=user,
        send_notification=True
    ).select_related('unit').order_by('-created_at')


@login_required
def fetch_user_fixed_charges(request):
    unit = Unit.objects.filter(user=request.user, is_active=True).first()

    charges = get_user_charges(FixedChargeCalc, request.user)
    area_charges = get_user_charges(AreaChargeCalc, request.user)
    person_charges = get_user_charges(PersonChargeCalc, request.user)
    fix_person_charges = get_user_charges(FixPersonChargeCalc, request.user)
    fix_area_charges = get_user_charges(FixAreaChargeCalc, request.user)
    person_area_charges = get_user_charges(ChargeByPersonAreaCalc, request.user)
    fix_person_area_charges = get_user_charges(ChargeByFixPersonAreaCalc, request.user)
    fix_variable_charges = get_user_charges(ChargeFixVariableCalc, request.user)

    context = {
        'unit': unit,
        'charges': charges,
        'area_charges': area_charges,
        'person_charges': person_charges,
        'fix_person_charges': fix_person_charges,
        'fix_area_charges': fix_area_charges,
        'person_area_charges': person_area_charges,
        'fix_person_area_charges': fix_person_area_charges,
        'fix_variable_charges': fix_variable_charges,
    }

    return render(request, 'manage_charges.html', context)


# ========================= Pdf Charges ===================
def export_fix_variable_charge_pdf(request, pk, charge_type=None):
    charge = get_object_or_404(ChargeFixVariableCalc, pk=pk)
    user = request.user

    # دریافت مدیر میانی
    manager = user.manager

    # بانک‌های ثبت‌شده توسط مدیر
    bank = Bank.objects.filter(user=manager, is_active=True).first()

    # ساختمان‌های ثبت‌شده توسط مدیر
    house = MyHouse.objects.filter(user=manager, is_active=True).first()
    template = get_template('pdf/fix_variable_pdf.html')
    html_string = template.render({'charge': charge,
                                   'bank': bank,
                                   'house': house,
                                   })
    font_url = request.build_absolute_uri('/static/fonts/BYekan.ttf')
    css = CSS(string=f"""
        @page {{ size: A5 portrait; margin: 1cm; }}
        body {{
            font-family: 'BYekan', sans-serif;
        }}
        @font-face {{
            font-family: 'BYekan';
            src: url('{font_url}');
        }}
    """)

    pdf_file = io.BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(pdf_file, stylesheets=[css])
    pdf_file.seek(0)

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment;filename=charge_unit:{charge.unit.unit}.pdf'
    return response


def export_person_charge_pdf(request, pk, charge_type=None):
    charge = get_object_or_404(PersonChargeCalc, pk=pk)
    user = request.user

    # دریافت مدیر میانی
    manager = user.manager

    # بانک‌های ثبت‌شده توسط مدیر
    bank = Bank.objects.filter(user=manager, is_active=True).first()

    # ساختمان‌های ثبت‌شده توسط مدیر
    house = MyHouse.objects.filter(user=manager, is_active=True).first()
    template = get_template('pdf/person_charge_pdf.html')
    html_string = template.render({'charge': charge,
                                   'bank': bank,
                                   'house': house,
                                   })
    font_url = request.build_absolute_uri('/static/fonts/BYekan.ttf')
    css = CSS(string=f"""
        @page {{ size: A5 portrait; margin: 1cm; }}
        body {{
            font-family: 'BYekan', sans-serif;
        }}
        @font-face {{
            font-family: 'BYekan';
            src: url('{font_url}');
        }}
    """)

    pdf_file = io.BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(pdf_file, stylesheets=[css])
    pdf_file.seek(0)

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment;filename=charge_unit:{charge.unit.unit}.pdf'
    return response


def export_area_charge_pdf(request, pk, charge_type=None):
    charge = get_object_or_404(AreaChargeCalc, pk=pk)
    user = request.user

    # دریافت مدیر میانی
    manager = user.manager

    # بانک‌های ثبت‌شده توسط مدیر
    bank = Bank.objects.filter(user=manager, is_active=True).first()

    # ساختمان‌های ثبت‌شده توسط مدیر
    house = MyHouse.objects.filter(user=manager, is_active=True).first()
    template = get_template('pdf/area_charge_pdf.html')
    html_string = template.render({'charge': charge,
                                   'bank': bank,
                                   'house': house,
                                   })
    font_url = request.build_absolute_uri('/static/fonts/BYekan.ttf')
    css = CSS(string=f"""
        @page {{ size: A5 portrait; margin: 1cm; }}
        body {{
            font-family: 'BYekan', sans-serif;
        }}
        @font-face {{
            font-family: 'BYekan';
            src: url('{font_url}');
        }}
    """)

    pdf_file = io.BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(pdf_file, stylesheets=[css])
    pdf_file.seek(0)

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment;filename=charge_unit:{charge.unit.unit}.pdf'
    return response


def export_fix_person_area_charge_pdf(request, pk, charge_type=None):
    charge = get_object_or_404(ChargeByFixPersonAreaCalc, pk=pk)
    user = request.user

    # دریافت مدیر میانی
    manager = user.manager

    # بانک‌های ثبت‌شده توسط مدیر
    bank = Bank.objects.filter(user=manager, is_active=True).first()

    # ساختمان‌های ثبت‌شده توسط مدیر
    house = MyHouse.objects.filter(user=manager, is_active=True).first()
    template = get_template('pdf/fix_person_area_pdf.html')
    html_string = template.render({'charge': charge,
                                   'bank': bank,
                                   'house': house,
                                   })
    font_url = request.build_absolute_uri('/static/fonts/BYekan.ttf')
    css = CSS(string=f"""
        @page {{ size: A5 portrait; margin: 1cm; }}
        body {{
            font-family: 'BYekan', sans-serif;
        }}
        @font-face {{
            font-family: 'BYekan';
            src: url('{font_url}');
        }}
    """)

    pdf_file = io.BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(pdf_file, stylesheets=[css])
    pdf_file.seek(0)

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment;filename=charge_unit:{charge.unit.unit}.pdf'
    return response


def export_fix_area_charge_pdf(request, pk, charge_type=None):
    charge = get_object_or_404(FixAreaChargeCalc, pk=pk)
    user = request.user

    # دریافت مدیر میانی
    manager = user.manager

    # بانک‌های ثبت‌شده توسط مدیر
    bank = Bank.objects.filter(user=manager, is_active=True).first()

    # ساختمان‌های ثبت‌شده توسط مدیر
    house = MyHouse.objects.filter(user=manager, is_active=True).first()
    template = get_template('pdf/fix_area_pdf.html')
    html_string = template.render({'charge': charge,
                                   'bank': bank,
                                   'house': house,
                                   })
    font_url = request.build_absolute_uri('/static/fonts/BYekan.ttf')
    css = CSS(string=f"""
        @page {{ size: A5 portrait; margin: 1cm; }}
        body {{
            font-family: 'BYekan', sans-serif;
        }}
        @font-face {{
            font-family: 'BYekan';
            src: url('{font_url}');
        }}
    """)

    pdf_file = io.BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(pdf_file, stylesheets=[css])
    pdf_file.seek(0)

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment;filename=charge_unit:{charge.unit.unit}.pdf'
    return response


def export_fix_person_charge_pdf(request, pk, charge_type=None):
    charge = get_object_or_404(FixPersonChargeCalc, pk=pk)
    user = request.user

    # دریافت مدیر میانی
    manager = user.manager

    # بانک‌های ثبت‌شده توسط مدیر
    bank = Bank.objects.filter(user=manager, is_active=True).first()

    # ساختمان‌های ثبت‌شده توسط مدیر
    house = MyHouse.objects.filter(user=manager, is_active=True).first()
    template = get_template('pdf/fix_person_pdf.html')
    html_string = template.render({'charge': charge,
                                   'bank': bank,
                                   'house': house,
                                   })
    font_url = request.build_absolute_uri('/static/fonts/BYekan.ttf')
    css = CSS(string=f"""
        @page {{ size: A5 portrait; margin: 1cm; }}
        body {{
            font-family: 'BYekan', sans-serif;
        }}
        @font-face {{
            font-family: 'BYekan';
            src: url('{font_url}');
        }}
    """)

    pdf_file = io.BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(pdf_file, stylesheets=[css])
    pdf_file.seek(0)

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment;filename=charge_unit:{charge.unit.unit}.pdf'
    return response


def export_fix_charge_pdf(request, pk, charge_type=None):
    charge = get_object_or_404(FixedChargeCalc, pk=pk)
    user = request.user

    # دریافت مدیر میانی
    manager = user.manager

    # بانک‌های ثبت‌شده توسط مدیر
    bank = Bank.objects.filter(user=manager, is_active=True).first()

    # ساختمان‌های ثبت‌شده توسط مدیر
    house = MyHouse.objects.filter(user=manager, is_active=True).first()
    # bank = Bank.objects.filter(user__manager=request.user, is_active=True).first()
    template = get_template('pdf/fix_charge_pdf.html')
    html_string = template.render({'charge': charge,
                                   'bank': bank,
                                   'house': house,
                                   })
    font_url = request.build_absolute_uri('/static/fonts/BYekan.ttf')
    css = CSS(string=f"""
        @page {{ size: A5 portrait; margin: 1cm; }}
        body {{
            font-family: 'BYekan', sans-serif;
        }}
        @font-face {{
            font-family: 'BYekan';
            src: url('{font_url}');
        }}
    """)

    pdf_file = io.BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(pdf_file, stylesheets=[css])
    pdf_file.seek(0)

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment;filename=charge_unit:{charge.unit.unit}.pdf'
    return response


def export_person_area_charge_pdf(request, pk, charge_type=None):
    charge = get_object_or_404(ChargeByPersonAreaCalc, pk=pk)
    user = request.user

    # دریافت مدیر میانی
    manager = user.manager

    # بانک‌های ثبت‌شده توسط مدیر
    bank = Bank.objects.filter(user=manager, is_active=True).first()

    # ساختمان‌های ثبت‌شده توسط مدیر
    house = MyHouse.objects.filter(user=manager, is_active=True).first()
    template = get_template('pdf/person_area_pdf.html')
    html_string = template.render({'charge': charge, 'bank': bank, 'house': house});
    font_url = request.build_absolute_uri('/static/fonts/BYekan.ttf')
    css = CSS(string=f"""
        @page {{ size: A5 portrait; margin: 1cm; }}
        body {{
            font-family: 'BYekan', sans-serif;
        }}
        @font-face {{
            font-family: 'BYekan';
            src: url('{font_url}');
        }}
    """)

    pdf_file = io.BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(pdf_file, stylesheets=[css])
    pdf_file.seek(0)

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment;filename=charge_unit:{charge.unit.unit}.pdf'
    return response


def user_announcements(request):
    user = request.user

    # اگر کاربر مدیر میانی ندارد، هیچ اطلاعیه‌ای ندارد
    if not user.manager:
        announcements = []
    else:
        # فقط اطلاعیه‌های مدیر میانی کاربر
        announcements = Announcement.objects.filter(
            user=user.manager,
            is_active=True
        ).order_by('-created_at')

    context = {
        'announcements': announcements
    }
    return render(request, 'manage_announcement.html', context)



