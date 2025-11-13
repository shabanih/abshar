import io

from django.apps import apps
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView, CreateView, ListView, DetailView
from pypdf import PdfWriter
from weasyprint import CSS, HTML

from user_app import helper
from admin_panel.models import Announcement, FixedChargeCalc, AreaChargeCalc, PersonCharge, PersonChargeCalc, \
    FixPersonChargeCalc, FixAreaChargeCalc, ChargeByPersonAreaCalc, ChargeByFixPersonAreaCalc, ChargeFixVariableCalc
from user_app.forms import LoginForm, MobileLoginForm, SupportUserForm, SupportMessageForm
from user_app.models import User, Unit, Bank, MyHouse, SupportUser, SupportFile, SupportMessage


def index(request):
    announcements = Announcement.objects.filter(is_active=True).order_by('-created_at')[:4]
    form = LoginForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            mobile = form.cleaned_data['mobile']
            password = form.cleaned_data['password']
            user = authenticate(request, username=mobile, password=password)
            if user is not None and user.is_active:
                login(request, user)
                if user.is_superuser:
                    return redirect(reverse('admin_dashboard'))
                elif user.is_middle_admin:
                    return redirect(reverse('middle_admin_dashboard'))
                else:
                    return redirect(reverse('user_panel'))

            messages.error(request, 'ورود ناموفق: شماره موبایل یا کلمه عبور نادرست است.')

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


def logout_user(request):
    logout(request)
    return redirect('index')


def site_header_component(request):
    context = {
        'user': request.user,
        # اگر اعلان داری می‌توانی اعلان‌ها را هم اضافه کنی مثلا:
        # 'notifications': Notification.objects.filter(user=request.user, is_read=False),
    }
    return render(request, 'partials/notification_template.html', context)


def user_panel(request):
    user = request.user

    # 🧠 If this user is a middle admin
    if user.is_middle_admin:
        # Show their own announcements + their managed units
        units = Unit.objects.filter(user__manager=user, is_active=True).prefetch_related('renters')
        announcements = Announcement.objects.filter(user=user, is_active=True).order_by('-created_at')[:4]

    else:
        # 🧠 If this user is a normal user
        units = Unit.objects.filter(user=user, is_active=True).prefetch_related('renters')

        # Show announcements from this user's manager (middle admin)
        announcements = Announcement.objects.filter(
            is_active=True,
            user=user.manager
        ).order_by('-created_at')[:4]

    # find active renters for each unit
    units_with_active_renter = []
    for unit in units:
        active_renter = unit.renters.filter(renter_is_active=True).first()
        units_with_active_renter.append((unit, active_renter))

    units_with_details = []
    for unit in units:
        active_renter = unit.renters.filter(renter_is_active=True).first()
        units_with_details.append({
            'unit': unit,
            'active_renter': active_renter,

        })

    context = {
        'user': user,
        'units': units,
        'announcements': announcements,
        'units_with_active_renter': units_with_active_renter,
        'units_with_details': units_with_details,
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


class SupportUserCreateView(CreateView):
    model = SupportUser
    template_name = 'send_ticket.html'
    form_class = SupportUserForm
    success_url = reverse_lazy('user_support_ticket')

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.user = self.request.user
        obj.save()

        # Handle multiple files manually
        files = self.request.FILES.getlist('file')
        for f in files:
            SupportFile.objects.create(support_user=obj, file=f)

        initial_message = form.cleaned_data.get('message')
        if initial_message:
            msg = SupportMessage.objects.create(
                support_user=obj,
                sender=self.request.user,
                message=initial_message
            )

            # اگر فایل‌ها مربوط به پیام هستند
            for f in files:
                file_obj = SupportFile.objects.create(support_user=obj, file=f)
                msg.attachments.add(file_obj)

        messages.success(
            self.request,
            'تیکت با موفقیت ارسال گردید. کارشناسان ما طی ۳ تا ۵ ساعت آینده پاسخ خواهند داد.'
        )

        # ✅ بدون ذخیره دوباره فرم
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tickets'] = SupportUser.objects.filter(
            user=self.request.user
        ).order_by('-created_at')
        return context


class TicketsView(ListView):
    model = SupportUser
    template_name = 'user_ticket.html'
    context_object_name = 'tickets'

    def get_paginate_by(self, queryset):
        paginate = self.request.GET.get('paginate')
        if paginate == '1000':
            return None  # نمایش همه
        return int(paginate or 20)

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        qs = SupportUser.objects.filter(user=self.request.user)
        if query:
            qs = qs.filter(
                Q(subject__icontains=query) |
                Q(message__icontains=query) |
                Q(ticket_no__icontains=query)
            )
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


def user_ticket_detail(request, pk):
    ticket = get_object_or_404(SupportUser, id=pk)
    form = SupportMessageForm()

    if request.method == 'POST':
        form = SupportMessageForm(request.POST, request.FILES)
        files = request.FILES.getlist('attachments')
        if form.is_valid():
            msg = form.save(commit=False)
            msg.support_user = ticket
            msg.sender = request.user
            msg.save()
            for f in files:
                file_obj = SupportFile.objects.create(file=f)
                msg.attachments.add(file_obj)
            # تغییر وضعیت تیکت بعد از پاسخ
            ticket.is_answer = True
            ticket.is_closed = False
            ticket.save()
            messages.success(request, "پیام با موفقیت ارسال شد.")
            return redirect('ticket_detail', pk=ticket.id)

    messages_list = ticket.messages.order_by('-created_at')
    return render(request, 'ticket_details.html', {
        'ticket': ticket,
        'messages': messages_list,
        'form': form
    })


def close_ticket(request, pk):
    ticket = get_object_or_404(SupportUser, id=pk)
    ticket.is_closed = True
    ticket.save()
    return redirect('ticket_detail', pk=ticket.id)
