import io
import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView, CreateView, ListView, DetailView
from pypdf import PdfWriter
from weasyprint import CSS, HTML

from admin_panel.forms import UnifiedChargePaymentForm
from middleAdmin_panel.views import middle_admin_required
from notifications.models import Notification, SupportUser
from user_app import helper
from admin_panel.models import Announcement, UnifiedCharge, MessageToUser
from user_app.forms import LoginForm, MobileLoginForm
from user_app.models import User, Unit, Bank, MyHouse, CalendarNote


def index(request):
    form = LoginForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        mobile = form.cleaned_data['mobile']
        password = form.cleaned_data['password']
        print("Mobile:", mobile)
        print("Password entered:", password)

        user = authenticate(request, username=mobile, password=password)
        # print("Authenticated user:", user)

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
                # messages.success(request, "ورود موفق")
                return redirect('user_panel')

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


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def user_panel(request):
    user = request.user

    # -------------------------
    # Unified Charges
    # -------------------------
    units = Unit.objects.filter(
        is_active=True
    ).filter(
        Q(user=user) |  # مالک
        Q(renters__user=user, renters__renter_is_active=True)  # مستاجر فعال
    ).distinct()

    unified_qs = UnifiedCharge.objects.filter(
        unit__in=units
    ).select_related('unit')

    paid_unified_qs = unified_qs.filter(is_paid=True)
    unpaid_unified_qs = unified_qs.filter(is_paid=False)

    # Update penalty ONLY for unpaid charges
    # for charge in unpaid_unified_qs:
    #     charge.update_penalty()

    # -------------------------
    # STATISTICS
    # -------------------------
    total_charge = unified_qs.count()
    total_charge_unpaid = unpaid_unified_qs.count()

    total_paid_amount = (
            paid_unified_qs.aggregate(
                total=Sum("total_charge_month")
            )["total"] or 0
    )

    # -------------------------
    # LAST CHARGES
    # -------------------------
    last_charges = unified_qs.order_by('-created_at')[:6]

    # -------------------------
    # TICKETS
    # -------------------------
    tickets = SupportUser.objects.filter(user=user).order_by('-created_at')[:5]
    ticket_count = tickets.count()

    # -------------------------
    # UNITS & ANNOUNCEMENTS
    # -------------------------
    if user.is_middle_admin:
        units = (
            Unit.objects
            .filter(user__manager=user, is_active=True)
            .prefetch_related('renters')
        )
        announcements = (
            Announcement.objects
            .filter(user=user, is_active=True)
            .order_by('-created_at')[:5]
        )
    else:
        units = (
            Unit.objects
            .filter(user=user, is_active=True)
            .prefetch_related('renters')
        )
        announcements = (
            Announcement.objects
            .filter(user=user.manager, is_active=True)
            .order_by('-created_at')[:5]
        )

    # -------------------------
    # ACTIVE RENTERS PER UNIT
    # -------------------------
    units_with_details = [
        {
            "unit": unit,
            "active_renter": unit.renters.filter(renter_is_active=True).first()
        }
        for unit in units
    ]

    # -------------------------
    # CONTEXT
    # -------------------------
    context = {
        "user": user,
        "units": units,
        "units_with_details": units_with_details,

        "tickets": tickets,
        "ticket": ticket_count,

        "announcements": announcements,

        "total_charge": total_charge,
        "total_charge_unpaid": total_charge_unpaid,
        "total_paid_amount": total_paid_amount,

        "last_charges": last_charges,
        "unpaid_charges": unpaid_unified_qs,
    }

    return render(request, 'partials/home_template.html', context)


# ==================================

def fetch_user_charges(request):
    user = request.user
    query = request.GET.get('q', '').strip()
    paginate = request.GET.get('paginate', '20')

    # واحدهایی که کاربر به‌عنوان مالک یا مستاجر فعال دارد
    units = Unit.objects.filter(
        is_active=True
    ).filter(
        Q(user=user) |  # مالک
        Q(renters__user=user, renters__renter_is_active=True)  # مستاجر فعال
    ).distinct()

    charges = UnifiedCharge.objects.filter(
        unit__in=units
    ).select_related('unit')

    for charge in charges:
        charge.update_penalty()

    if query:
        charges = charges.filter(
            Q(title__icontains=query) |
            Q(details__icontains=query)
        )

    charges = charges.order_by('-created_at')

    try:
        paginate = int(paginate)
    except ValueError:
        paginate = 20

    paginator = Paginator(charges, paginate)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'paginate': paginate,
    }
    return render(request, 'manage_charges.html', context)


# ======================== Pdf Charges ===================

@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def export_charge_pdf(request, pk):
    charge = get_object_or_404(UnifiedCharge, pk=pk)

    house = None
    bank = None

    # 1️⃣ پیدا کردن خانه از روی واحد
    if charge.unit:
        # اگر Unit به MyHouse وصل است
        # ⚠️ اگر Unit هنوز FK به MyHouse نداره، باید اضافه بشه
        house = charge.unit.myhouse  # ← اسم FK واقعی توی مدل Unit

    # 2️⃣ بانک پیش‌فرض مربوط به همان خانه
    if house:
        bank = Bank.objects.filter(house=house, is_default=True, is_active=True).first()

    template = get_template('middleCharge/single_charge_pdf.html')
    html_string = template.render({'charge': charge,
                                   'house': house,
                                   'bank': bank,
                                   'font_url': request.build_absolute_uri('/static/fonts/Vazir.ttf')
                                   })

    css = CSS(string=f"""
        @page {{ size: A5 portrait; margin: 1cm; }}
        body {{
            font-family: 'Vazir', sans-serif;
        }}
        @font-face {{
            font-family: 'Vazira', sans-serif;
    
        }}
    """)

    pdf_file = io.BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(pdf_file, stylesheets=[css])
    pdf_file.seek(0)

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment;filename=charge_unit:{charge.unit.unit}.pdf'
    return response


@method_decorator(login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN), name='dispatch')
class AnnouncementListView(ListView):
    model = Announcement
    template_name = 'manage_announcement.html'
    context_object_name = 'announcements'

    def get_paginate_by(self, queryset):
        paginate = self.request.GET.get('paginate')
        if paginate == '1000':
            return None  # نمایش همه آیتم‌ها
        return int(paginate or 20)

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'manager') or not user.manager:
            return Announcement.objects.none()

        query = self.request.GET.get('q', '')
        queryset = Announcement.objects.filter(
            user=user.manager,
            is_active=True
        )

        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
            )

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['paginate'] = self.request.GET.get('paginate', '20')
        return context


@method_decorator(login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN), name='dispatch')
class MessageListView(ListView):
    template_name = 'user_message.html'
    context_object_name = 'user_messages'

    def get_paginate_by(self, queryset):
        paginate = self.request.GET.get('paginate')
        if paginate == '1000':
            return None  # نمایش همه آیتم‌ها
        return int(paginate or 20)

    def get_queryset(self):
        user = self.request.user
        query = self.request.GET.get('q', '')
        queryset = MessageToUser.objects.filter(
            user=user,
            is_active=True
        )
        queryset.update(is_seen=True)

        if query:
            queryset = queryset.filter(
                Q(user__full_name__icontains=query) |
                Q(title__icontains=query) |
                Q(message__icontains=query)
            ).distinct()

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['paginate'] = self.request.GET.get('paginate', '20')
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def user_profile(request):
    user = request.user

    # اگر فرم ارسال شد
    if request.method == 'POST':
        password_form = PasswordChangeForm(user, request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, user)  # مهم: کاربر بعد از تغییر رمز لاگ‌اوت نشود
            messages.success(request, 'رمز عبور با موفقیت تغییر کرد!')
            return redirect('user_profile')  # redirect باعث می‌شود پیام ظاهر شود
        else:
            messages.warning(request, 'رمز عبور باید حداقل 8 رقم و شامل حروف و اعداد باشد. مجددا بررسی فرمایید.')
    else:
        password_form = PasswordChangeForm(user)

    # اطلاعات واحد
    unit = Unit.objects.filter(user=user).first()

    context = {
        'user_obj': user,
        'unit': unit,
        'password_form': password_form,
    }
    return render(request, 'my_profile.html', context)
