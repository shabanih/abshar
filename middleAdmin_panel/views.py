import io
import json
import logging
import os
import time
from datetime import timezone, datetime
from decimal import Decimal
from itertools import chain
from django.apps import apps
from django.conf.urls.static import static
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models.functions import ExtractMonth
from django.utils import timezone
import jdatetime
import openpyxl
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import user_passes_test, login_required
from django.db import transaction, IntegrityError, models
from django.db.models import ProtectedError, Count, Q, Sum, F
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template, render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, UpdateView, DetailView, ListView
from openpyxl.styles import PatternFill, Alignment, Font
from pypdf import PdfWriter
from sweetify import sweetify
from weasyprint import CSS, HTML

from admin_panel import helper
from admin_panel.forms import announcementForm, BankForm, UnitForm, ExpenseCategoryForm, ExpenseForm, \
    IncomeCategoryForm, IncomeForm, ReceiveMoneyForm, PayerMoneyForm, PropertyForm, MaintenanceForm, FixChargeForm, \
    FixAreaChargeForm, AreaChargeForm, PersonChargeForm, FixPersonChargeForm, PersonAreaChargeForm, \
    PersonAreaFixChargeForm, VariableFixChargeForm, MyHouseForm, SmsForm, RenterAddForm, ExpensePayForm, IncomePayForm, \
    SmsCreditForm, SubscriptionPlanForm
from admin_panel.helper import send_notify_user_by_sms
from admin_panel.models import Announcement, ExpenseCategory, Expense, Fund, ExpenseDocument, IncomeCategory, Income, \
    IncomeDocument, ReceiveMoney, ReceiveDocument, PayMoney, PayDocument, Property, PropertyDocument, Maintenance, \
    MaintenanceDocument, FixCharge, AreaCharge, PersonCharge, \
    FixAreaCharge, FixPersonCharge, ChargeByPersonArea, \
    ChargeByFixPersonArea, ChargeFixVariable, SmsManagement, \
    UnifiedCharge, SmsCredit, SubscriptionPlan, Subscription
from admin_panel.services.calculators import CALCULATORS
from middleAdmin_panel.services.unit_services import UnitUpdateService
from notifications.models import Notification, SupportUser
from notifications.services.sms_service import SmsService
from polls.templatetags.poll_extras import show_jalali

from user_app.models import Bank, Unit, User, Renter, MyHouse, UnitResidenceHistory


def middle_admin_required(view_func):
    return user_passes_test(
        lambda u: u.is_authenticated and getattr(u, 'is_middle_admin', False),
        login_url=settings.LOGIN_URL_MIDDLE_ADMIN
    )(view_func)


# ========================== Subscription =====================
def buy_subscription(request):
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('duration')

    managed_users = request.user.managed_users.all()
    unit_count = Unit.objects.filter(
        Q(user=request.user) | Q(user__in=managed_users),
        is_active=True,
    ).count()

    if request.method == "POST":
        try:
            units = int(request.POST.get("units_count"))
        except ValueError:
            sweetify.error(request, "تعداد واحد نامعتبر است.")
            return redirect("buy_subscription")

        # بررسی اینکه عدد وارد شده کمتر از تعداد واقعی نباشد
        if units < unit_count:
            messages.error(
                request,
                f"تعداد واحد وارد شده نمی‌تواند کمتر از تعداد ثبت‌شده ({unit_count}) باشد."
            )
            return redirect("buy_subscription")

        plan_id = int(request.POST.get("plan"))
        plan = SubscriptionPlan.objects.get(id=plan_id)
        total = units * plan.price_per_unit

        Subscription.objects.create(
            user=request.user,
            house=request.user.myhouse,
            units_count=units,
            plan=plan,
            total_amount=total,
            is_paid=False
        )

        return redirect("subscription_success")

    return render(request, "middle_admin/middle_add_subscription.html", {
        "plans": plans,
        "unit_count": unit_count  # برای مقدار پیش‌فرض فرم
    })

# ==============================================================
def get_single_resident_building(user):
    units = Unit.objects.filter(
        Q(user=user) |
        Q(renters__user=user, renters__renter_is_active=True),
        is_active=True
    ).select_related('myhouse').distinct()

    buildings = set(
        unit.myhouse_id for unit in units if unit.myhouse_id
    )

    if len(buildings) == 1:
        return units.first()  # یک واحد از همان ساختمان
    return None


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def switch_to_resident(request):
    """
    سوییچ به محیط ساکن برای مدیر یا middleAdmin
    """
    user = request.user

    # فقط admin یا middleAdmin می‌توانند سوییچ کنند
    if not (user.is_staff or user.is_middle_admin):
        messages.error(request, 'دسترسی به پنل ساکن ندارید.')
        return redirect('middle_admin_dashboard')

    # فقط مدیرانی که ساکن هستند می‌توانند
    if not getattr(user, 'is_resident', False):
        messages.error(request, 'شما ساکن ساختمان نیستید.')
        return redirect('middle_admin_dashboard')

    unit = get_single_resident_building(user)
    if not unit:
        messages.error(request, 'شما یا ساکن واحد نیستید یا بیش از یک ساختمان دارید.')
        return redirect('middle_admin_dashboard')

    # ✅ تنظیم session
    request.session['active_context'] = 'resident'
    request.session['active_unit_id'] = unit.id
    request.session['active_building_id'] = unit.myhouse.id

    return redirect('user_panel')


# ================================================================
@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_admin_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')  # یا هر URL ورود شما

    managed_users = request.user.managed_users.all()
    resident_unit = get_single_resident_building(request.user)
    announcements = Announcement.objects.filter(is_active=True, user=request.user).order_by('-created_at')[:3]
    units = Unit.objects.filter(
        myhouse__user=request.user,
        is_active=True
    ).distinct()

    unit_count = units.count()
    tickets = SupportUser.objects.filter(Q(user=request.user) | Q(user__in=managed_users)).order_by('-created_at')[:5]

    funds = Fund.objects.select_related('bank', 'content_type').filter(
        Q(user=request.user) | Q(user__in=managed_users)
    ).order_by('-payment_date')

    totals = funds.aggregate(total_income=Sum('debtor_amount'), total_expense=Sum('creditor_amount'))
    balance = (totals['total_income'] or 0) - (totals['total_expense'] or 0)

    unit_count_unpaid_charges = UnifiedCharge.objects.filter(
        house__user=request.user,
        send_notification=True,
        is_paid=False,
        unit__isnull=False
    ).count()

    # نمودار مالک/مستاجر
    renter_units = units.filter(renters__renter_is_active=True).distinct()
    owner_units = units.exclude(id__in=renter_units.values_list('id', flat=True))

    owner_renter_stats = {
        'owner': owner_units.count(),
        'renter': renter_units.count(),
    }

    # نمودار خانه خالی/پر
    residence_stats = {
        'occupied': units.filter(status_residence='occupied').count(),
        'empty': units.filter(status_residence='empty').count(),
    }

    # ماه‌های شمسی
    persian_months = [
        "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
        "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
    ]

    def get_persian_month(g_date):
        if g_date:
            return jdatetime.date.fromgregorian(date=g_date).month
        return None

    # شارژهای پرداخت‌شده
    paid_charges_qs = UnifiedCharge.objects.filter(
        house__user=request.user,
        send_notification=True,
        unit__in=units,
        is_paid=True
    )
    print(f'paid-{paid_charges_qs.count()}')
    paid_counts = {i: 0 for i in range(1, 13)}
    for charge in paid_charges_qs:
        month = get_persian_month(charge.payment_date)
        if month:
            paid_counts[month] += 1

    # شارژهای پرداخت‌نشده
    unpaid_charges_qs = UnifiedCharge.objects.filter(
        house__user=request.user,
        send_notification=True,
        unit__in=units,
        is_paid=False
    )
    print(unpaid_charges_qs.count())
    unpaid_counts = {i: 0 for i in range(1, 13)}
    for charge in unpaid_charges_qs:
        month = get_persian_month(charge.send_notification_date)
        if month:
            unpaid_counts[month] += 1

    months = list(range(1, 13))
    paid_data = [paid_counts[m] for m in months]
    unpaid_data = [unpaid_counts[m] for m in months]

    has_charge_data = any(paid_data) or any(unpaid_data)

    context = {
        'announcements': announcements,
        'unit_count': unit_count,
        'fund_amount': balance,
        'tickets': tickets,
        'unit_count_unpaid_charges': unit_count_unpaid_charges,
        'resident_unit': resident_unit,
        'owner_renter_stats': owner_renter_stats,
        'residence_stats': residence_stats,
        'months': months,
        'paid_data': paid_data,
        'unpaid_data': unpaid_data,
        'has_charge_date': has_charge_data,
        # 'current_subscription': current_subscription,  # << اضافه شد
    }

    return render(request, 'middleShared/home_template.html', context)


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def middle_admin_login_view(request):
    if request.method == 'POST':
        mobile = request.POST.get('mobile')
        password = request.POST.get('password1')

        user = authenticate(request, mobile=mobile, password=password)
        if user is not None:
            if user.is_middle_admin:
                login(request, user)
                sweetify.success(request, f"{user.full_name} عزیز، با موفقیت وارد بخش مدیر ساختمان شدید!")
                return redirect(reverse('middle_manage_house'))
            else:
                logout(request)  # Log out any non-superuser who authenticated successfully
                messages.error(request, 'شما مجوز دسترسی به بخش مدیر ساختمان را ندارید!')
                return redirect(reverse('login_middle_admin'))
        else:
            messages.error(request, 'نام کاربری و یا رمز عبور اشتباه است!')
            return redirect(reverse('login_middle_admin'))

    return render(request, 'middleShared/middle_login.html')


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def logout__middle_admin(request):
    logout(request)
    return redirect('index')


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def site_header_component(request):
    context = {
        'user': request.user,
    }
    return render(request, 'middleShared/notification_template.html', context)


# =====================================Middle Profile ============================
@login_required(login_url=settings.LOGIN_URL_ADMIN)
def middle_profile(request):
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
    # unit = Unit.objects.filter(user=user).first()

    context = {
        'user_obj': user,
        # 'unit': unit,
        'password_form': password_form,
    }
    return render(request, 'middle_admin/middle_my_profile.html', context)


# ========================== My House Views ========================
@method_decorator(middle_admin_required, name='dispatch')
class MiddleAddMyHouseView(CreateView):
    model = MyHouse
    template_name = 'middle_admin/middle_add_my_house.html'
    form_class = MyHouseForm
    success_url = reverse_lazy('middle_admin_dashboard')

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        self.object.save()
        self.object.residents.add(self.request.user)

        messages.success(self.request, 'اطلاعات ساختمان با موفقیت ثبت گردید!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['houses'] = MyHouse.objects.filter(user=self.request.user)
        return context


@method_decorator(middle_admin_required, name='dispatch')
class MiddleMyHouseUpdateView(UpdateView):
    model = MyHouse
    form_class = MyHouseForm
    success_url = reverse_lazy('middle_manage_house')
    template_name = 'middle_admin/middle_add_my_house.html'

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        messages.success(self.request, 'اطلاعات ساختمان با موفقیت ویرایش گردید!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['houses'] = MyHouse.objects.filter(user=self.request.user)
        return context


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def middle_house_delete(request, pk):
    house = get_object_or_404(MyHouse, id=pk)
    try:
        house.delete()
        messages.success(request, 'ساختمان با موفقیت حذف گردید!')
        return redirect(reverse('middle_manage_house'))
    except Bank.DoesNotExist:
        messages.info(request, 'خطا در حذف')
        return redirect(reverse('middle_manage_house'))


# ============================= Announcement ====================
@method_decorator(middle_admin_required, name='dispatch')
class MiddleAnnouncementView(CreateView):
    model = Announcement
    template_name = 'middle_admin/middle_send_announcement.html'
    form_class = announcementForm
    success_url = reverse_lazy('middle_announcement')

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        self.object.house = MyHouse.objects.filter(user=self.request.user).first()  # یا .houses.first()

        self.object.save()

        messages.success(self.request, 'اطلاعیه با موفقیت ثبت گردید!')
        return super(MiddleAnnouncementView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['announcements'] = Announcement.objects.filter(user=self.request.user).order_by('-created_at')
        return context


@method_decorator(middle_admin_required, name='dispatch')
class MiddleAnnouncementListView(ListView):
    model = Announcement
    template_name = 'middle_admin/middle_announcement.html'
    context_object_name = 'announcements'

    def get_paginate_by(self, queryset):
        paginate = self.request.GET.get('paginate')
        if paginate == '1000':
            return None  # نمایش همه آیتم‌ها
        return int(paginate or 20)

    def get_queryset(self):
        query = self.request.GET.get('q', '')

        queryset = Announcement.objects.filter(
            user=self.request.user,
            is_active=True
        )

        if query:
            queryset = queryset.filter(title__icontains=query)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['paginate'] = self.request.GET.get('paginate', '20')
        return context


@method_decorator(middle_admin_required, name='dispatch')
class MiddleAnnouncementUpdateView(UpdateView):
    model = Announcement
    template_name = 'middle_admin/middle_send_announcement.html'
    form_class = announcementForm
    success_url = reverse_lazy('middle_announcement')

    def form_valid(self, form):
        edit_instance = form.instance
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        self.object.house = MyHouse.objects.filter(user=self.request.user).first()  # یا .houses.first()

        self.object.save()
        messages.success(self.request, 'اطلاعیه با موفقیت ویرایش گردید!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['announcements'] = Announcement.objects.filter(user=self.request.user).order_by('-created_at')
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_announcement_delete(request, pk):
    announce = get_object_or_404(Announcement, id=pk)
    print(announce.id)

    try:
        announce.delete()
        messages.success(request, 'اظلاعیه با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('middle_announcement'))


# ========================== Bank Views ========================
@method_decorator(middle_admin_required, name='dispatch')
class middleAddBankView(CreateView):
    model = Bank
    template_name = 'middle_admin/middle_add_my_bank.html'
    form_class = BankForm
    success_url = reverse_lazy('middle_manage_bank')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)

        bank = self.object
        house = bank.house  # اینجا هم اصلاح شد

        # اگر موجودی اولیه دارد → Fund افتتاحیه
        if bank.initial_fund and bank.initial_fund > 0:
            content_type = ContentType.objects.get_for_model(Bank)

            if not Fund.objects.filter(
                    content_type=content_type,
                    object_id=bank.id,
                    payment_description__icontains='افتتاحیه'
            ).exists():
                Fund.objects.create(
                    user=self.request.user,
                    bank=bank,
                    house=house,
                    payer_name=bank.account_holder_name,
                    receiver_name='صندوق',
                    payment_gateway='پرداخت الکترونیک',
                    content_type=content_type,
                    object_id=bank.id,
                    is_initial=True,
                    is_paid=True,
                    amount=bank.initial_fund,
                    debtor_amount=bank.initial_fund,
                    creditor_amount=Decimal(0),
                    payment_date=bank.create_at.date(),
                    payment_description=f'افتتاحیه حساب بانک {bank.bank_name}'
                )

        messages.success(self.request, 'حساب بانکی با موفقیت ثبت گردید!')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['banks'] = Bank.objects.filter(user=self.request.user)
        return context


@method_decorator(middle_admin_required, name='dispatch')
class middleBankUpdateView(UpdateView):
    model = Bank
    template_name = 'middle_admin/middle_add_my_bank.html'
    form_class = BankForm
    success_url = reverse_lazy('middle_manage_bank')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        bank = self.get_object()
        old_initial_fund = bank.initial_fund  # مقدار قبلی

        # ست کردن کاربر قبل از ذخیره فرم
        form.instance.user = self.request.user

        # ذخیره Bank (شامل house و بقیه فیلدها)
        response = super().form_valid(form)

        # بارگذاری دوباره بانک بعد از ذخیره
        bank.refresh_from_db()
        new_initial_fund = bank.initial_fund
        house = bank.house  # حتما house را از بانک بگیری

        # بررسی تغییر مقدار اولیه
        if old_initial_fund == new_initial_fund:
            messages.success(self.request, 'اطلاعات حساب بانکی بروزرسانی شد.')
            return response

        content_type = ContentType.objects.get_for_model(Bank)
        initial_fund_obj = Fund.objects.filter(
            content_type=content_type,
            object_id=bank.id,
            is_initial=True
        ).first()

        # اگر موجودی جدید مثبت است → ایجاد یا بروزرسانی Fund
        if new_initial_fund and new_initial_fund > 0:
            if initial_fund_obj:
                # بروزرسانی
                initial_fund_obj.amount = Decimal(new_initial_fund)
                initial_fund_obj.debtor_amount = Decimal(new_initial_fund)
                initial_fund_obj.creditor_amount = Decimal(0)
                initial_fund_obj.payment_description = f'افتتاحیه حساب بانک {bank.bank_name}'
                initial_fund_obj.house = house  # ✅ مهم
                initial_fund_obj.save()
                Fund.recalc_final_amounts_from(initial_fund_obj)
            else:
                # ایجاد Fund جدید
                fund = Fund.objects.create(
                    user=self.request.user,
                    bank=bank,
                    house=house,  # ✅ مهم
                    payer_name=bank.account_holder_name,
                    receiver_name='صندوق',
                    payment_gateway='پرداخت الکترونیک',
                    content_type=content_type,
                    object_id=bank.id,
                    is_initial=True,
                    is_paid=True,
                    amount=Decimal(new_initial_fund),
                    debtor_amount=Decimal(new_initial_fund),
                    creditor_amount=Decimal(0),
                    payment_date=bank.created_at.date(),
                    payment_description=f'افتتاحیه حساب بانک {bank.bank_name}'
                )
                Fund.recalc_final_amounts_from(fund)

        # اگر موجودی صفر یا حذف شد → حذف Fund افتتاحیه
        else:
            if initial_fund_obj:
                next_fund = Fund.objects.filter(
                    bank=bank,
                    id__gt=initial_fund_obj.id
                ).order_by('id').first()

                initial_fund_obj.delete()

                if next_fund:
                    Fund.recalc_final_amounts_from(next_fund)

        messages.success(self.request, 'اطلاعات حساب بانکی با موفقیت بروزرسانی شد!')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['banks'] = Bank.objects.filter(user=self.request.user)
        return context


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def middle_bank_delete(request, pk):
    bank = get_object_or_404(Bank, id=pk)
    try:
        has_fund = Fund.objects.filter(bank=bank).exists()

        if has_fund:
            messages.error(
                request,
                'به دلیل وجود گردش مالی، امکان حذف این حساب بانکی وجود ندارد.'
            )
            return redirect('middle_manage_bank')
        bank.delete()
        messages.success(request, 'حساب بانکی با موفقیت حذف گردید!')
        return redirect(reverse('middle_manage_bank'))
    except Bank.DoesNotExist:
        messages.info(request, 'خطا در حذف')
        return redirect(reverse('middle_manage_bank'))


# =========================== unit Views ================================

@method_decorator(middle_admin_required, name='dispatch')
class MiddleUnitRegisterView(CreateView):
    model = Unit
    form_class = UnitForm
    template_name = 'middle_unit_templates/unit_register.html'
    success_url = reverse_lazy('middle_manage_unit')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # ---------- محدودیت بر اساس Subscription ----------
                subscription = Subscription.objects.filter(
                    house__user=self.request.user,
                    is_paid=True
                ).order_by('-created_at').first()

                if not subscription:
                    form.add_error(None, "هیچ اشتراک فعالی برای شما وجود ندارد. ابتدا اشتراک خریداری کنید.")
                    return self.form_invalid(form)

                current_units_count = Unit.objects.filter(myhouse__user=self.request.user).count()
                if current_units_count >= subscription.units_count:
                    messages.warning(self.request, f"شما مجاز به ثبت بیش از {subscription.units_count} واحد نیستید.")
                    # form.add_error(None, f"شما مجاز به ثبت بیش از {subscription.units_count} واحد نیستید.")
                    # return self.form_invalid(form)
                    return redirect('middle_unit_register')

                is_renter = str(form.cleaned_data.get('is_renter')).lower() == 'true'

                # -----------------------
                # 1️⃣ ساخت User مالک
                # -----------------------
                owner_mobile = form.cleaned_data.get('owner_mobile')
                owner_name = form.cleaned_data.get('owner_name')

                owner_user, owner_created = User.objects.get_or_create(
                    mobile=owner_mobile,
                    defaults={
                        'username': owner_mobile,
                        'full_name': owner_name,
                        'is_active': True,
                        'manager': self.request.user,
                        'is_unit': True,
                    }
                )

                # اگر قبلاً وجود داشته → نقش‌ها آپدیت شود
                if not owner_created:
                    owner_user.is_unit = True
                    owner_user.manager = self.request.user
                    owner_user.full_name = owner_name
                    owner_user.save()

                # اگر تازه ساخته شده → پسورد ست شود
                if owner_created:
                    password = form.cleaned_data.get('password')
                    if password:
                        owner_user.set_password(password)
                        owner_user.save()

                # -----------------------
                # 2️⃣ ساخت Unit با مالک
                # -----------------------
                unit = form.save(commit=False)
                unit.user = owner_user
                unit.myhouse = MyHouse.objects.filter(
                    user=self.request.user,
                    is_active=True
                ).first()

                unit.save()

                # -----------------------
                # 3️⃣ اگر مستاجر دارد
                # -----------------------
                if is_renter:

                    renter_mobile = form.cleaned_data.get('renter_mobile')
                    renter_name = form.cleaned_data.get('renter_name')

                    renter_user, renter_created = User.objects.get_or_create(
                        mobile=renter_mobile,
                        defaults={
                            'username': renter_mobile,
                            'full_name': renter_name,
                            'is_active': True,
                            'manager': self.request.user,
                            'is_unit': True,
                        }
                    )

                    # 👇 غیرفعال کردن مالک
                    owner_user.is_active = False
                    owner_user.save(update_fields=['is_active'])

                    # ساخت مستاجر
                    Renter.objects.create(
                        unit=unit,
                        user=renter_user,
                        myhouse=unit.myhouse,
                        renter_name=renter_name,
                        renter_mobile=renter_mobile,
                        renter_national_code=form.cleaned_data.get('renter_national_code'),
                        renter_people_count=form.cleaned_data.get('renter_people_count'),
                        contract_number=form.cleaned_data.get('contract_number'),
                        estate_name=form.cleaned_data.get('estate_name'),
                        renter_is_active=True,
                        start_date=form.cleaned_data.get('start_date'),
                        end_date=form.cleaned_data.get('end_date'),
                        first_charge_renter=form.cleaned_data.get('first_charge_renter'),
                        renter_payment_date=form.cleaned_data.get('renter_payment_date'),
                        renter_transaction_no=form.cleaned_data.get('renter_transaction_no'),
                        renter_bank=form.cleaned_data.get('renter_bank'),
                    )

                    unit.people_count = form.cleaned_data.get('renter_people_count') or 0

                else:
                    unit.people_count = form.cleaned_data.get('owner_people_count') or 0

                unit.save(update_fields=['people_count'])

                owner_bank = form.cleaned_data.get('owner_bank') or Bank.objects.first()
                first_charge_owner = int(form.cleaned_data.get('first_charge_owner') or 0)
                if first_charge_owner > 0:
                    Fund.objects.create(
                        user=owner_user,
                        unit=unit,
                        bank=owner_bank,
                        house=unit.myhouse,
                        debtor_amount=Decimal(first_charge_owner),
                        creditor_amount=0,
                        amount=Decimal(first_charge_owner),
                        is_initial=True,
                        payment_date=form.cleaned_data.get('owner_payment_date'),
                        payer_name=unit.get_label(),
                        payment_description="شارژ اولیه مالک",
                        payment_gateway='پرداخت الکترونیک',
                        content_object=unit,
                        transaction_no=form.cleaned_data.get('owner_transaction_no'),
                    )

                # -------------------------
                # ایجاد شارژ اولیه مستاجر
                # -------------------------
                renter_bank = form.cleaned_data.get('renter_bank') or Bank.objects.first()
                first_charge_renter = int(form.cleaned_data.get('first_charge_renter') or 0)
                if first_charge_renter > 0:
                    Fund.objects.create(
                        user=renter_user,
                        unit=unit,
                        bank=renter_bank,
                        house=unit.myhouse,
                        debtor_amount=Decimal(first_charge_renter),
                        creditor_amount=0,
                        amount=Decimal(first_charge_renter),
                        is_initial=True,
                        payment_date=form.cleaned_data.get('renter_payment_date'),
                        payer_name=unit.get_label(),
                        payment_description="شارژ اولیه مستاجر",
                        payment_gateway='پرداخت الکترونیک',
                        content_object=unit,
                        transaction_no=form.cleaned_data.get('renter_transaction_no'),
                    )

                messages.success(self.request, 'واحد با موفقیت ثبت شد.')
                return super().form_valid(form)

        except Exception as e:
            form.add_error(None, f'خطا در ثبت اطلاعات: {e}')
            return self.form_invalid(form)


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def add_renter_to_unit(request, unit_id):
    unit = get_object_or_404(Unit, id=unit_id)

    if request.method == 'POST':
        form = RenterAddForm(request.POST, user=request.user)
        if form.is_valid():
            renter_mobile = form.cleaned_data['renter_mobile']

            # ❌ جلوگیری از مستاجر فعال در واحد دیگر
            if Renter.objects.filter(
                    user__mobile=renter_mobile,
                    renter_is_active=True
            ).exclude(unit=unit).exists():
                form.add_error(
                    'renter_mobile',
                    'این شماره موبایل در واحد دیگری به عنوان مستاجر فعال ثبت شده است.'
                )
                return render(
                    request,
                    'middle_unit_templates/new_renter_register.html',
                    {'form': form, 'unit': unit}
                )

            with transaction.atomic():
                # -------------------------
                # غیرفعال کردن مستاجر قبلی
                # -------------------------
                unit.renters.filter(renter_is_active=True).update(renter_is_active=False)

                # -------------------------
                # گرفتن یا ساخت یوزر مستاجر
                # -------------------------
                renter_user, created = User.objects.get_or_create(
                    mobile=renter_mobile,
                    defaults={
                        'username': renter_mobile,
                        'full_name': form.cleaned_data['renter_name'],
                        'is_active': True,
                        'manager': request.user,
                        'is_unit': True,  # ← اضافه شد
                    }
                )

                # بروزرسانی اطلاعات یوزر
                renter_user.full_name = form.cleaned_data['renter_name']
                renter_user.is_active = True
                password = form.cleaned_data.get('password')
                if password:
                    renter_user.set_password(password)
                renter_user.save()

                # -------------------------
                # انتخاب بانک
                # -------------------------
                renter_bank = form.cleaned_data.get('renter_bank') or Bank.objects.first()

                # -------------------------
                # ایجاد مستاجر جدید
                # -------------------------
                Renter.objects.create(
                    unit=unit,
                    user=renter_user,
                    renter_bank=renter_bank,
                    myhouse=unit.myhouse,
                    renter_name=form.cleaned_data['renter_name'],
                    renter_mobile=renter_mobile,
                    renter_national_code=form.cleaned_data['renter_national_code'],
                    renter_people_count=form.cleaned_data['renter_people_count'],
                    start_date=form.cleaned_data['start_date'],
                    end_date=form.cleaned_data['end_date'],
                    contract_number=form.cleaned_data['contract_number'],
                    estate_name=form.cleaned_data['estate_name'],
                    first_charge_renter=form.cleaned_data.get('first_charge_renter') or 0,
                    renter_details=form.cleaned_data.get('renter_details'),
                    renter_is_active=True,
                    renter_payment_date=form.cleaned_data.get('renter_payment_date'),
                    renter_transaction_no=form.cleaned_data.get('renter_transaction_no'),
                )
                owner_user = unit.user
                owner_user.is_active = False
                owner_user.save(update_fields=['is_active'])

                # -------------------------
                # بروزرسانی واحد
                # -------------------------
                unit.is_renter = True

                # -------------------------
                # بروزرسانی people_count
                # -------------------------
                active_renter = unit.get_active_renter()
                if active_renter:
                    unit.people_count = int(active_renter.renter_people_count or 0)
                else:
                    unit.people_count = int(unit.owner_people_count or 0)
                unit.save(update_fields=['is_renter', 'people_count'])

                # -------------------------
                # ایجاد شارژ اولیه مستاجر
                # -------------------------
                first_charge_renter = int(form.cleaned_data.get('first_charge_renter') or 0)
                if first_charge_renter > 0:
                    Fund.objects.create(
                        user=renter_user,
                        unit=unit,
                        house=unit.myhouse,
                        bank=renter_bank,
                        debtor_amount=Decimal(first_charge_renter),
                        creditor_amount=0,
                        amount=Decimal(first_charge_renter),
                        is_initial=True,
                        payment_date=form.cleaned_data.get('renter_payment_date'),
                        payer_name=unit.get_label(),
                        payment_description="شارژ اولیه مستاجر",
                        payment_gateway='پرداخت الکترونیک',
                        content_object=unit,
                        transaction_no=form.cleaned_data.get('renter_transaction_no'),
                    )

                messages.success(request, 'مستاجر با موفقیت ثبت شد.')
                return redirect('middle_manage_unit')

    else:
        form = RenterAddForm(user=request.user)

    return render(
        request,
        'middle_unit_templates/new_renter_register.html',
        {'form': form, 'unit': unit}
    )


@method_decorator(middle_admin_required, name='dispatch')
class MiddleUnitUpdateView(UpdateView):
    model = Unit
    form_class = UnitForm
    template_name = 'middle_unit_templates/edit_unit.html'
    success_url = reverse_lazy('middle_manage_unit')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            UnitUpdateService(
                unit=self.object,
                form=form,
                request=self.request
            ).execute()

            messages.success(self.request, 'اطلاعات واحد با موفقیت ویرایش شد')
            return super().form_valid(form)

        except ValueError as e:
            # نمایش پیام واقعی
            if str(e) == 'duplicate_mobile':
                messages.error(self.request, 'شماره موبایل وارد شده قبلاً ثبت شده است.')
            else:
                messages.error(self.request, f'خطا در ثبت! ({e})')

            return self.form_invalid(form)


@method_decorator(middle_admin_required, name='dispatch')
class MiddleUnitInfoView(DetailView):
    model = Unit
    template_name = 'middle_unit_templates/unit_info.html'
    context_object_name = 'unit'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        unit = self.object

        # --- جستجو ---
        q = self.request.GET.get('q', '').strip()
        page_number = self.request.GET.get('page')

        renters_qs = unit.renters.all()

        if q:
            renters_qs = renters_qs.filter(
                Q(renter_name__icontains=q) |
                Q(renter_mobile__icontains=q) |
                Q(renter_national_code__icontains=q) |
                Q(contract_number__icontains=q)
            )

        renters_qs = renters_qs.order_by(
            '-renter_is_active',
            '-start_date'
        )

        # --- صفحه‌بندی ---
        paginator = Paginator(renters_qs, 20)
        page_obj = paginator.get_page(page_number)

        context['renters'] = page_obj.object_list
        context['page_obj'] = page_obj
        context['q'] = q

        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_unit_delete(request, pk):
    unit = get_object_or_404(Unit, id=pk)

    # اگر رکورد مرتبط در Fund یا UnifiedCharge وجود داشته باشد، حذف امکان‌پذیر نیست
    if unit.funds.exists():
        messages.error(
            request,
            "امکان حذف وجود ندارد! برای این واحد در گردش صندوق رکورد ثبت شده است."
        )
        return redirect(reverse('middle_manage_unit'))

    try:
        # فقط زمانی مستاجر حذف می‌شود که Unit قابل حذف باشد
        unit.renters.all().delete()

        # حذف کاربر فقط اگر هیچ واحد دیگری نداشته باشد
        if unit.user and not Unit.objects.filter(user=unit.user).exclude(pk=unit.pk).exists():
            unit.user.delete()

        # حذف خود واحد
        unit.delete()
        messages.success(
            request,
            "واحد با موفقیت حذف گردید! مستاجرها و سوابق سکونت به درستی مدیریت شدند."
        )

    except ProtectedError:
        messages.error(request, "امکان حذف وجود ندارد!")

    return redirect(reverse('middle_manage_unit'))


@method_decorator(middle_admin_required, name='dispatch')
class MiddleUnitListView(ListView):
    model = Unit
    template_name = 'middle_unit_templates/unit_management.html'

    def get_paginate_by(self, queryset):
        paginate = self.request.GET.get('paginate')
        if paginate == '1000':
            return None
        return int(paginate) if paginate and paginate.isdigit() else 20

    def get_queryset(self):
        user = self.request.user

        queryset = (
            Unit.objects
            .filter(myhouse__user=user)
            .prefetch_related('renters')
        )

        filters = Q()
        params = self.request.GET

        if params.get('unit', '').isdigit():
            filters &= Q(unit=int(params['unit']))

        if params.get('owner_name'):
            filters &= Q(owner_name__icontains=params['owner_name'])

        if params.get('owner_mobile'):
            filters &= Q(owner_mobile__icontains=params['owner_mobile'])

        if params.get('area', '').isdigit():
            filters &= Q(area=int(params['area']))

        if params.get('bedrooms_count', '').isdigit():
            filters &= Q(bedrooms_count=int(params['bedrooms_count']))

        if params.get('renter_name'):
            filters &= Q(renters__renter_name__icontains=params['renter_name'])

        if params.get('renter_mobile'):
            filters &= Q(renters__renter_mobile__icontains=params['renter_mobile'])

        if params.get('people_count', '').isdigit():
            filters &= Q(owner_people_count=int(params['people_count']))

        if params.get('status_residence'):
            filters &= Q(status_residence=params['status_residence'])

        qs = queryset.filter(filters).distinct().order_by('unit')

        for unit in qs:
            unit.active_renters = unit.renters.filter(renter_is_active=True)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            'total_units': Unit.objects.filter(
                myhouse__user=self.request.user
            ).count(),
            'units': context['object_list'],
            'paginate': self.request.GET.get('paginate', '20'),
        })

        return context


def to_jalali(date_obj):
    if not date_obj:
        return ''
    jalali_date = jdatetime.date.fromgregorian(date=date_obj)
    return jalali_date.strftime('%Y/%m/%d')


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def export_units_excel(request):
    units = Unit.objects.filter(user__manager=request.user).order_by('unit')

    filter_fields = {
        'unit': 'unit__icontains',
        'owner_name': 'owner_name__icontains',
        'owner_mobile': 'owner_mobile__icontains',
        'renter_name': 'renter_name__icontains',
        'renter_mobile': 'renter_mobile__icontains',
        'status_residence': 'status_residence__icontains',
        'area': 'area__icontains',
        'bedrooms_count': 'bedrooms_count__icontains',
        'people_count': 'people_count__icontains',
    }

    # Apply filters based on GET parameters
    for field, lookup in filter_fields.items():
        value = request.GET.get(field)
        if value:
            filter_expression = {lookup: value}
            units = units.filter(**filter_expression)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "units"
    ws.sheet_view.rightToLeft = True

    # ✅ Add title
    title_cell = ws.cell(row=1, column=1, value="لیست واحدها")
    title_cell.font = Font(bold=True, size=18)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=22)

    # ✅ Style setup
    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")  # Gold
    header_font = Font(bold=True, color="000000")  # Black bold text

    headers = [
        'واحد', 'طبقه', 'متراژ', 'تعداد خواب', 'شماره تلفن',
        'تعداد پارکینگ', 'شماره پارکینگ', 'موقعیت پارکینک', 'وضعیت سکونت',
        'نام مالک', 'تلفن مالک', 'کد ملی مالک', 'تاریخ خرید', 'تعداد نفرات',
        'نام مستاجر', 'تلفن مستاجر', 'کد ملی مستاجر',
        'تاریخ اجاره', 'تاریخ پایان', 'شماره قرارداد', 'اجاره دهنده', 'شارژ اولیه',
    ]

    # ✅ Write header (row 2)
    for col_num, column_title in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_num, value=column_title)
        cell.fill = header_fill
        cell.font = header_font

    # ✅ Write data (start from row 3)
    for row_num, unit in enumerate(units, start=3):
        ws.cell(row=row_num, column=1, value=unit.unit)
        ws.cell(row=row_num, column=2, value=unit.floor_number)
        ws.cell(row=row_num, column=3, value=unit.area)
        ws.cell(row=row_num, column=4, value=unit.bedrooms_count)
        ws.cell(row=row_num, column=5, value=unit.unit_phone)
        ws.cell(row=row_num, column=6, value=unit.parking_count)
        ws.cell(row=row_num, column=7, value=unit.parking_number)
        ws.cell(row=row_num, column=8, value=unit.parking_place)
        ws.cell(row=row_num, column=9, value=unit.status_residence)
        ws.cell(row=row_num, column=10, value=unit.owner_name)
        ws.cell(row=row_num, column=11, value=unit.owner_mobile)
        ws.cell(row=row_num, column=12, value=unit.owner_national_code)
        ws.cell(row=row_num, column=13, value=to_jalali(unit.purchase_date))
        ws.cell(row=row_num, column=14, value=unit.people_count)
        renter = unit.renters.first()  # or .last(), or use filtering for current renter
        if renter:
            ws.cell(row=row_num, column=15, value=renter.renter_name)
            ws.cell(row=row_num, column=16, value=renter.renter_mobile)
            ws.cell(row=row_num, column=17, value=renter.renter_national_code)
            ws.cell(row=row_num, column=18, value=to_jalali(renter.start_date))
            ws.cell(row=row_num, column=19, value=to_jalali(renter.end_date))
            ws.cell(row=row_num, column=20, value=renter.contract_number)
            ws.cell(row=row_num, column=21, value=renter.estate_name)
            ws.cell(row=row_num, column=22, value=renter.first_charge_renter)

    # ✅ Return file
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=units.xlsx'
    wb.save(response)
    return response


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def export_units_pdf(request):
    units = Unit.objects.filter(user__manager=request.user).order_by('unit')

    filter_fields = {
        'unit': 'unit__icontains',
        'owner_name': 'owner_name__icontains',
        'owner_mobile': 'owner_mobile__icontains',
        'renter_name': 'renter_name__icontains',
        'renter_mobile': 'renter_mobile__icontains',
        'status_residence': 'status_residence__icontains',
        'area': 'area__icontains',
        'bedrooms_count': 'bedrooms_count__icontains',
        'people_count': 'people_count__icontains',
    }

    # Apply filters based on GET parameters
    for field, lookup in filter_fields.items():
        value = request.GET.get(field)
        if value:
            filter_expression = {lookup: value}
            units = units.filter(**filter_expression)

    # PDF settings
    font_url = request.build_absolute_uri('/static/fonts/BYekan.ttf')
    css = CSS(string=f"""
        @page {{ size: A4 landscape; margin: 1cm; }}
        body {{
            font-family: 'BYekan', sans-serif;
        }}
        @font-face {{
            font-family: 'BYekan';
            src: url('{font_url}');
        }}
    """)

    # Render template
    template = get_template("unit_templates/unit_pdf.html")
    context = {
        'units': units,
        'font_path': font_url,
    }

    html = template.render(context)
    page_pdf = io.BytesIO()
    HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(page_pdf, stylesheets=[css])
    page_pdf.seek(0)

    # Create response
    pdf_merger = PdfWriter()
    pdf_merger.append(page_pdf)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="filtered_units.pdf"'
    pdf_merger.write(response)

    return response


# ================================= Expense Views ==============================
@method_decorator(middle_admin_required, name='dispatch')
class MiddleExpenseCategoryView(CreateView):
    model = ExpenseCategory
    template_name = 'middle_expense_templates/add_category_expense.html'
    form_class = ExpenseCategoryForm
    success_url = reverse_lazy('middle_add_category_expense')

    def form_valid(self, form):
        form.instance.user = self.request.user
        try:
            self.object = form.save()
            messages.success(self.request, 'موضوع هزینه با موفقیت ثبت گردید!')
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, 'خطا در ثبت !')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ExpenseCategory.objects.filter(user=self.request.user)
        return context


@method_decorator(middle_admin_required, name='dispatch')
class MiddleExpenseCategoryUpdate(UpdateView):
    model = ExpenseCategory
    template_name = 'middle_expense_templates/add_category_expense.html'
    form_class = ExpenseCategoryForm
    success_url = reverse_lazy('middle_add_category_expense')

    def form_valid(self, form):
        form.instance.user = self.request.user
        try:
            edit_instance = form.instance
            self.object = form.save()
            messages.success(self.request, f' موضوع هزینه با موفقیت ویرایش گردید!')
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, 'خطا در ثبت !')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ExpenseCategory.objects.filter(user=self.request.user)
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_expense_category_delete(request, pk):
    category = get_object_or_404(ExpenseCategory, id=pk)
    try:
        category.delete()
        messages.success(request, 'موضوع هزینه با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('middle_add_category_expense'))


@method_decorator(middle_admin_required, name='dispatch')
class MiddleExpenseView(CreateView):
    model = Expense
    template_name = 'middle_expense_templates/expense_register.html'
    form_class = ExpenseForm
    success_url = reverse_lazy('middle_add_expense')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        house = MyHouse.objects.filter(user=self.request.user, is_active=True).first()
        form.instance.house = house  # 🔹 این مهم است

        try:
            with transaction.atomic():
                self.object = form.save(commit=False)

                # هزینه هنوز پرداخت نشده
                self.object.is_paid = False
                self.object.save()

                # ذخیره فایل‌ها
                files = self.request.FILES.getlist('document')
                for f in files:
                    ExpenseDocument.objects.create(
                        expense=self.object,
                        document=f
                    )

            messages.success(
                self.request,
                'هزینه با موفقیت ثبت شد (در انتظار پرداخت)'
            )
            return redirect(self.success_url)

        except Exception:
            messages.error(self.request, 'خطا در ثبت هزینه')
            return self.form_invalid(form)

    def get_queryset(self):
        queryset = Expense.objects.filter(user=self.request.user).order_by('-created_at')

        # فیلتر بر اساس category__title
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category__id=category_id)

        bank_id = self.request.GET.get('bank')
        if bank_id:
            queryset = queryset.filter(bank__id=bank_id)

        # فیلتر بر اساس amount
        amount = self.request.GET.get('amount')
        if amount:
            queryset = queryset.filter(amount__icontains=amount)

        description = self.request.GET.get('description')
        if description:
            queryset = queryset.filter(description__icontains=description)

        doc_no = self.request.GET.get('doc_no')
        if doc_no:
            queryset = queryset.filter(doc_no__icontains=doc_no)

        details = self.request.GET.get('details')
        if details:
            queryset = queryset.filter(details__icontains=details)

        receiver_name = self.request.GET.get('receiver_name')
        if receiver_name:
            queryset = queryset.filter(receiver_name__icontains=receiver_name)

        # فیلتر بر اساس date
        from_date_str = self.request.GET.get('from_date')
        to_date_str = self.request.GET.get('to_date')

        try:
            if from_date_str:
                jalali_from = jdatetime.datetime.strptime(from_date_str, '%Y-%m-%d')
                gregorian_from = jalali_from.togregorian().date()
                queryset = queryset.filter(date__gte=gregorian_from)

            if to_date_str:
                jalali_to = jdatetime.datetime.strptime(to_date_str, '%Y-%m-%d')
                gregorian_to = jalali_to.togregorian().date()
                queryset = queryset.filter(date__lte=gregorian_to)
        except ValueError:
            messages.warning(self.request, 'فرمت تاریخ وارد شده صحیح نیست.')

        is_paid = self.request.GET.get('is_paid')
        if is_paid == '1':
            queryset = queryset.filter(is_paid=True)
        elif is_paid == '0':
            queryset = queryset.filter(is_paid=False)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        expenses = self.get_queryset()  # از get_queryset برای دریافت داده‌های فیلتر شده استفاده می‌کنیم
        paginator = Paginator(expenses, 50)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context['page_obj'] = page_obj
        context['total_expense'] = Expense.objects.filter(user=self.request.user).count()
        context['categories'] = ExpenseCategory.objects.filter(user=self.request.user)
        context['banks'] = Bank.objects.filter(user=self.request.user)
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def expense_pay_view(request, expense_id):
    expense = get_object_or_404(
        Expense,
        id=expense_id,
        is_paid=False,
        is_active=True
    )

    if request.method == 'POST':
        form = ExpensePayForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    bank = form.cleaned_data['bank']
                    reference = form.cleaned_data.get('transaction_reference')
                    payment_date = form.cleaned_data.get('payment_date')
                    receiver_name = form.cleaned_data.get('receiver_name')
                    unit = form.cleaned_data['unit']

                    # 🔹 موجودی فعلی صندوق بانک انتخاب شده

                    funds = Fund.objects.filter(user=request.user, bank=bank)
                    print(f"Funds count for bank {bank.id}: {funds.count()}")
                    for f in funds:
                        print(f"Fund: {f.id}, bank: {f.bank}, final: {f.final_amount}")

                    bank_funds = Fund.objects.filter(user=request.user, bank=bank)
                    total_debit = bank_funds.aggregate(Sum('debtor_amount'))['debtor_amount__sum'] or 0
                    total_credit = bank_funds.aggregate(Sum('creditor_amount'))['creditor_amount__sum'] or 0
                    current_final = Decimal(total_debit) - Decimal(total_credit)

                    print(f'bank-fund:{current_final}')

                    # 🔴 بررسی موجودی
                    if current_final < expense.amount:
                        messages.error(
                            request,
                            'موجودی صندوق کافی نیست'
                        )
                        return redirect(request.META.get('HTTP_REFERER'))

                    # 🔹 ثبت Fund (هزینه → بستانکار)
                    fund = Fund.objects.create(
                        unit=unit if unit else None,
                        receiver_name=receiver_name if not unit else f' {unit.get_label()}',
                        user=request.user,
                        bank=bank,
                        house=expense.house,
                        content_object=expense,
                        amount=expense.amount,
                        debtor_amount=0,
                        creditor_amount=expense.amount,
                        payment_date=payment_date,
                        transaction_no=reference,
                        payment_gateway='پرداخت الکترونیک',
                        payment_description=f' هزینه: پرداخت سند {expense.doc_no}',
                        is_paid=True,

                    )

                    # 🔹 بروزرسانی Expense
                    expense.is_paid = True
                    expense.bank = bank
                    expense.transaction_reference = reference
                    expense.payment_date = payment_date
                    expense.unit = unit
                    expense.receiver_name = unit.get_label() if unit else receiver_name

                    expense.save(update_fields=[
                        'is_paid',
                        'bank',
                        'transaction_reference',
                        'payment_date',
                        'unit',
                        'receiver_name'
                    ])

                messages.success(request, 'پرداخت با موفقیت انجام شد')
                return redirect('middle_add_expense')

            except ValidationError as e:
                messages.error(request, e.message)
            except Exception as e:
                messages.error(request, f'خطا در پرداخت: {e}')

    else:
        form = ExpensePayForm(user=request.user)

    return render(
        request,
        'middle_expense_templates/expense_pay.html',
        {
            'expense': expense,
            'form': form
        }
    )


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def expense_cancel_pay_view(request, expense_id):
    # Expense فقط اگر پرداخت شده باشد قابل لغو است
    expense = get_object_or_404(
        Expense,
        id=expense_id,
        is_paid=True,
        is_active=True
    )

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # پیدا کردن Fund مربوطه
                fund = Fund.objects.filter(
                    content_type__model='expense',
                    object_id=expense.id,
                    user=request.user,
                    is_paid=True
                ).first()

                if not fund:
                    messages.error(request, 'Fund مرتبط با این پرداخت پیدا نشد!')
                    return redirect(request.META.get('HTTP_REFERER'))

                # حذف Fund
                fund.delete()

                # بازمحاسبه موجودی صندوق از این Fund به بعد
                Fund.recalc_final_amounts_from(fund)

                # بازگرداندن Expense به حالت پرداخت‌نشده
                expense.is_paid = False
                expense.bank = None
                expense.transaction_reference = None
                expense.payment_date = None
                expense.save(update_fields=[
                    'is_paid',
                    'bank',
                    'transaction_reference',
                    'payment_date'
                ])

                messages.success(request, 'پرداخت با موفقیت لغو شد و صندوق اصلاح شد.')
                return redirect(request.META.get('HTTP_REFERER'))

        except Exception as e:
            messages.error(request, f'خطا در لغو پرداخت: {e}')
            return redirect(request.META.get('HTTP_REFERER'))

    # اگر GET باشد، فقط برگرد به صفحه قبل
    return redirect(request.META.get('HTTP_REFERER'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_expense_edit(request, pk):
    expense = get_object_or_404(Expense, pk=pk)

    # اگر پرداخت شده → ویرایش مجاز نیست
    if expense.is_paid:
        messages.warning(request, 'این هزینه پرداخت شده است و قابل ویرایش نیست.')
        return redirect('middle_add_expense')

    if request.method != 'POST':
        return redirect('middle_add_expense')

    form = ExpenseForm(request.POST, request.FILES, instance=expense, user=request.user)

    if not form.is_valid():
        messages.error(request, f'خطا در ویرایش فرم هزینه: {form.errors}')
        return redirect('middle_add_expense')

    try:
        new_amount = Decimal(form.cleaned_data['amount'] or 0)
    except Exception:
        messages.error(request, "مقدار مبلغ وارد شده معتبر نیست.")
        return redirect('middle_add_expense')

    with transaction.atomic():
        # 🔹 ست کردن خانه مرتبط با کاربر
        house = MyHouse.objects.filter(user=request.user, is_active=True).first()
        form.instance.house = house

        # ذخیره Expense
        expense = form.save()

        # ذخیره فایل‌های جدید بدون حذف قبلی
        for f in request.FILES.getlist('document'):
            ExpenseDocument.objects.create(expense=expense, document=f)

    messages.success(request, 'هزینه با موفقیت ویرایش شد.')
    return redirect('middle_add_expense')


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_expense_delete(request, pk):
    expense = get_object_or_404(Expense, id=pk)

    try:
        with transaction.atomic():
            # حذف Fund مربوطه
            expense_ct = ContentType.objects.get_for_model(Expense)
            Fund.objects.filter(content_type=expense_ct, object_id=expense.id).delete()

            # حذف خود Expense
            expense.delete()

        messages.success(request, 'هزینه با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, "امکان حذف وجود ندارد!")
    except Exception as e:
        messages.error(request, f"خطا در حذف: {str(e)}")

    return redirect(reverse('middle_add_expense'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
@csrf_exempt
def middle_delete_expense_document(request):
    if request.method == 'POST':
        image_url = request.POST.get('url')
        expense_id = request.POST.get('expense_id')

        if not image_url or not expense_id:
            return JsonResponse({'status': 'error', 'message': 'URL یا ID هزینه مشخص نیست'})

        try:
            expense = get_object_or_404(Expense, id=expense_id)

            relative_path = image_url.replace(settings.MEDIA_URL, '')  # دقیق کردن مسیر
            doc = ExpenseDocument.objects.filter(expense=expense, document=relative_path).first()

            if doc:
                # Delete the file from filesystem
                if doc.document:
                    file_path = os.path.join(settings.MEDIA_ROOT, doc.document.name)
                    if os.path.exists(file_path):
                        os.remove(file_path)

                doc.delete()
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'error', 'message': 'تصویر مرتبط پیدا نشد'})

        except Expense.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'هزینه یافت نشد'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'خطا در حذف تصویر: {str(e)}'})

    return JsonResponse({'status': 'error', 'message': 'درخواست معتبر نیست'})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_export_expense_pdf(request):
    expenses = Expense.objects.filter(user=request.user)
    house = None
    if request.user.is_authenticated:
        house = MyHouse.objects.filter(residents=request.user).order_by('-created_at').first()

    filter_fields = {
        'category': 'category__id',
        'bank': 'bank__id',
        'amount': 'amount__icontains',
        'doc_no': 'doc_no__icontains',
        'description': 'description__icontains',
        'details': 'details__icontains',
        'is_paid': 'is_paid',
    }

    # Apply filters based on GET parameters
    for field, lookup in filter_fields.items():
        value = request.GET.get(field)
        if value:
            filter_expression = {lookup: value}
            expenses = expenses.filter(**filter_expression)

    # Handle date filtering
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    try:
        if from_date_str:
            from_date = jdatetime.datetime.strptime(from_date_str, '%Y/%m/%d').togregorian().date()
            expenses = expenses.filter(date__gte=from_date)
        if to_date_str:
            to_date = jdatetime.datetime.strptime(to_date_str, '%Y/%m/%d').togregorian().date()
            expenses = expenses.filter(date__lte=to_date)
    except ValueError:
        expenses = Expense.objects.none()

    # Log the filtered expenses for debugging
    print(expenses)

    # Font setup
    font_url = request.build_absolute_uri('/static/fonts/BYekan.ttf')
    css = CSS(string=f"""
            @page {{ size: A4 landscape; margin: 1cm; }}
            body {{
                font-family: 'BYekan', sans-serif;
            }}
            @font-face {{
                font-family: 'BYekan';
                src: url('{font_url}');
            }}
        """)

    # Render HTML template
    template = get_template("middle_expense_templates/expense_pdf.html")
    context = {
        'expenses': expenses,
        'font_path': font_url,
        'house': house,
        'today': timezone.now()
    }
    html = template.render(context)

    # Generate PDF
    page_pdf = io.BytesIO()
    HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(page_pdf, stylesheets=[css])

    page_pdf.seek(0)

    # Generate the final PDF response
    pdf_merger = PdfWriter()
    pdf_merger.append(page_pdf)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="expenses.pdf"'
    pdf_merger.write(response)
    return response


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_export_expense_excel(request):
    expenses = Expense.objects.filter(user=request.user)

    # Filter fields
    filter_fields = {
        'category': 'category__id',
        'bank': 'bank__id',
        'amount': 'amount__icontains',
        'doc_no': 'doc_no__icontains',
        'description': 'description__icontains',
        'details': 'details__icontains',
        'is_paid': 'is_paid'
    }

    # Apply filters based on query parameters
    for field, lookup in filter_fields.items():
        value = request.GET.get(field)
        if value:
            filter_expression = {lookup: value}
            expenses = expenses.filter(**filter_expression)

    # Date range filtering
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    try:
        if from_date_str:
            from_date = jdatetime.datetime.strptime(from_date_str, '%Y/%m/%d').togregorian().date()
            expenses = expenses.filter(date__gte=from_date)
        if to_date_str:
            to_date = jdatetime.datetime.strptime(to_date_str, '%Y/%m/%d').togregorian().date()
            expenses = expenses.filter(date__lte=to_date)
    except ValueError:
        expenses = Expense.objects.none()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "expenses"
    ws.sheet_view.rightToLeft = True

    # ✅ Add title
    title_cell = ws.cell(row=1, column=1, value="لیست هزینه‌ها")
    title_cell.font = Font(bold=True, size=18)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=10)

    # ✅ Style setup
    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")  # Gold
    header_font = Font(bold=True, color="000000")  # Black bold text

    headers = ['#', 'موضوع هزینه', 'شرح سند', ' شماره سند', 'مبلغ', 'تاریخ سند', 'پرداخت به', 'شماره حساب',
               'تاریخ پرداخت', 'توضیحات']

    # ✅ Write header (row 2)
    for col_num, column_title in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_num, value=column_title)
        cell.fill = header_fill
        cell.font = header_font

    # ✅ Write data (start from row 3)
    for row_num, expense in enumerate(expenses, start=3):
        ws.cell(row=row_num, column=1, value=row_num - 2)  # index starts from 1
        ws.cell(row=row_num, column=2, value=expense.category.title)
        ws.cell(row=row_num, column=3, value=expense.description)
        ws.cell(row=row_num, column=4, value=expense.doc_no)
        ws.cell(row=row_num, column=5, value=expense.amount)
        ws.cell(row=row_num, column=6, value=show_jalali(expense.date))
        ws.cell(row=row_num, column=7, value=expense.receiver_name)
        ws.cell(row=row_num, column=8, value=expense.bank.bank_name)
        ws.cell(row=row_num, column=9, value=show_jalali(expense.payment_date))
        ws.cell(row=row_num, column=10, value=expense.details)

    # ✅ Return file
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=expenses.xlsx'
    wb.save(response)
    return response


# =========================== Income Views =========================
@method_decorator(middle_admin_required, name='dispatch')
class MiddleIncomeCategoryView(CreateView):
    model = IncomeCategory
    template_name = 'middle_income_templates/add_category_income.html'
    form_class = IncomeCategoryForm
    success_url = reverse_lazy('middle_add_category_income')

    def form_valid(self, form):
        form.instance.user = self.request.user
        try:
            self.object = form.save()

            messages.success(self.request, 'موضوع درآمد با موفقیت ثبت گردید!')
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, 'خطا در ثبت !')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['income_categories'] = IncomeCategory.objects.filter(user=self.request.user)
        return context


@method_decorator(middle_admin_required, name='dispatch')
class MiddleIncomeCategoryUpdate(UpdateView):
    model = IncomeCategory
    template_name = 'middle_income_templates/add_category_income.html'
    form_class = IncomeCategoryForm
    success_url = reverse_lazy('middle_add_category_income')

    def form_valid(self, form):
        form.instance.user = self.request.user
        try:
            edit_instance = form.instance
            self.object = form.save()
            messages.success(self.request, f' موضوع درآمد با موفقیت ویرایش گردید!')
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, 'خطا در ثبت !')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['income_categories'] = IncomeCategory.objects.filter(user=self.request.user)
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_income_category_delete(request, pk):
    income_category = get_object_or_404(IncomeCategory, id=pk)
    try:
        income_category.delete()
        messages.success(request, 'موضوع درآمد با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('middle_add_category_income'))


@method_decorator(middle_admin_required, name='dispatch')
class MiddleIncomeView(CreateView):
    model = Income
    template_name = 'middle_income_templates/income_register.html'
    form_class = IncomeForm
    success_url = reverse_lazy('middle_add_income')

    def form_valid(self, form):
        form.instance.user = self.request.user
        house = MyHouse.objects.filter(user=self.request.user, is_active=True).first()
        form.instance.house = house  # 🔹 این مهم است

        try:
            with transaction.atomic():
                self.object = form.save(commit=False)

                # هزینه هنوز پرداخت نشده
                self.object.is_paid = False
                self.object.save()

                # ذخیره فایل‌ها
                files = self.request.FILES.getlist('document')
                for f in files:
                    IncomeDocument.objects.create(
                        income=self.object,
                        document=f
                    )

            messages.success(
                self.request,
                'درآمد با موفقیت ثبت شد (در انتظار دریافت)'
            )
            return redirect(self.success_url)

        except Exception:
            messages.error(self.request, 'خطا در ثبت درآمد')
            return self.form_invalid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        queryset = Income.objects.filter(user=self.request.user).order_by('-created_at')

        # فیلتر بر اساس category
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category__id=category_id)

        # فیلتر بر اساس بانک
        bank_id = self.request.GET.get('bank')
        if bank_id:
            queryset = queryset.filter(bank__id=bank_id)

        # فیلتر بر اساس واحد
        unit_id = self.request.GET.get('unit')
        if unit_id:
            queryset = queryset.filter(unit__id=unit_id)

        # فیلتر بر اساس amount
        amount = self.request.GET.get('amount')
        if amount:
            queryset = queryset.filter(amount__icontains=amount)

        # فیلتر بر اساس description
        description = self.request.GET.get('description')
        if description:
            queryset = queryset.filter(description__icontains=description)

        # فیلتر بر اساس doc_number
        doc_number = self.request.GET.get('doc_number')
        if doc_number:
            queryset = queryset.filter(doc_number__icontains=doc_number)

        # فیلتر بر اساس details
        details = self.request.GET.get('details')
        if details:
            queryset = queryset.filter(details__icontains=details)

        payer_name = self.request.GET.get('payer_name')
        if payer_name:
            queryset = queryset.filter(payer_name__icontains=payer_name)

        # فیلتر بر اساس تاریخ
        from_date_str = self.request.GET.get('from_date')
        to_date_str = self.request.GET.get('to_date')
        try:
            if from_date_str:
                jalali_from = jdatetime.datetime.strptime(from_date_str, '%Y-%m-%d')
                gregorian_from = jalali_from.togregorian().date()
                queryset = queryset.filter(doc_date__gte=gregorian_from)

            if to_date_str:
                jalali_to = jdatetime.datetime.strptime(to_date_str, '%Y-%m-%d')
                gregorian_to = jalali_to.togregorian().date()
                queryset = queryset.filter(doc_date__lte=gregorian_to)
        except ValueError:
            messages.warning(self.request, 'فرمت تاریخ وارد شده صحیح نیست.')

        is_paid = self.request.GET.get('is_paid')
        if is_paid == '1':
            queryset = queryset.filter(is_paid=True)
        elif is_paid == '0':
            queryset = queryset.filter(is_paid=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        incomes = self.get_queryset()  # از get_queryset برای دریافت داده‌های فیلتر شده استفاده می‌کنیم
        paginator = Paginator(incomes, 50)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context['page_obj'] = page_obj
        context['total_incomes'] = Income.objects.filter(user=self.request.user).count()
        context['categories'] = IncomeCategory.objects.filter(user=self.request.user)
        context['banks'] = Bank.objects.filter(user=self.request.user)
        managed_users = User.objects.filter(Q(manager=self.request.user) | Q(pk=self.request.user.pk))
        context['units'] = Unit.objects.filter(is_active=True, user__in=managed_users)

        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def income_pay_view(request, income_id):
    income = get_object_or_404(
        Income,
        id=income_id,
        is_paid=False,
        is_active=True
    )

    if request.method == 'POST':
        form = IncomePayForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    bank = form.cleaned_data['bank']
                    reference = form.cleaned_data.get('transaction_reference')
                    payment_date = form.cleaned_data.get('payment_date')
                    payer_name = form.cleaned_data.get('payer_name')
                    unit = form.cleaned_data['unit']

                    fund = Fund.objects.create(
                        unit=unit if unit else None,
                        payer_name=payer_name if not unit else f' {unit.get_label()}',
                        user=request.user,
                        bank=bank,
                        house=income.house,
                        content_object=income,
                        amount=income.amount,
                        debtor_amount=income.amount,
                        creditor_amount=0,
                        payment_date=payment_date,
                        transaction_no=reference,
                        payment_gateway='پرداخت الکترونیک',
                        payment_description=f' درآمد:پرداخت سند {income.doc_number}',
                        is_paid=True,

                    )

                    # 🔹 بروزرسانی Expense
                    income.is_paid = True
                    income.bank = bank
                    income.transaction_reference = reference
                    income.payment_date = payment_date
                    income.unit = unit
                    income.payer_name = unit.get_label() if unit else payer_name

                    income.save(update_fields=[
                        'is_paid',
                        'bank',
                        'transaction_reference',
                        'payment_date',
                        'unit',
                        'payer_name'
                    ])

                messages.success(request, 'دریافت با موفقیت انجام شد')
                return redirect('middle_add_income')

            except ValidationError as e:
                messages.error(request, e.message)
            except Exception as e:
                messages.error(request, f'خطا در دریافت: {e}')

    else:
        form = IncomePayForm(user=request.user)

    return render(
        request,
        'middle_income_templates/income_pay.html',
        {
            'income': income,
            'form': form
        }
    )


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def income_cancel_pay_view(request, income_id):
    income = get_object_or_404(
        Income,
        id=income_id,
        is_paid=True,
        is_active=True,
        user=request.user
    )

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # پیدا کردن Fund مربوطه
                fund = Fund.objects.filter(
                    content_type__model='income',
                    object_id=income.id,
                    user=request.user,
                    is_paid=True
                ).first()

                if not fund:
                    messages.error(request, 'Fund مرتبط با این پرداخت پیدا نشد!')
                    return redirect(request.META.get('HTTP_REFERER'))

                # حذف Fund
                fund.delete()

                # بازمحاسبه موجودی صندوق از این Fund به بعد
                Fund.recalc_final_amounts_from(fund)

                # بازگرداندن Expense به حالت پرداخت‌نشده
                income.is_paid = False
                income.bank = None
                income.transaction_reference = None
                income.payment_date = None
                income.payer_name = None
                income.save(update_fields=[
                    'is_paid',
                    'bank',
                    'transaction_reference',
                    'payment_date',
                    'payer_name',
                ])

                messages.success(request, 'دریافت با موفقیت لغو شد و صندوق اصلاح شد.')
                return redirect(request.META.get('HTTP_REFERER'))

        except Exception as e:
            messages.error(request, f'خطا در لغو دریافت: {e}')
            return redirect(request.META.get('HTTP_REFERER'))

    # اگر GET باشد، فقط برگرد به صفحه قبل
    return redirect(request.META.get('HTTP_REFERER'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_income_edit(request, pk):
    income = get_object_or_404(Income, pk=pk)

    if income.is_paid:
        messages.warning(request, 'این درآمد پرداخت شده است و قابل ویرایش نیست.')
        return redirect('middle_add_income')

    if request.method != 'POST':
        return redirect('middle_add_income')

    form = IncomeForm(request.POST, request.FILES, instance=income, user=request.user)

    if not form.is_valid():
        messages.error(request, 'خطا در ویرایش فرم درآمد. لطفا دوباره تلاش کنید.')
        return redirect('middle_add_income')

    try:
        with transaction.atomic():
            house = MyHouse.objects.filter(user=request.user, is_active=True).first()
            form.instance.house = house
            income = form.save()

            # 🔹 ذخیره فایل‌های جدید بدون حذف قبلی
            files = request.FILES.getlist('document')
            for f in files:
                IncomeDocument.objects.create(income=income, document=f)

        messages.success(request, 'درآمد با موفقیت ویرایش شد.')
        return redirect('middle_add_income')

    except Exception as e:
        messages.error(request, 'خطا در ویرایش درآمد.')
        return redirect('middle_add_income')


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_income_delete(request, pk):
    income = get_object_or_404(Income, id=pk)
    try:
        with transaction.atomic():
            # حذف Fund مربوطه
            income_ct = ContentType.objects.get_for_model(Income)
            Fund.objects.filter(content_type=income_ct, object_id=income.id).delete()

            # حذف خود Expense
            income.delete()

        messages.success(request, 'درآمد با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, "امکان حذف وجود ندارد!")
    except Exception as e:
        messages.error(request, f"خطا در حذف: {str(e)}")

    return redirect(reverse('middle_add_income'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
@csrf_exempt
def middle_delete_income_document(request):
    if request.method == 'POST':
        image_url = request.POST.get('url')
        income_id = request.POST.get('income_id')

        if not image_url or not income_id:
            return JsonResponse({'status': 'error', 'message': 'URL یا ID هزینه مشخص نیست'})

        try:
            income = get_object_or_404(Income, id=income_id)

            relative_path = image_url.replace(settings.MEDIA_URL, '')  # دقیق کردن مسیر
            doc = IncomeDocument.objects.filter(income=income, document=relative_path).first()

            if doc:
                # Delete the file from filesystem
                if doc.document:
                    file_path = os.path.join(settings.MEDIA_ROOT, doc.document.name)
                    if os.path.exists(file_path):
                        os.remove(file_path)

                doc.delete()
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'error', 'message': 'تصویر مرتبط پیدا نشد'})

        except Expense.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'هزینه یافت نشد'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'خطا در حذف تصویر: {str(e)}'})

    return JsonResponse({'status': 'error', 'message': 'درخواست معتبر نیست'})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def export_income_pdf(request):
    house = None
    if request.user.is_authenticated:
        house = MyHouse.objects.filter(residents=request.user).order_by('-created_at').first()
    incomes = Income.objects.filter(user=request.user)

    filter_fields = {
        'category': 'category__id',
        'bank': 'bank__id',
        'amount': 'amount__icontains',
        'doc_number': 'doc_number__icontains',
        'description': 'description__icontains',
        'details': 'details__icontains',
        'is_paid': 'is_paid'
    }

    for field, lookup in filter_fields.items():
        value = request.GET.get(field)
        if value:
            filter_expression = {lookup: value}
            incomes = incomes.filter(**filter_expression)

    # فیلتر تاریخ
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    try:
        if from_date_str:
            from_date = jdatetime.datetime.strptime(from_date_str, '%Y/%m/%d').togregorian().date()
            incomes = incomes.filter(doc_date__gte=from_date)
        if to_date_str:
            to_date = jdatetime.datetime.strptime(to_date_str, '%Y/%m/%d').togregorian().date()
            incomes = incomes.filter(doc_date__lte=to_date)
    except ValueError:
        incomes = Income.objects.none()

    # مسیر فونت
    font_url = request.build_absolute_uri('/static/fonts/BYekan.ttf')
    css = CSS(string=f"""
            @page {{ size: A4 landscape; margin: 1cm; }}
            body {{
                font-family: 'BYekan', sans-serif;
            }}
            @font-face {{
                font-family: 'BYekan';
                src: url('{font_url}');
            }}
        """)

    # رندر قالب HTML
    template = get_template("middle_income_templates/income_pdf.html")
    context = {
        'incomes': incomes,
        'font_path': font_url,
        'house': house,
        'today': timezone.now()
    }

    html = template.render(context)
    page_pdf = io.BytesIO()
    HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(page_pdf, stylesheets=[css])

    page_pdf.seek(0)

    # تولید پاسخ PDF
    pdf_merger = PdfWriter()
    pdf_merger.append(page_pdf)
    response = HttpResponse(content_type='application/pdf')

    response['Content-Disposition'] = f'attachment; filename="incomes.pdf"'

    pdf_merger.write(response)
    return response


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def export_income_excel(request):
    incomes = Income.objects.filter(user=request.user)

    # Filter fields
    filter_fields = {
        'category': 'category__id',
        'bank': 'bank__id',
        'amount': 'amount__icontains',
        'doc_number': 'doc_number__icontains',
        'description': 'description__icontains',
        'details': 'details__icontains',
        'is_paid': 'is_paid'
    }
    # Apply filters based on query parameters
    for field, lookup in filter_fields.items():
        value = request.GET.get(field)
        if value:
            filter_expression = {lookup: value}
            incomes = incomes.filter(**filter_expression)

    # Date range filtering
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    try:
        if from_date_str:
            from_date = jdatetime.datetime.strptime(from_date_str, '%Y/%m/%d').togregorian().date()
            incomes = incomes.filter(doc_date__gte=from_date)
        if to_date_str:
            to_date = jdatetime.datetime.strptime(to_date_str, '%Y/%m/%d').togregorian().date()
            incomes = incomes.filter(doc_date__lte=to_date)
    except ValueError:
        expenses = Expense.objects.none()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "incomes"
    ws.sheet_view.rightToLeft = True

    # ✅ Add title
    title_cell = ws.cell(row=1, column=1, value="لیست درآمدها")
    title_cell.font = Font(bold=True, size=18)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=9)

    # ✅ Style setup
    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")  # Gold
    header_font = Font(bold=True, color="000000")  # Black bold text

    headers = ['#', 'موضوع درآمد', 'شرح سند', ' شماره سند', 'مبلغ', 'تاریخ سند', 'توضیحات', 'پرداخت کننده',
               'تاریخ پرداخت']

    # ✅ Write header (row 2)
    for col_num, column_title in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_num, value=column_title)
        cell.fill = header_fill
        cell.font = header_font

    # ✅ Write data (start from row 3)
    for row_num, income in enumerate(incomes, start=3):
        ws.cell(row=row_num, column=1, value=row_num - 2)  # index starts from 1
        ws.cell(row=row_num, column=2, value=income.category.subject)
        ws.cell(row=row_num, column=3, value=income.description)
        ws.cell(row=row_num, column=4, value=income.doc_number)
        ws.cell(row=row_num, column=5, value=income.amount)
        ws.cell(row=row_num, column=6, value=show_jalali(income.doc_date))
        ws.cell(row=row_num, column=7, value=income.details)
        ws.cell(row=row_num, column=8, value=income.payer_name)
        ws.cell(row=row_num, column=9, value=show_jalali(income.payment_date))

    # ✅ Return file
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=incomes.xlsx'
    wb.save(response)
    return response


# ============================ ReceiveMoneyView ==========================
@method_decorator(middle_admin_required, name='dispatch')
class MiddleReceiveMoneyCreateView(CreateView):
    model = ReceiveMoney
    form_class = ReceiveMoneyForm
    template_name = 'MiddleReceiveMoney/add_receive_money.html'
    success_url = reverse_lazy('middle_add_receive')

    def form_valid(self, form):
        form.instance.user = self.request.user
        try:
            # 🔹 مشخص کردن خانه کاربر
            house = MyHouse.objects.filter(user=self.request.user, is_active=True).first()
            form.instance.house = house  # ذخیره خانه در ReceiveMoney

            self.object = form.save(commit=False)
            self.object.payer_name = self.object.get_payer_display()
            self.object.is_received_money = True
            self.object.save()
            form.save_m2m()

            content_type = ContentType.objects.get_for_model(self.object)
            payer_name_for_fund = self.object.payer_name if not self.object.unit else f"{self.object.unit}"

            # 🔹 ذخیره سند در Fund با خانه
            Fund.objects.create(
                user=self.request.user,
                content_type=content_type,
                object_id=self.object.id,
                bank=self.object.bank,
                unit=self.object.unit,
                house=house,  # ← اضافه شد
                amount=self.object.amount or 0,
                debtor_amount=self.object.amount or 0,
                creditor_amount=0,
                doc_number=self.object.doc_number,
                payer_name=payer_name_for_fund,
                payment_gateway='پرداخت الکترونیک',
                transaction_no=self.object.transaction_reference,
                payment_date=self.object.payment_date,
                payment_description=f"حسابهای دریافتنی: {self.object.description[:50]}",
                is_paid=True,
                is_received_money=True
            )

            files = self.request.FILES.getlist('document')
            for f in files:
                ReceiveDocument.objects.create(receive=self.object, document=f)

            messages.success(self.request, 'سند دریافت با موفقیت ثبت گردید!')
            return super().form_valid(form)

        except Exception as e:
            messages.error(self.request, f'خطا در ثبت! {e}')
            return self.form_invalid(form)

    def get_queryset(self):
        queryset = ReceiveMoney.objects.filter(user=self.request.user).order_by('-created_at')

        bank_id = self.request.GET.get('bank')
        if bank_id:
            queryset = queryset.filter(bank__id=bank_id)

        # فیلتر بر اساس amount
        amount = self.request.GET.get('amount')
        if amount:
            queryset = queryset.filter(amount__icontains=amount)

        payer_name = self.request.GET.get('payer_name')
        if payer_name:
            queryset = queryset.filter(payer_name__icontains=payer_name)

        description = self.request.GET.get('description')
        if description:
            queryset = queryset.filter(description__icontains=description)

        doc_number = self.request.GET.get('doc_number')
        if doc_number:
            queryset = queryset.filter(doc_number__icontains=doc_number)

        details = self.request.GET.get('details')
        if details:
            queryset = queryset.filter(details__icontains=details)

        # فیلتر بر اساس date
        from_date_str = self.request.GET.get('from_date')
        to_date_str = self.request.GET.get('to_date')

        try:
            if from_date_str:
                jalali_from = jdatetime.datetime.strptime(from_date_str, '%Y/%m/%d')
                gregorian_from = jalali_from.togregorian().date()
                queryset = queryset.filter(doc_date__gte=gregorian_from)

            if to_date_str:
                jalali_to = jdatetime.datetime.strptime(to_date_str, '%Y/%m/%d')
                gregorian_to = jalali_to.togregorian().date()
                queryset = queryset.filter(doc_date__lte=gregorian_to)
        except ValueError:
            messages.warning(self.request, 'فرمت تاریخ وارد شده صحیح نیست.')

        is_paid = self.request.GET.get('is_paid')
        if is_paid == '1':
            queryset = queryset.filter(is_paid=True)
        elif is_paid == '0':
            queryset = queryset.filter(is_paid=False)
        return queryset

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        receives = self.get_queryset()
        paginator = Paginator(receives, 50)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context['page_obj'] = page_obj
        context['total_receives'] = ReceiveMoney.objects.filter(user=self.request.user).count()
        context['receives'] = ReceiveMoney.objects.filter(user=self.request.user)
        context['banks'] = Bank.objects.filter(user=self.request.user)
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_receive_edit(request, pk):
    receive = get_object_or_404(
        ReceiveMoney,
        pk=pk,
        user=request.user
    )
    if receive.is_paid:
        messages.warning(request, 'این سند بدلیل ثبت رکورد پرداخت قابل ویرایش نیست')
        return redirect('middle_add_receive')

    if request.method == 'POST':
        form = ReceiveMoneyForm(
            request.POST,
            request.FILES,
            instance=receive,
            user=request.user
        )

        if form.is_valid():
            try:
                with transaction.atomic():

                    receive = form.save(commit=False)
                    receive.payer_name = receive.get_payer_display()
                    receive.is_received_money = True
                    receive.save()
                    form.save_m2m()

                    payer_name_for_fund = (
                        str(receive.unit) if receive.unit else receive.payer_name
                    )

                    content_type = ContentType.objects.get_for_model(receive)

                    fund, created = Fund.objects.get_or_create(
                        content_type=content_type,
                        object_id=receive.id,
                        defaults={
                            'user': request.user,
                        }
                    )

                    fund.bank = receive.bank
                    fund.unit = receive.unit
                    fund.amount = receive.amount or 0
                    fund.debtor_amount = receive.amount or 0
                    fund.creditor_amount = 0
                    fund.payment_date = receive.payment_date
                    fund.transaction_no = receive.transaction_reference
                    fund.doc_number = receive.doc_number
                    fund.payment_gateway = 'پرداخت الکترونیک'
                    fund.payer_name = payer_name_for_fund
                    fund.payment_description = (
                        f"حسابهای دریافتنی: {(receive.description or '')[:50]}"
                    )
                    fund.is_paid = True
                    fund.is_received_money = True
                    fund.save()

                    Fund.recalc_final_amounts_from(fund)

                    # 📎 ذخیره فایل‌ها
                    files = request.FILES.getlist('document')
                    for f in files:
                        ReceiveDocument.objects.create(
                            receive=receive,
                            document=f
                        )

                messages.success(request, 'سند با موفقیت ویرایش گردید.')
                return redirect('middle_add_receive')

            except Exception as e:
                messages.error(request, f'خطا در ذخیره اطلاعات: {e}')

        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفاً دوباره تلاش کنید.')

    else:
        form = ReceiveMoneyForm(instance=receive, user=request.user)

    return render(
        request,
        'MiddleReceiveMoney/add_receive_money.html',
        {
            'form': form,
            'receive': receive,
        }
    )


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_receive_delete(request, pk):
    receive = get_object_or_404(ReceiveMoney, id=pk)
    try:
        with transaction.atomic():
            # حذف Fund مربوطه
            receive_ct = ContentType.objects.get_for_model(ReceiveMoney)
            Fund.objects.filter(content_type=receive_ct, object_id=receive.id).delete()

            # حذف خود Expense
            receive.delete()
            messages.success(request, ' سند با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('middle_add_receive'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
@csrf_exempt
def middle_delete_receive_document(request):
    if request.method == 'POST':
        image_url = request.POST.get('url')
        receive_id = request.POST.get('receive_id')

        if not image_url or not receive_id:
            return JsonResponse({'status': 'error', 'message': 'URL یا ID هزینه مشخص نیست'})

        try:
            receive = get_object_or_404(ReceiveMoney, id=receive_id)

            relative_path = image_url.replace(settings.MEDIA_URL, '')  # دقیق کردن مسیر
            doc = ReceiveDocument.objects.filter(receive=receive, document=relative_path).first()

            if doc:
                # Delete the file from filesystem
                if doc.document:
                    file_path = os.path.join(settings.MEDIA_ROOT, doc.document.name)
                    if os.path.exists(file_path):
                        os.remove(file_path)

                doc.delete()
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'error', 'message': 'تصویر مرتبط پیدا نشد'})

        except Expense.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'هزینه یافت نشد'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'خطا در حذف تصویر: {str(e)}'})

    return JsonResponse({'status': 'error', 'message': 'درخواست معتبر نیست'})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def export_receive_pdf(request):
    house = None
    if request.user.is_authenticated:
        house = MyHouse.objects.filter(residents=request.user).order_by('-created_at').first()
    receives = ReceiveMoney.objects.select_related('bank').filter(user=request.user)

    filter_fields = {
        'bank': 'bank__id',
        'payer_name': 'payer_name__icontains',
        'amount': 'amount__icontains',
        'doc_number': 'doc_number__icontains',
        'description': 'description__icontains',
        'details': 'details__icontains',
    }

    for field, lookup in filter_fields.items():
        value = request.GET.get(field)
        if value:
            filter_expression = {lookup: value}
            receives = receives.filter(**filter_expression)

    # فیلتر تاریخ
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    try:
        if from_date_str:
            from_date = jdatetime.datetime.strptime(from_date_str, '%Y/%m/%d').togregorian().date()
            receives = receives.filter(doc_date__gte=from_date)
        if to_date_str:
            to_date = jdatetime.datetime.strptime(to_date_str, '%Y/%m/%d').togregorian().date()
            receives = receives.filter(doc_date__lte=to_date)
    except ValueError:
        receives = ReceiveMoney.objects.none()

    # مسیر فونت
    font_url = request.build_absolute_uri('/static/fonts/BYekan.ttf')
    css = CSS(string=f"""
            @page {{ size: A4 landscape; margin: 1cm; }}
            body {{
                font-family: 'BYekan', sans-serif;
            }}
            @font-face {{
                font-family: 'BYekan';
                src: url('{font_url}');
            }}
        """)

    # رندر قالب HTML
    template = get_template("MiddleReceiveMoney/receive_pdf.html")
    context = {
        'receives': receives,
        'font_path': font_url,
        'house': house,
        'today': timezone.now()
    }

    html = template.render(context)
    page_pdf = io.BytesIO()
    HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(page_pdf, stylesheets=[css])

    page_pdf.seek(0)

    # تولید پاسخ PDF
    pdf_merger = PdfWriter()
    pdf_merger.append(page_pdf)
    response = HttpResponse(content_type='application/pdf')

    # response['Content-Disposition'] = f'attachment; filename="receives.pdf"'
    response['Content-Disposition'] = (
        f'attachment; filename="receives_{int(time.time())}.pdf"'
    )

    pdf_merger.write(response)
    return response


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def export_receive_excel(request):
    receives = ReceiveMoney.objects.filter(user=request.user)

    filter_fields = {
        'bank': 'bank__id',
        'payer_name': 'payer_name__icontains',
        'amount': 'amount__icontains',
        'doc_number': 'doc_number__icontains',
        'description': 'description__icontains',
        'details': 'details__icontains',
    }

    # Apply filters based on query parameters
    for field, lookup in filter_fields.items():
        value = request.GET.get(field)
        if value:
            filter_expression = {lookup: value}
            receives = receives.filter(**filter_expression)

    # Date range filtering
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    try:
        if from_date_str:
            from_date = jdatetime.datetime.strptime(from_date_str, '%Y/%m/%d').togregorian().date()
            receives = receives.filter(doc_date__gte=from_date)
        if to_date_str:
            to_date = jdatetime.datetime.strptime(to_date_str, '%Y/%m/%d').togregorian().date()
            receives = receives.filter(doc_date__lte=to_date)
    except ValueError:
        receives = ReceiveMoney.objects.none()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "receives"
    ws.sheet_view.rightToLeft = True

    # ✅ Add title
    title_cell = ws.cell(row=1, column=1, value="لیست اسناد دریافتنی")
    title_cell.font = Font(bold=True, size=18)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=10)

    # ✅ Style setup
    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")  # Gold
    header_font = Font(bold=True, color="000000")  # Black bold text

    headers = ['#', 'شماره جساب', 'دریافت کننده', 'شرح سند', ' شماره سند', 'مبلغ', 'تاریخ سند', 'توضیحات',
               'تاریخ پرداخت', 'شماره پیگیری']

    # ✅ Write header (row 2)
    for col_num, column_title in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_num, value=column_title)
        cell.fill = header_fill
        cell.font = header_font

    # ✅ Write data (start from row 3)
    for row_num, receive in enumerate(receives, start=3):
        ws.cell(row=row_num, column=1, value=row_num - 2)  # index starts from 1
        bank_account = ""
        if receive.bank and receive.bank.account_no:
            bank_account = f"{receive.bank.bank_name} - {receive.bank.account_no}"
        payer_name = (
            str(receive.unit)
            if receive.unit
            else receive.payer_name
        )
        ws.cell(row=row_num, column=2, value=bank_account)
        ws.cell(row=row_num, column=3, value=payer_name)
        ws.cell(row=row_num, column=4, value=receive.description)
        ws.cell(row=row_num, column=5, value=receive.doc_number)
        ws.cell(row=row_num, column=6, value=receive.amount)
        ws.cell(row=row_num, column=7, value=show_jalali(receive.doc_date))
        ws.cell(row=row_num, column=8, value=receive.details)
        ws.cell(row=row_num, column=9, value=show_jalali(receive.payment_date))
        ws.cell(row=row_num, column=10, value=receive.transaction_reference)

    # ✅ Return file
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=receive_doc.xlsx'
    wb.save(response)
    return response


# ============================ PaymentMoneyView ==========================
@method_decorator(middle_admin_required, name='dispatch')
class MiddlePaymentMoneyCreateView(CreateView):
    model = PayMoney
    form_class = PayerMoneyForm
    template_name = 'MiddlePayMoney/add_pay_money.html'
    success_url = reverse_lazy('middle_add_pay')

    def form_valid(self, form):
        form.instance.user = self.request.user
        house = MyHouse.objects.filter(user=self.request.user, is_active=True).first()
        form.instance.house = house

        with transaction.atomic():

            self.object = form.save(commit=False)

            bank = self.object.bank
            amount = self.object.amount

            bank_funds = Fund.objects.filter(
                user=self.request.user,
                bank=bank
            )

            total_debit = bank_funds.aggregate(
                Sum('debtor_amount')
            )['debtor_amount__sum'] or 0

            total_credit = bank_funds.aggregate(
                Sum('creditor_amount')
            )['creditor_amount__sum'] or 0

            current_final = Decimal(total_debit) - Decimal(total_credit)

            if current_final < amount:
                messages.error(self.request, 'موجودی صندوق کافی نیست')
                return self.form_invalid(form)

            self.object.receiver_name = self.object.get_receiver_display
            self.object.is_paid_money = True
            self.object.save()
            form.save_m2m()

            content_type = ContentType.objects.get_for_model(self.object)

            receiver_name_for_fund = (
                self.object.receiver_name
                if not self.object.unit else f"{self.object.unit}"
            )

            Fund.objects.create(
                user=self.request.user,
                content_type=content_type,
                object_id=self.object.id,
                bank=bank,
                house=house,
                unit=self.object.unit,
                amount=self.object.amount,
                debtor_amount=0,
                receiver_name=receiver_name_for_fund,
                creditor_amount=self.object.amount,
                payment_gateway='پرداخت الکترونیک',
                payment_date=self.object.payment_date,
                doc_number=self.object.document_number,
                payment_description=f"حسابهای پرداختنی: {self.object.description[:50]}",
                is_paid=True,
                is_paid_money=True
            )

            files = self.request.FILES.getlist('document')
            for f in files:
                PayDocument.objects.create(payment=self.object, document=f)

            messages.success(self.request, 'سند پرداخت با موفقیت ثبت گردید!')
            return super().form_valid(form)

        # except Exception as e:
        #     messages.error(self.request, f'خطا در ثبت: {e}')
        #     return self.form_invalid(form)

    def get_queryset(self):
        queryset = PayMoney.objects.filter(user=self.request.user).order_by('-created_at')

        bank_id = self.request.GET.get('bank')
        if bank_id:
            queryset = queryset.filter(bank__id=bank_id)

        # فیلتر بر اساس amount
        amount = self.request.GET.get('amount')
        if amount:
            queryset = queryset.filter(amount__icontains=amount)

        receiver_name = self.request.GET.get('payer_name')
        if receiver_name:
            queryset = queryset.filter(receiver_name__icontains=receiver_name)

        description = self.request.GET.get('description')
        if description:
            queryset = queryset.filter(description__icontains=description)

        document_number = self.request.GET.get('document_number')
        if document_number:
            queryset = queryset.filter(document_number__icontains=document_number)

        details = self.request.GET.get('details')
        if details:
            queryset = queryset.filter(details__icontains=details)

        # فیلتر بر اساس date
        from_date_str = self.request.GET.get('from_date')
        to_date_str = self.request.GET.get('to_date')

        try:
            if from_date_str:
                jalali_from = jdatetime.datetime.strptime(from_date_str, '%Y/%m/%d')
                gregorian_from = jalali_from.togregorian().date()
                queryset = queryset.filter(document_date__gte=gregorian_from)

            if to_date_str:
                jalali_to = jdatetime.datetime.strptime(to_date_str, '%Y/%m/%d')
                gregorian_to = jalali_to.togregorian().date()
                queryset = queryset.filter(document_date__lte=gregorian_to)
        except ValueError:
            messages.warning(self.request, 'فرمت تاریخ وارد شده صحیح نیست.')

        is_paid = self.request.GET.get('is_paid')
        if is_paid == '1':
            queryset = queryset.filter(is_paid=True)
        elif is_paid == '0':
            queryset = queryset.filter(is_paid=False)
        return queryset

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        receives = self.get_queryset()
        paginator = Paginator(receives, 50)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context['page_obj'] = page_obj
        context['total_payments'] = PayMoney.objects.filter(user=self.request.user).count()
        context['payments'] = PayMoney.objects.filter(user=self.request.user)
        context['banks'] = Bank.objects.filter(user=self.request.user)
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_pay_edit(request, pk):
    # گرفتن رکورد پرداخت موجود
    payment = get_object_or_404(PayMoney, pk=pk)

    if payment.is_paid:
        messages.warning(request, 'این سند بدلیل ثبت رکورد پرداخت قابل ویرایش نیست')
        return redirect('middle_add_pay')

    if request.method == 'POST':
        # فرم با instance برای ویرایش
        form = PayerMoneyForm(request.POST, request.FILES, instance=payment, user=request.user)

        if form.is_valid():
            payment = form.save(commit=False)
            payment.receiver_name = payment.get_receiver_display
            payment.is_paid_money = True
            payment.save()
            form.save_m2m()

            if payment.unit:
                receiver_name_for_fund = str(payment.unit)
            else:
                receiver_name_for_fund = payment.receiver_name

            content_type = ContentType.objects.get_for_model(PayMoney)
            fund = Fund.objects.filter(content_type=content_type, object_id=payment.id).first()

            if fund:
                # بروزرسانی رکورد موجود
                fund.bank = payment.bank
                fund.unit = payment.unit
                fund.debtor_amount = 0
                fund.amount = payment.amount or 0
                fund.creditor_amount = payment.amount or 0
                fund.payment_date = payment.document_date
                fund.doc_number = payment.document_number
                fund.receiver_name = receiver_name_for_fund
                fund.payment_gateway = 'پرداخت الکترونیک'
                fund.payment_description = f"حسابهای پرداختنی: {(payment.description or '')[:50]}"
                fund.is_paid_money = True
                fund.is_paid = True
                fund.save()  # موجودی بانک بروزرسانی می‌شود
                Fund.recalc_final_amounts_from(fund)


            else:
                # ایجاد فقط اگر رکورد موجود نبود
                Fund.objects.create(
                    content_type=content_type,
                    object_id=payment.id,
                    bank=payment.bank,
                    unit=payment.unit,
                    debtor_amount=0,
                    amount=payment.amount or 0,
                    creditor_amount=payment.amount or 0,
                    user=request.user,
                    receiver_name=receiver_name_for_fund,
                    payment_date=payment.document_date,
                    doc_number=payment.document_number,
                    payment_gateway='پرداخت الکترونیک',
                    payment_description=f"حسابهای پرداختنی: {(payment.description or '')[:50]}",
                    is_paid=True,
                    is_paid_money=True
                )

            # ثبت فایل‌های پیوست جدید
            files = request.FILES.getlist('document')
            for f in files:
                PayDocument.objects.create(payment=payment, document=f)

            messages.success(request, 'سند با موفقیت ویرایش گردید.')
            return redirect(reverse('middle_add_pay'))  # Adjust redirect as necessary

        else:
            messages.error(request, 'خطا در ویرایش فرم . لطفا دوباره تلاش کنید.')
            return render(request, 'MiddlePayMoney/add_pay_money.html', {'form': form, 'payment': payment})
    else:
        form = PayerMoneyForm(instance=payment, user=request.user)
        return render(request, 'MiddlePayMoney/add_pay_money.html', {'form': form, 'payment': payment})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_pay_delete(request, pk):
    payment = get_object_or_404(PayMoney, id=pk)
    try:
        with transaction.atomic():
            # حذف Fund مربوطه
            payment_ct = ContentType.objects.get_for_model(PayMoney)
            Fund.objects.filter(content_type=payment_ct, object_id=payment.id).delete()

            # حذف خود Expense
            payment.delete()
        messages.success(request, ' سند با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('middle_add_pay'))


@login_required(login_url=settings.LOGIN_URL_ADMIN)
@csrf_exempt
def middle_delete_pay_document(request):
    if request.method == 'POST':
        image_url = request.POST.get('url')
        payment_id = request.POST.get('payment_id')

        if not image_url or not payment_id:
            return JsonResponse({'status': 'error', 'message': 'URL یا ID هزینه مشخص نیست'})

        try:
            payment = get_object_or_404(PayMoney, id=payment_id)

            relative_path = image_url.replace(settings.MEDIA_URL, '')  # دقیق کردن مسیر
            doc = PayDocument.objects.filter(payment=payment, document=relative_path).first()

            if doc:
                # Delete the file from filesystem
                if doc.document:
                    file_path = os.path.join(settings.MEDIA_ROOT, doc.document.name)
                    if os.path.exists(file_path):
                        os.remove(file_path)

                doc.delete()
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'error', 'message': 'تصویر مرتبط پیدا نشد'})

        except Expense.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'هزینه یافت نشد'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'خطا در حذف تصویر: {str(e)}'})

    return JsonResponse({'status': 'error', 'message': 'درخواست معتبر نیست'})


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def export_pay_pdf(request):
    house = None
    if request.user.is_authenticated:
        house = MyHouse.objects.filter(residents=request.user).order_by('-created_at').first()
    payments = PayMoney.objects.filter(user=request.user)

    filter_fields = {
        'bank': 'bank__id',
        'receiver_name': 'payer_name',
        'amount': 'amount__icontains',
        'document_number': 'doc_number__icontains',
        'description': 'description__icontains',
        'details': 'details__icontains',
        'is_paid': 'is_paid'
    }

    for field, lookup in filter_fields.items():
        value = request.GET.get(field)
        if value:
            filter_expression = {lookup: value}
            payments = payments.filter(**filter_expression)

    # فیلتر تاریخ
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    try:
        if from_date_str:
            from_date = jdatetime.datetime.strptime(from_date_str, '%Y/%m/%d').togregorian().date()
            payments = payments.filter(document_date__gte=from_date)
        if to_date_str:
            to_date = jdatetime.datetime.strptime(to_date_str, '%Y/%m/%d').togregorian().date()
            payments = payments.filter(document_date__lte=to_date)
    except ValueError:
        payments = PayMoney.objects.none()

    # مسیر فونت
    font_url = request.build_absolute_uri('/static/fonts/BYekan.ttf')
    css = CSS(string=f"""
            @page {{ size: A4 landscape; margin: 1cm; }}
            body {{
                font-family: 'BYekan', sans-serif;
            }}
            @font-face {{
                font-family: 'BYekan';
                src: url('{font_url}');
            }}
        """)

    # رندر قالب HTML
    template = get_template("MiddlePayMoney/pay_pdf.html")
    context = {
        'payments': payments,
        'font_path': font_url,
        'house': house,
        'today': timezone.now()
    }

    html = template.render(context)
    page_pdf = io.BytesIO()
    HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(page_pdf, stylesheets=[css])

    page_pdf.seek(0)

    # تولید پاسخ PDF
    pdf_merger = PdfWriter()
    pdf_merger.append(page_pdf)
    response = HttpResponse(content_type='application/pdf')

    response['Content-Disposition'] = f'attachment; filename="payments.pdf"'

    pdf_merger.write(response)
    return response


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def export_pay_excel(request):
    payments = PayMoney.objects.filter(user=request.user)

    filter_fields = {
        'bank': 'bank__id',
        'receiver_name': 'receiver_name__icontains',
        'amount': 'amount__icontains',
        'doc_number': 'doc_number__icontains',
        'description': 'description__icontains',
        'details': 'details__icontains',
        'is_paid': 'is_paid'
    }

    # Apply filters based on query parameters
    for field, lookup in filter_fields.items():
        value = request.GET.get(field)
        if value:
            filter_expression = {lookup: value}
            payments = payments.filter(**filter_expression)

    # Date range filtering
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    try:
        if from_date_str:
            from_date = jdatetime.datetime.strptime(from_date_str, '%Y/%m/%d').togregorian().date()
            payments = payments.filter(document_date__gte=from_date)
        if to_date_str:
            to_date = jdatetime.datetime.strptime(to_date_str, '%Y/%m/%d').togregorian().date()
            payments = payments.filter(document_date__lte=to_date)
    except ValueError:
        payments = PayMoney.objects.none()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "payments"
    ws.sheet_view.rightToLeft = True

    # ✅ Add title
    title_cell = ws.cell(row=1, column=1, value="لیست اسناد پرداختنی")
    title_cell.font = Font(bold=True, size=18)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=10)

    # ✅ Style setup
    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")  # Gold
    header_font = Font(bold=True, color="000000")  # Black bold text

    headers = ['#', 'شماره جساب', 'دریافت کننده', 'شرح سند', ' شماره سند', 'مبلغ', 'تاریخ سند', 'توضیحات',
               'تاریخ پرداخت', 'شماره پیگیری']

    # ✅ Write header (row 2)
    for col_num, column_title in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_num, value=column_title)
        cell.fill = header_fill
        cell.font = header_font

    # ✅ Write data (start from row 3)
    for row_num, payment in enumerate(payments, start=3):
        ws.cell(row=row_num, column=1, value=row_num - 2)  # index starts from 1
        bank_account = ""
        if payment.bank and payment.bank.account_no:
            bank_account = f"{payment.bank.bank_name} - {payment.bank.account_no}"

        receiver_name = (
            str(payment.unit)
            if payment.unit
            else payment.receiver_name
        )

        ws.cell(row=row_num, column=2, value=bank_account)
        ws.cell(row=row_num, column=3, value=receiver_name)
        ws.cell(row=row_num, column=4, value=payment.description)
        ws.cell(row=row_num, column=5, value=payment.document_number)
        ws.cell(row=row_num, column=6, value=payment.amount)
        ws.cell(row=row_num, column=7, value=show_jalali(payment.document_date))
        ws.cell(row=row_num, column=8, value=payment.details)
        ws.cell(row=row_num, column=9, value=show_jalali(payment.payment_date))
        ws.cell(row=row_num, column=10, value=payment.transaction_reference)

    # ✅ Return file
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=payment.xlsx'
    wb.save(response)
    return response


# ============================ PropertyView ==========================
@method_decorator(middle_admin_required, name='dispatch')
class MiddlePropertyCreateView(CreateView):
    model = Property
    template_name = 'middleProperty/manage_property.html'
    form_class = PropertyForm
    success_url = reverse_lazy('middle_add_property')

    def form_valid(self, form):
        form.instance.user = self.request.user
        house = MyHouse.objects.filter(user=self.request.user, is_active=True).first()
        form.instance.house = house
        try:
            self.object = form.save()
            files = self.request.FILES.getlist('document')

            for f in files:
                PropertyDocument.objects.create(property=self.object, document=f)
            messages.success(self.request, 'سند پرداخت با موفقیت ثبت گردید!')
            return super().form_valid(form)
        except:
            messages.error(self.request, 'خطا در ثبت!')
            return self.form_invalid(form)

    def get_queryset(self):
        queryset = Property.objects.filter(user=self.request.user)

        # فیلتر بر اساس amount
        property_name = self.request.GET.get('property_name')
        if property_name:
            queryset = queryset.filter(property_name__icontains=property_name)

        property_unit = self.request.GET.get('property_unit')
        if property_unit:
            queryset = queryset.filter(property_unit__icontains=property_unit)

        property_location = self.request.GET.get('property_location')
        if property_location:
            queryset = queryset.filter(property_location__icontains=property_location)

        property_code = self.request.GET.get('property_code')
        if property_code:
            queryset = queryset.filter(property_code__icontains=property_code)

        property_price = self.request.GET.get('property_price')
        if property_price:
            queryset = queryset.filter(property_price__icontains=property_price)

        details = self.request.GET.get('details')
        if details:
            queryset = queryset.filter(details__icontains=details)

        # فیلتر بر اساس date
        from_date_str = self.request.GET.get('from_date')
        to_date_str = self.request.GET.get('to_date')

        try:
            if from_date_str:
                jalali_from = jdatetime.datetime.strptime(from_date_str, '%Y-%m-%d')
                gregorian_from = jalali_from.togregorian().date()
                queryset = queryset.filter(property_purchase_date__gte=gregorian_from)

            if to_date_str:
                jalali_to = jdatetime.datetime.strptime(to_date_str, '%Y-%m-%d')
                gregorian_to = jalali_to.togregorian().date()
                queryset = queryset.filter(property_purchase_date__lte=gregorian_to)
        except ValueError:
            messages.warning(self.request, 'فرمت تاریخ وارد شده صحیح نیست.')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        receives = self.get_queryset()
        paginator = Paginator(receives, 50)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context['page_obj'] = page_obj
        context['total_properties'] = Property.objects.filter(user=self.request.user).count()
        context['properties'] = Property.objects.filter(user=self.request.user)
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_property_edit(request, pk):
    property_d = get_object_or_404(Property, pk=pk)

    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES, instance=property_d)

        if form.is_valid():
            property_d = form.save()  # Save the form (updates or creates expense)

            # Handle multiple file uploads
            files = request.FILES.getlist('document')
            if files:
                for f in files:
                    PropertyDocument.objects.create(property_d=property_d, document=f)

            messages.success(request, 'اموال با موفقیت ویرایش شد.')
            return redirect('middle_add_property')  # Adjust redirect as necessary

        else:
            messages.error(request, 'خطا در ویرایش فرم درآمد. لطفا دوباره تلاش کنید.')
            return redirect('middle_add_property')
    else:
        # If the request is not POST, redirect to the appropriate page
        return redirect('middle_add_property')


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_property_delete(request, pk):
    property_d = get_object_or_404(Property, id=pk)
    try:
        property_d.delete()
        messages.success(request, ' اموال با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('middle_add_property'))


@login_required(login_url=settings.LOGIN_URL_ADMIN)
@csrf_exempt
def middle_delete_property_document(request):
    if request.method == 'POST':
        image_url = request.POST.get('url')
        property_id = request.POST.get('property_id')

        print(f'property_id: {property_id}')

        if not image_url or not property_id:
            return JsonResponse({'status': 'error', 'message': 'URL یا ID هزینه مشخص نیست'})

        try:
            property = get_object_or_404(Property, id=property_id)

            relative_path = image_url.replace(settings.MEDIA_URL, '')  # دقیق کردن مسیر
            doc = PropertyDocument.objects.filter(property=property, document=relative_path).first()

            if doc:
                # Delete the file from filesystem
                if doc.document:
                    file_path = os.path.join(settings.MEDIA_ROOT, doc.document.name)
                    if os.path.exists(file_path):
                        os.remove(file_path)

                doc.delete()
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'error', 'message': 'تصویر مرتبط پیدا نشد'})

        except Expense.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'هزینه یافت نشد'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'خطا در حذف تصویر: {str(e)}'})

    return JsonResponse({'status': 'error', 'message': 'درخواست معتبر نیست'})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def export_property_pdf(request):
    properties = Property.objects.all()

    filter_fields = {
        'property_name': 'property_name__icontains',
        'property_unit': 'property_unit__icontains',
        'property_location': 'property_location__icontains',
        'property_code': 'property_code__icontains',
        'property_price': 'property_price__icontains',
        'details': 'details__icontains',

    }

    for field, lookup in filter_fields.items():
        value = request.GET.get(field)
        if value:
            filter_expression = {lookup: value}
            properties = properties.filter(**filter_expression)

    # فیلتر تاریخ
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    try:
        if from_date_str:
            from_date = jdatetime.datetime.strptime(from_date_str, '%Y/%m/%d').togregorian().date()
            properties = properties.filter(property_purchase_date__gte=from_date)
        if to_date_str:
            to_date = jdatetime.datetime.strptime(to_date_str, '%Y/%m/%d').togregorian().date()
            properties = properties.filter(property_purchase_date__lte=to_date)
    except ValueError:
        properties = Property.objects.none()

    # مسیر فونت
    font_url = request.build_absolute_uri('/static/fonts/BYekan.ttf')
    css = CSS(string=f"""
            @page {{ size: A4 landscape; margin: 1cm; }}
            body {{
                font-family: 'BYekan', sans-serif;
            }}
            @font-face {{
                font-family: 'BYekan';
                src: url('{font_url}');
            }}
        """)

    # رندر قالب HTML
    template = get_template("property/property_pdf.html")
    context = {
        'properties': properties,
        'font_path': font_url,
    }

    html = template.render(context)
    page_pdf = io.BytesIO()
    HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(page_pdf, stylesheets=[css])

    page_pdf.seek(0)

    # تولید پاسخ PDF
    pdf_merger = PdfWriter()
    pdf_merger.append(page_pdf)
    response = HttpResponse(content_type='application/pdf')

    response['Content-Disposition'] = f'attachment; filename="properties.pdf"'

    pdf_merger.write(response)
    return response


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def export_property_excel(request):
    properties = Property.objects.all()

    filter_fields = {
        'property_name': 'property_name__icontains',
        'property_unit': 'property_unit__icontains',
        'property_location': 'property_location__icontains',
        'property_code': 'property_code__icontains',
        'property_price': 'property_price__icontains',
        'details': 'details__icontains',

    }

    # Apply filters based on query parameters
    for field, lookup in filter_fields.items():
        value = request.GET.get(field)
        if value:
            filter_expression = {lookup: value}
            properties = properties.filter(**filter_expression)

    # Date range filtering
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    try:
        if from_date_str:
            from_date = jdatetime.datetime.strptime(from_date_str, '%Y/%m/%d').togregorian().date()
            properties = properties.filter(property_purchase_date__gte=from_date)
        if to_date_str:
            to_date = jdatetime.datetime.strptime(to_date_str, '%Y/%m/%d').togregorian().date()
            properties = properties.filter(property_purchase_date__lte=to_date)
    except ValueError:
        properties = Property.objects.none()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "properties"
    ws.sheet_view.rightToLeft = True

    # ✅ Add title
    title_cell = ws.cell(row=1, column=1, value="لیست اموال ساختمان")
    title_cell.font = Font(bold=True, size=18)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=8)

    # ✅ Style setup
    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")  # Gold
    header_font = Font(bold=True, color="000000")  # Black bold text

    headers = ['#', 'نام اموال', 'واحد', ' شماره اموال', ' موقعیت ', 'ارزش', 'تاریخ خرید', 'توضیحات']

    # ✅ Write header (row 2)
    for col_num, column_title in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_num, value=column_title)
        cell.fill = header_fill
        cell.font = header_font

    # ✅ Write data (start from row 3)
    for row_num, property in enumerate(properties, start=3):
        ws.cell(row=row_num, column=1, value=row_num - 2)  # index starts from 1
        ws.cell(row=row_num, column=2, value=property.property_name)
        ws.cell(row=row_num, column=3, value=property.property_unit)
        ws.cell(row=row_num, column=4, value=property.property_code)
        ws.cell(row=row_num, column=5, value=property.property_location)
        ws.cell(row=row_num, column=6, value=property.property_price)
        jalali_date = jdatetime.date.fromgregorian(date=property.property_purchase_date).strftime('%Y/%m/%d')
        ws.cell(row=row_num, column=7, value=jalali_date)
        ws.cell(row=row_num, column=8, value=property.details)

    # ✅ Return file
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=properties.xlsx'
    wb.save(response)
    return response


# ============================ MaintenanceView ==========================
@method_decorator(middle_admin_required, name='dispatch')
class MiddleMaintenanceCreateView(CreateView):
    model = Maintenance
    template_name = 'middleMaintenance/add_maintenance.html'
    form_class = MaintenanceForm
    success_url = reverse_lazy('middle_add_maintenance')

    def form_valid(self, form):
        form.instance.user = self.request.user
        house = MyHouse.objects.filter(user=self.request.user, is_active=True).first()
        form.instance.house = house
        try:
            self.object = form.save()
            files = self.request.FILES.getlist('document')

            for f in files:
                MaintenanceDocument.objects.create(maintenance=self.object, document=f)
            messages.success(self.request, 'سند با موفقیت ثبت گردید!')
            return super().form_valid(form)
        except:
            messages.error(self.request, 'خطا در ثبت!')
            return self.form_invalid(form)

    def get_queryset(self):
        queryset = Maintenance.objects.filter(user=self.request.user)

        # فیلتر بر اساس amount
        maintenance_description = self.request.GET.get('maintenance_description')
        if maintenance_description:
            queryset = queryset.filter(maintenance_description__icontains=maintenance_description)

        maintenance_price = self.request.GET.get('maintenance_price')
        if maintenance_price:
            queryset = queryset.filter(maintenance_price__icontains=maintenance_price)

        maintenance_status = self.request.GET.get('maintenance_status')
        if maintenance_status:
            queryset = queryset.filter(maintenance_status__icontains=maintenance_status)

        service_company = self.request.GET.get('service_company')
        if service_company:
            queryset = queryset.filter(service_company__icontains=service_company)

        maintenance_start_date = self.request.GET.get('maintenance_start_date')
        if maintenance_start_date and isinstance(maintenance_start_date, str):
            try:
                j_start = jdatetime.date.fromisoformat(maintenance_start_date)
                g_start = j_start.togregorian()
                queryset = queryset.filter(maintenance_start_date__gte=g_start)
            except (ValueError, TypeError) as e:
                print("Invalid date format:", maintenance_start_date, e)

        maintenance_end_date = self.request.GET.get('maintenance_end_date')
        if maintenance_end_date and isinstance(maintenance_end_date, str):
            try:
                j_start = jdatetime.date.fromisoformat(maintenance_end_date)
                g_start = j_start.togregorian()
                queryset = queryset.filter(maintenance_end_date__lte=g_start)
            except (ValueError, TypeError) as e:
                print("Invalid date format:", maintenance_end_date, e)

        details = self.request.GET.get('details')
        if details:
            queryset = queryset.filter(details__icontains=details)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        maintenances = self.get_queryset()
        paginator = Paginator(maintenances, 50)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['page_obj'] = page_obj
        context['total_maintenances'] = maintenances.filter(user=self.request.user).count()
        context['maintenances'] = page_obj.object_list
        return context


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def middle_maintenance_edit(request, pk):
    maintenance = get_object_or_404(Maintenance, pk=pk)

    if request.method == 'POST':
        form = MaintenanceForm(request.POST, request.FILES, instance=maintenance)

        if form.is_valid():
            maintenance = form.save()  # Save the form (updates or creates expense)

            # Handle multiple file uploads
            files = request.FILES.getlist('document')
            if files:
                for f in files:
                    MaintenanceDocument.objects.create(maintenance=maintenance, document=f)

            messages.success(request, 'سند با موفقیت ویرایش شد.')
            return redirect('middle_add_maintenance')  # Adjust redirect as necessary

        else:
            messages.error(request, 'خطا در ویرایش فرم درآمد. لطفا دوباره تلاش کنید.')
            return redirect('middle_add_maintenance')
    else:
        # If the request is not POST, redirect to the appropriate page
        return redirect('middle_add_maintenance')


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def middle_maintenance_delete(request, pk):
    maintenance = get_object_or_404(Maintenance, id=pk)
    try:
        maintenance.delete()
        messages.success(request, ' سند با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('middle_add_maintenance'))


@login_required(login_url=settings.LOGIN_URL_ADMIN)
@csrf_exempt
def middle_delete_maintenance_document(request):
    if request.method == 'POST':
        image_url = request.POST.get('url')
        maintenance_id = request.POST.get('maintenance_id')

        print(f'maintenance_id: {maintenance_id}')

        if not image_url or not maintenance_id:
            return JsonResponse({'status': 'error', 'message': 'URL یا ID هزینه مشخص نیست'})

        try:
            maintenance = get_object_or_404(Maintenance, id=maintenance_id)

            relative_path = image_url.replace(settings.MEDIA_URL, '')  # دقیق کردن مسیر
            doc = MaintenanceDocument.objects.filter(maintenance=maintenance, document=relative_path).first()

            if doc:
                # Delete the file from filesystem
                if doc.document:
                    file_path = os.path.join(settings.MEDIA_ROOT, doc.document.name)
                    if os.path.exists(file_path):
                        os.remove(file_path)

                doc.delete()
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'error', 'message': 'تصویر مرتبط پیدا نشد'})

        except Expense.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'هزینه یافت نشد'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'خطا در حذف تصویر: {str(e)}'})

    return JsonResponse({'status': 'error', 'message': 'درخواست معتبر نیست'})


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def parse_jalali_to_gregorian(date_str):
    try:
        return jdatetime.date.fromisoformat(date_str.strip()).togregorian()
    except Exception:
        return None


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def export_maintenance_pdf(request):
    maintenances = Maintenance.objects.all()

    filter_fields = {
        'maintenance_description': 'maintenance_description__icontains',
        'maintenance_start_date': 'maintenance_start_date__gte',
        'maintenance_end_date': 'maintenance_end_date__lte',
        'maintenance_price': 'maintenance_price__icontains',
        'maintenance_status': 'maintenance_status__icontains',
        'service_company': 'service_company__icontains',
        'maintenance_document_no': 'maintenance_document_no__icontains',
        'details': 'details__icontains',
    }

    for field, lookup in filter_fields.items():
        value = request.GET.get(field)
        if value:
            if field in ['maintenance_start_date', 'maintenance_end_date']:
                gregorian_date = parse_jalali_to_gregorian(value)
                if gregorian_date:
                    maintenances = maintenances.filter(**{lookup: gregorian_date})
            else:
                maintenances = maintenances.filter(**{lookup: value.strip()})

    # مسیر فونت
    font_url = request.build_absolute_uri('/static/fonts/BYekan.ttf')
    css = CSS(string=f"""
            @page {{ size: A4 landscape; margin: 1cm; }}
            body {{
                font-family: 'BYekan', sans-serif;
            }}
            @font-face {{
                font-family: 'BYekan';
                src: url('{font_url}');
            }}
        """)

    # رندر قالب HTML
    template = get_template("maintenance/maintenance_pdf.html")
    context = {
        'maintenances': maintenances,
        'font_path': font_url,
    }

    html = template.render(context)
    page_pdf = io.BytesIO()
    HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(page_pdf, stylesheets=[css])

    page_pdf.seek(0)

    # تولید پاسخ PDF
    pdf_merger = PdfWriter()
    pdf_merger.append(page_pdf)
    response = HttpResponse(content_type='application/pdf')

    response['Content-Disposition'] = f'attachment; filename="maintenances.pdf"'

    pdf_merger.write(response)
    return response


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def export_maintenance_excel(request):
    maintenances = Maintenance.objects.all()

    filter_fields = {
        'maintenance_description': 'maintenance_description__icontains',
        'maintenance_start_date': 'maintenance_start_date__gte',
        'maintenance_end_date': 'maintenance_end_date__lte',
        'maintenance_price': 'maintenance_price__icontains',
        'maintenance_status': 'maintenance_status__icontains',
        'service_company': 'service_company__icontains',
        'maintenance_document_no': 'maintenance_document_no__icontains',
        'details': 'details__icontains',
    }

    for field, lookup in filter_fields.items():
        value = request.GET.get(field)
        if value:
            if field in ['maintenance_start_date', 'maintenance_end_date']:
                gregorian_date = parse_jalali_to_gregorian(value)
                if gregorian_date:
                    maintenances = maintenances.filter(**{lookup: gregorian_date})
            else:
                maintenances = maintenances.filter(**{lookup: value.strip()})

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "maintenances"
    ws.sheet_view.rightToLeft = True

    # ✅ Add title
    title_cell = ws.cell(row=1, column=1, value="لیست هزینه های تعمیرات و نگهداری")
    title_cell.font = Font(bold=True, size=18)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=9)

    # ✅ Style setup
    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")  # Gold
    header_font = Font(bold=True, color="000000")  # Black bold text

    headers = ['#', 'شرح کار', 'تاریخ شروع', ' تاریخ پایان', ' اجرت/دستمزد ', 'شرکت خدماتی', 'شماره فاکتور',
               'توضیحات', 'آخرین وضعیت']

    # ✅ Write header (row 2)
    for col_num, column_title in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_num, value=column_title)
        cell.fill = header_fill
        cell.font = header_font

    # ✅ Write data (start from row 3)
    for row_num, maintenance in enumerate(maintenances, start=3):
        ws.cell(row=row_num, column=1, value=row_num - 2)  # index starts from 1
        ws.cell(row=row_num, column=2, value=maintenance.maintenance_description)
        jalali_date = jdatetime.date.fromgregorian(date=maintenance.maintenance_start_date).strftime('%Y/%m/%d')
        ws.cell(row=row_num, column=3, value=jalali_date)
        jalali_date = jdatetime.date.fromgregorian(date=maintenance.maintenance_end_date).strftime('%Y/%m/%d')
        ws.cell(row=row_num, column=4, value=jalali_date)
        ws.cell(row=row_num, column=5, value=maintenance.maintenance_price)
        ws.cell(row=row_num, column=6, value=maintenance.service_company)
        ws.cell(row=row_num, column=7, value=maintenance.maintenance_document_no)
        ws.cell(row=row_num, column=8, value=maintenance.details)
        ws.cell(row=row_num, column=9, value=maintenance.maintenance_status)

    # ✅ Return file
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=maintenances.xlsx'
    wb.save(response)
    return response


# ======================== Charge Views ======================================
@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_charge_view(request):
    user = request.user

    if not user.is_middle_admin:
        return HttpResponseForbidden()

    context = {
        "allowed_methods": user.charge_method_codes
    }

    return render(
        request,
        "middleCharge/add_charge.html",
        context
    )


@method_decorator(middle_admin_required, name='dispatch')
class MiddleFixChargeCreateView(CreateView):
    model = FixCharge
    template_name = 'middleCharge/fix_charge_template.html'
    form_class = FixChargeForm
    success_url = reverse_lazy('middle_add_fixed_charge')

    def form_valid(self, form):
        charge_name = form.cleaned_data.get('name') or 'شارژ ثابت'

        # گرفتن کاربران تحت مدیریت
        managed_users = self.request.user.managed_users.all()

        unit_count = UnifiedCharge.objects.filter(
            user=self.request.user,
            unit__is_active=True
        ).values('unit').distinct().count()
        form.instance.unit_count = unit_count

        units = Unit.objects.filter(
            is_active=True
        ).filter(
            Q(user=self.request.user) | Q(user__in=managed_users)
        ).distinct()

        if not units.exists():
            messages.error(
                self.request,
                'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدها را ثبت کنید.'
            )
            return redirect('middle_manage_unit')

        # ذخیره FixCharge
        fix_charge = form.save(commit=False)
        fix_charge.user = self.request.user
        fix_charge.name = charge_name
        fix_charge.save()

        # انتخاب Calculator
        calculator = CALCULATORS.get(fix_charge.charge_type)
        if not calculator:
            messages.error(self.request, 'نوع شارژ پشتیبانی نمی‌شود')
            return redirect(self.success_url)

        unified_charges = []

        for unit in units:
            # محاسبه مبلغ پایه برای هر واحد
            base_amount = calculator.calculate(unit, fix_charge)

            # مطمئن شدن که فیلدهای عددی عدد هستند
            civil_amount = fix_charge.civil or 0
            other_amount = fix_charge.other_cost_amount or 0
            total_monthly_charge = base_amount + civil_amount + other_amount

            unified_charges.append(
                UnifiedCharge(
                    user=self.request.user,
                    unit=unit,
                    bank=None,
                    amount=base_amount,
                    house=unit.myhouse,
                    charge_type=fix_charge.charge_type,
                    base_charge=total_monthly_charge,
                    main_charge=fix_charge,
                    penalty_percent=fix_charge.payment_penalty_amount,
                    civil=civil_amount,
                    other_cost_amount=other_amount,
                    penalty_amount=0,
                    total_charge_month=total_monthly_charge,
                    details=fix_charge.details or '',
                    title=fix_charge.name,
                    send_notification=False,  # ⛔ اعلان ارسال نشده
                    send_notification_date=None,
                    payment_deadline_date=fix_charge.payment_deadline,
                    content_type=ContentType.objects.get_for_model(FixCharge),
                    object_id=fix_charge.id,
                )
            )

        # ایجاد همه UnifiedCharge ها در دیتابیس یکجا
        UnifiedCharge.objects.bulk_create(unified_charges)

        messages.success(self.request, 'شارژ با موفقیت ثبت گردید.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manager_units = Unit.objects.filter(is_active=True, user=self.request.user)
        managed_units = Unit.objects.filter(is_active=True, user__manager=self.request.user)

        # ترکیب و distinct
        all_units = (manager_units | managed_units).distinct()
        context['unit_count'] = all_units.count()
        context['units'] = all_units

        charges = FixCharge.objects.filter(user=self.request.user).annotate(
            total_units=Count('unified_charges'),  # همه واحدهای مرتبط
            notified_count=Count(
                'unified_charges',
                filter=Q(unified_charges__send_notification=True)
            )
        ).order_by('-created_at')
        context['charges'] = charges
        paginate_by = self.request.GET.get('paginate', '20')

        if paginate_by == '1000':  # نمایش همه
            paginator = Paginator(charges, charges.count() or 20)
        else:
            paginate_by = int(paginate_by)
            paginator = Paginator(charges, paginate_by)

        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['charges'] = page_obj
        context['page_obj'] = page_obj
        context['paginate'] = paginate_by
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_fix_charge_edit(request, pk):
    fix_charge = get_object_or_404(FixCharge, pk=pk, user=request.user)

    # بررسی اینکه برای این شارژ اعلان ارسال شده باشد
    any_notify = UnifiedCharge.objects.filter(
        content_type=ContentType.objects.get_for_model(FixCharge),
        object_id=fix_charge.id,
        send_notification=True
    ).exists()
    if any_notify:
        messages.error(request, 'برای این شارژ اعلان ارسال شده و قابل ویرایش نیست.')
        return redirect('middle_add_fixed_charge')

    if request.method == 'POST':
        form = FixChargeForm(request.POST, request.FILES, instance=fix_charge)
        if form.is_valid():
            with transaction.atomic():
                fix_charge = form.save(commit=False)
                fix_charge.name = fix_charge.name or 'شارژ ثابت'
                fix_charge.save()

                # کاربران و واحدهای تحت مدیریت
                managed_users = request.user.managed_users.all()
                units = Unit.objects.filter(is_active=True, user__in=managed_users)
                if not units.exists():
                    messages.error(request, 'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدها را ثبت کنید.')
                    return redirect('middle_manage_unit')

                # انتخاب Calculator
                calculator = CALCULATORS.get(fix_charge.charge_type)
                if not calculator:
                    messages.error(request, 'نوع شارژ پشتیبانی نمی‌شود.')
                    return redirect('middle_add_fixed_charge')

                unified_charges = []

                for unit in units:
                    # محاسبه مبلغ پایه برای هر واحد
                    base_amount = calculator.calculate(unit, fix_charge)
                    civil_amount = fix_charge.civil or 0
                    other_amount = fix_charge.other_cost_amount or 0
                    total_monthly = base_amount + civil_amount + other_amount

                    # آپدیت یا ایجاد UnifiedCharge برای این واحد
                    UnifiedCharge.objects.update_or_create(
                        user=request.user,
                        unit=unit,
                        content_type=ContentType.objects.get_for_model(FixCharge),
                        object_id=fix_charge.id,
                        defaults={
                            'bank': None,
                            'charge_type': fix_charge.charge_type,
                            'amount': base_amount,
                            'main_charge': fix_charge,
                            'base_charge': total_monthly,
                            'penalty_percent': fix_charge.payment_penalty_amount or 0,
                            'civil': civil_amount,
                            'other_cost_amount': other_amount,
                            'penalty_amount': 0,
                            'total_charge_month': total_monthly,
                            'details': fix_charge.details or '',
                            'title': fix_charge.name,
                            'send_notification': False,
                            'send_notification_date': None,
                            'payment_deadline_date': fix_charge.payment_deadline,
                        }
                    )

                messages.success(request, 'شارژ با موفقیت ویرایش شد.')
                return redirect('middle_add_fixed_charge')
        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
    else:
        form = FixChargeForm(instance=fix_charge)

    return render(request, 'middleCharge/fix_charge_template.html', {'form': form, 'charge': fix_charge})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_fix_charge_delete(request, pk):
    charge = get_object_or_404(FixCharge, id=pk, user=request.user)

    content_type = ContentType.objects.get_for_model(FixCharge)

    # بررسی اینکه هیچ رکورد UnifiedCharge با is_paid=True وجود نداشته باشد
    if UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            is_paid=True
    ).exists():
        messages.error(request, "امکان حذف شارژ وجود ندارد چون پرداخت شارژ توسط واحد ثبت شده است.")
        return redirect(reverse('middle_add_fixed_charge'))

    # چک کردن وجود رکوردهایی که send_notification == True هستند
    if UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            send_notification=True
    ).exists():
        messages.error(request, "برای این شارژ اطلاعیه صادر شده است. ابتدا اطلاعیه شارژ را حذف و مجدداً تلاش نمایید!")
        return redirect(reverse('middle_add_fixed_charge'))

    try:
        charge.delete()
        messages.success(request, f'{charge.name} با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, "امکان حذف این شارژ به دلیل وابستگی وجود ندارد!")

    return redirect(reverse('middle_add_fixed_charge'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_fix_charge_notification_view(request, pk):
    charge = get_object_or_404(FixCharge, id=pk, user=request.user)

    # واحدهای تحت مدیریت یا متعلق به خود کاربر
    manager_units = Unit.objects.filter(is_active=True, user=request.user)
    managed_units = Unit.objects.filter(is_active=True, user__manager=request.user)
    units = (manager_units | managed_units).distinct().order_by('unit')

    # -----------------------------
    # ساخت UnifiedCharge فقط برای واحدهای جدید
    # -----------------------------
    content_type = ContentType.objects.get_for_model(FixCharge)

    # واحدهایی که قبلاً شارژ برایشان ایجاد شده
    existing_uc_unit_ids = UnifiedCharge.objects.filter(
        content_type=content_type,
        object_id=charge.id,
        unit__in=units
    ).values_list('unit_id', flat=True)

    new_units = units.exclude(id__in=existing_uc_unit_ids)

    # ایجاد UnifiedCharge برای واحدهای جدید
    calculator = CALCULATORS.get(charge.charge_type)

    with transaction.atomic():
        for unit in new_units:
            base_amount = calculator.calculate(unit, charge)
            civil_amount = charge.civil or 0
            other_amount = charge.other_cost_amount or 0
            total_monthly_charge = base_amount + civil_amount + other_amount

            UnifiedCharge.objects.create(
                user=request.user,
                unit=unit,
                house=unit.myhouse,
                bank=None,
                amount=base_amount,
                charge_type=charge.charge_type,
                base_charge=total_monthly_charge,
                main_charge=charge,
                penalty_percent=charge.payment_penalty_amount,
                civil=civil_amount,
                other_cost_amount=other_amount,
                penalty_amount=0,
                total_charge_month=total_monthly_charge,
                details=charge.details or '',
                title=charge.name,
                send_notification=False,
                send_notification_date=None,
                payment_deadline_date=charge.payment_deadline,
                content_type=content_type,
                object_id=charge.id,
            )

    # -----------------------------
    # فیلتر جستجو
    # -----------------------------
    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    # -----------------------------
    # Pagination
    # -----------------------------
    per_page = int(request.GET.get('per_page', 30))
    paginator = Paginator(units, per_page)
    page_units = paginator.get_page(request.GET.get('page'))

    # -----------------------------
    # POST: ارسال اعلان یا پیامک
    # -----------------------------
    if request.method == 'POST':
        send_type = request.POST.get('send_type', 'notify')
        selected_units = request.POST.getlist('units')

        if not selected_units:
            messages.warning(request, 'هیچ واحدی انتخاب نشده است')
            return redirect(request.path)

        qs = UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            unit_id__in=selected_units
        ).select_related('unit', 'unit__user')

        if not qs.exists():
            messages.info(request, 'اطلاعیه جدیدی برای ارسال وجود ندارد')
            return redirect(request.path)

        with transaction.atomic():
            # ثبت اعلان سیستمی
            qs.update(
                send_notification=True,
                send_notification_date=timezone.now().date()
            )

            if send_type == 'sms':
                result = SmsService.send_for_unified_charges(
                    user=request.user,
                    unified_charges=qs,
                    meta_callback=lambda total_sms, total_price: qs.update(
                        send_sms=True,
                        send_sms_date=timezone.now().date(),
                        sms_count=total_sms,
                        sms_price=Decimal(settings.SMS_PRICE),
                        sms_total_price=total_price
                    )
                )

                if result.success:
                    messages.success(
                        request,
                        f'اطلاعیه سیستمی و پیامکی برای {qs.count()} واحد ارسال شد'
                    )
                else:
                    messages.error(request, result.message)

            else:
                messages.success(request, f'اطلاعیه سیستمی برای {qs.count()} واحد ثبت شد')

        return redirect(request.path)

    # -----------------------------
    # GET: آماده‌سازی داده‌ها برای قالب
    # -----------------------------
    uc_map = UnifiedCharge.objects.filter(
        content_type=content_type,
        object_id=charge.id,
        unit__in=page_units
    ).select_related('unit', 'unit__user', 'bank')

    uc_dict = {uc.unit_id: uc for uc in uc_map}

    # page_units → Page object اصلی از Paginator
    for i, unit in enumerate(page_units):
        uc = uc_dict.get(unit.id)
        renter = unit.renters.filter(renter_is_active=True).first()
        page_units.object_list[i] = {
            'unit': unit,
            'renter': renter,
            'is_paid': uc.is_paid if uc else False,
            'is_notified': uc.send_notification if uc else False,
            'send_sms': uc.send_sms if uc else False,
            'sms_date': uc.send_sms_date if uc else None,
            'total_charge': uc.total_charge_month if uc else 0,
        }

    return render(request, 'middleCharge/notify_fix_charge_template.html', {
        'charge': charge,
        'page_obj': page_units,  # ← حالا Page object واقعی است
    })


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_remove_send_notification_fix(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'فقط درخواست‌های POST مجاز است.'}, status=400)

    charge = get_object_or_404(FixCharge, id=pk, user=request.user)
    selected_units = request.POST.getlist('units[]')

    if not selected_units:
        return JsonResponse({'warning': 'هیچ واحدی انتخاب نشده است.'})

    try:
        with transaction.atomic():
            content_type = ContentType.objects.get_for_model(FixCharge)

            # رکوردهایی که باید غیرفعال شوند
            if selected_units == ['all']:
                qs = UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    is_paid=False,
                    send_notification=True,
                    send_sms=True
                )
            else:
                try:
                    selected_unit_ids = [int(uid) for uid in selected_units]
                except ValueError:
                    return JsonResponse({'error': 'شناسه واحد نامعتبر است.'}, status=400)

                qs = UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    unit_id__in=selected_unit_ids,
                    is_paid=False,
                    send_notification=True,  # فقط رکوردهای فعال

                )

            updated_count = qs.update(
                send_notification=False,
                send_notification_date=None,
                send_sms=False,
                send_sms_date=None
            )

            # اگر هیچ رکوردی با send_notification=True باقی نماند → شارژ را غیرفعال کن
            if not UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    send_notification=True
            ).exists():
                charge.send_notification = False
                charge.save()

        if updated_count:
            return JsonResponse({'success': f'{updated_count} اطلاعیه غیرفعال شد.'})
        else:
            return JsonResponse({'info': 'رکوردی برای غیرفعال کردن یافت نشد.'})

    except Exception as e:
        return JsonResponse({'error': f'خطایی هنگام غیرفعال کردن اطلاعیه‌ها رخ داد: {str(e)}'}, status=500)


# ========================================== Area Charge =======================
@method_decorator(middle_admin_required, name='dispatch')
class MiddleAreaChargeCreateView(CreateView):
    model = AreaCharge
    template_name = 'middleCharge/area_charge_template.html'
    form_class = AreaChargeForm
    success_url = reverse_lazy('middle_add_area_charge')

    def form_valid(self, form):
        charge_name = form.cleaned_data.get('name')

        # گرفتن کاربران تحت مدیریت
        managed_users = self.request.user.managed_users.all()

        unit_count = UnifiedCharge.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            unit__is_active=True
        ).values('unit').distinct().count()
        form.instance.unit_count = unit_count

        units = Unit.objects.filter(
            is_active=True
        ).filter(
            Q(user=self.request.user) | Q(user__in=managed_users)
        ).distinct()

        total_area = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).aggregate(total=Sum('area'))['total'] or 0
        form.instance.total_area = total_area

        if not units.exists():
            messages.error(
                self.request,
                'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدها را ثبت کنید.'
            )
            return redirect('middle_manage_unit')

        # ذخیره FixCharge
        area_charge = form.save(commit=False)
        area_charge.user = self.request.user
        area_charge.name = charge_name
        area_charge.save()

        # انتخاب Calculator
        calculator = CALCULATORS.get(area_charge.charge_type)
        if not calculator:
            messages.error(self.request, 'نوع شارژ پشتیبانی نمی‌شود')
            return redirect(self.success_url)

        unified_charges = []

        for unit in units:
            # محاسبه مبلغ پایه برای هر واحد
            base_amount = calculator.calculate(unit, area_charge)

            # مطمئن شدن که فیلدهای عددی عدد هستند
            civil_amount = area_charge.civil or 0
            other_amount = area_charge.other_cost_amount or 0
            total_monthly_charge = base_amount + civil_amount + other_amount

            unified_charges.append(
                UnifiedCharge(
                    user=self.request.user,
                    unit=unit,
                    bank=None,
                    house=unit.myhouse,
                    main_charge=area_charge,
                    charge_type=area_charge.charge_type,
                    amount=base_amount,
                    base_charge=total_monthly_charge,
                    penalty_percent=area_charge.payment_penalty_amount,
                    civil=civil_amount,
                    other_cost_amount=other_amount,
                    penalty_amount=0,
                    total_charge_month=total_monthly_charge,
                    details=area_charge.details or '',
                    title=area_charge.name,
                    send_notification=False,  # ⛔ اعلان ارسال نشده
                    send_notification_date=None,
                    payment_deadline_date=area_charge.payment_deadline,
                    content_type=ContentType.objects.get_for_model(AreaCharge),
                    object_id=area_charge.id,
                )
            )

        # ایجاد همه UnifiedCharge ها در دیتابیس یکجا
        UnifiedCharge.objects.bulk_create(unified_charges)

        messages.success(self.request, 'شارژ با موفقیت ثبت گردید.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        managed_users = self.request.user.managed_users.all()
        unit_count = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).count()

        context['unit_count'] = unit_count
        print(unit_count)

        total_area = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).aggregate(total=Sum('area'))['total'] or 0
        context['total_area'] = total_area

        charges = AreaCharge.objects.filter(user=self.request.user).annotate(
            total_units=Count('unified_charges'),  # همه واحدهای مرتبط
            notified_count=Count(
                'unified_charges',
                filter=Q(unified_charges__send_notification=True)
            )
        ).order_by('-created_at')
        context['charges'] = charges
        paginate_by = self.request.GET.get('paginate', '20')

        if paginate_by == '1000':  # نمایش همه
            paginator = Paginator(charges, charges.count() or 20)
        else:
            paginate_by = int(paginate_by)
            paginator = Paginator(charges, paginate_by)

        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['charges'] = page_obj
        context['page_obj'] = page_obj
        context['paginate'] = paginate_by

        context.update({
            'unit_count': unit_count,
            'total_area': total_area,
            # 'total_people': total_people,
            'charges': charges,
        })
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_area_charge_edit(request, pk):
    charge = get_object_or_404(AreaCharge, pk=pk, user=request.user)

    # بررسی اینکه برای این شارژ اعلان ارسال شده باشد
    any_notify = UnifiedCharge.objects.filter(
        content_type=ContentType.objects.get_for_model(AreaCharge),
        object_id=charge.id,
        send_notification=True
    ).exists()
    if any_notify:
        messages.error(request, 'برای این شارژ اعلان ارسال شده و قابل ویرایش نیست.')
        return redirect('middle_add_area_charge')

    if request.method == 'POST':
        form = AreaChargeForm(request.POST, request.FILES, instance=charge)
        if form.is_valid():
            with transaction.atomic():
                charge = form.save(commit=False)
                charge.name = charge.name or 'شارژ ثابت'
                charge.save()

                # کاربران و واحدهای تحت مدیریت
                managed_users = request.user.managed_users.all()
                units = Unit.objects.filter(
                    Q(user=request.user) | Q(user__in=managed_users),
                    is_active=True)
                if not units.exists():
                    messages.error(request, 'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدها را ثبت کنید.')
                    return redirect('middle_manage_unit')

                # انتخاب Calculator
                calculator = CALCULATORS.get(charge.charge_type)
                if not calculator:
                    messages.error(request, 'نوع شارژ پشتیبانی نمی‌شود.')
                    return redirect('middle_add_fixed_charge')

                unified_charges = []

                for unit in units:
                    # محاسبه مبلغ پایه برای هر واحد
                    base_amount = calculator.calculate(unit, charge)
                    civil_amount = charge.civil or 0
                    other_amount = charge.other_cost_amount or 0
                    total_monthly = base_amount + civil_amount + other_amount

                    # آپدیت یا ایجاد UnifiedCharge برای این واحد
                    UnifiedCharge.objects.update_or_create(
                        user=request.user,
                        unit=unit,
                        content_type=ContentType.objects.get_for_model(AreaCharge),
                        object_id=charge.id,
                        defaults={
                            'bank': None,
                            'charge_type': charge.charge_type,
                            'fix_amount': 0,
                            'amount': base_amount,
                            'main_charge': charge,
                            'base_charge': total_monthly,
                            'charge_by_person_amount': 0,
                            'charge_by_area_amount': charge.area_amount,
                            'fix_person_variable_amount': 0,
                            'fix_area_variable_amount': 0,
                            'penalty_percent': charge.payment_penalty_amount or 0,
                            'civil': civil_amount,
                            'other_cost_amount': other_amount,
                            'penalty_amount': 0,
                            'total_charge_month': total_monthly,
                            'details': charge.details or '',
                            'title': charge.name,
                            'send_notification': False,
                            'send_notification_date': None,
                            'payment_deadline_date': charge.payment_deadline,
                        }
                    )

                messages.success(request, 'شارژ با موفقیت ویرایش شد.')
                return redirect('middle_add_area_charge')
        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
    else:
        form = FixChargeForm(instance=charge)

    return render(request, 'middleCharge/area_charge_template.html', {'form': form, 'charge': charge})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_area_charge_delete(request, pk):
    charge = get_object_or_404(AreaCharge, id=pk, user=request.user)

    content_type = ContentType.objects.get_for_model(AreaCharge)

    # بررسی اینکه هیچ رکورد UnifiedCharge با is_paid=True وجود نداشته باشد
    if UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            is_paid=True
    ).exists():
        messages.error(request, "امکان حذف شارژ وجود ندارد چون پرداخت شارژ توسط واحد ثبت شده است.")
        return redirect(reverse('middle_add_area_charge'))

    # چک کردن وجود رکوردهایی که send_notification == True هستند
    if UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            send_notification=True
    ).exists():
        messages.error(request, "برای این شارژ اطلاعیه صادر شده است. ابتدا اطلاعیه شارژ را حذف و مجدداً تلاش نمایید!")
        return redirect(reverse('middle_add_area_charge'))

    try:
        charge.delete()
        messages.success(request, f'{charge.name} با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, "امکان حذف این شارژ به دلیل وابستگی وجود ندارد!")

    return redirect(reverse('middle_add_area_charge'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_area_charge_notification_view(request, pk):
    charge = get_object_or_404(AreaCharge, id=pk, user=request.user)
    content_type = ContentType.objects.get_for_model(AreaCharge)

    # ------------------ واحدها ------------------
    units = Unit.objects.filter(
        is_active=True
    ).filter(
        Q(user=request.user) | Q(user__manager=request.user)
    ).distinct().order_by('unit')

    # ------------------ ساخت UnifiedCharge ------------------
    existing_ids = UnifiedCharge.objects.filter(
        content_type=content_type,
        object_id=charge.id
    ).values_list('unit_id', flat=True)

    new_units = units.exclude(id__in=existing_ids)

    calculator = CALCULATORS.get(charge.charge_type)

    with transaction.atomic():
        for unit in new_units:
            base = calculator.calculate(unit, charge)
            civil = charge.civil or 0
            other = charge.other_cost_amount or 0
            total = base + civil + other

            UnifiedCharge.objects.create(
                user=request.user,
                unit=unit,
                amount=base,
                house=unit.myhouse,
                base_charge=total,
                total_charge_month=total,
                title=charge.name,
                main_charge=charge,
                charge_type=charge.charge_type,
                penalty_percent=charge.payment_penalty_amount,
                civil=civil,
                other_cost_amount=other,
                payment_deadline_date=charge.payment_deadline,
                content_type=content_type,
                object_id=charge.id,
            )

    # ------------------ جستجو ------------------
    q = request.GET.get('search', '').strip()
    if q:
        units = units.filter(
            Q(unit__icontains=q) |
            Q(owner_name__icontains=q) |
            Q(renters__renter_name__icontains=q)
        ).distinct()

    # ------------------ pagination ------------------
    try:
        per_page = int(request.GET.get('per_page', 30))
    except ValueError:
        per_page = 30

    paginator = Paginator(units, per_page)
    page_units = paginator.get_page(request.GET.get('page'))

    # ------------------ POST ------------------
    if request.method == "POST":

        send_type = request.POST.get("send_type", "notify")
        selected = request.POST.getlist("units")

        if not selected:
            messages.warning(request, 'هیچ واحدی انتخاب نشده')
            return redirect(request.path)

        qs = UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            unit_id__in=selected
        ).select_related("unit")

        if not qs.exists():
            messages.info(request, 'اطلاعیه‌ای برای ارسال وجود ندارد')
            return redirect(request.path)

        # ثبت اعلان سیستمی
        qs.update(
            send_notification=True,
            send_notification_date=timezone.now().date()
        )

        # ---------- ارسال SMS ----------
        if send_type == "sms":

            result = SmsService.send_for_unified_charges(
                user=request.user,
                unified_charges=qs,
                meta_callback=lambda total_sms, total_price: qs.update(
                    send_sms=True,
                    send_sms_date=timezone.now().date(),
                    sms_count=total_sms,
                    sms_price=Decimal(settings.SMS_PRICE),
                    sms_total_price=total_price
                )
            )

            if result.success:
                messages.success(
                    request,
                    f'اطلاعیه سیستمی و پیامکی برای {qs.count()} واحد ارسال شد'
                )
            else:
                messages.error(request, result.message)

        else:
            messages.success(
                request,
                f'اطلاعیه سیستمی برای {qs.count()} واحد ثبت شد'
            )

        return redirect(request.path)

    # ------------------ آماده‌سازی template ------------------
    uc_map = {
        uc.unit_id: uc
        for uc in UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            unit__in=page_units
        )
    }

    # دیگه نیازی به uc_dict نیست
    for i, unit in enumerate(page_units):
        uc = uc_map.get(unit.id)  # ← همینجا درست شد
        renter = unit.renters.filter(renter_is_active=True).first()
        page_units.object_list[i] = {
            'unit': unit,
            'renter': renter,
            'is_paid': uc.is_paid if uc else False,
            'is_notified': uc.send_notification if uc else False,
            'send_sms': uc.send_sms if uc else False,
            'sms_date': uc.send_sms_date if uc else None,
            'total_charge': uc.total_charge_month if uc else 0,
        }

    return render(request, 'middleCharge/notify_area_charge_template.html', {
        "charge": charge,
        "page_obj": page_units,
        # "paginator": paginator,
    })


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_remove_send_notification_area(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'فقط درخواست‌های POST مجاز است.'}, status=400)

    charge = get_object_or_404(AreaCharge, id=pk, user=request.user)
    selected_units = request.POST.getlist('units[]')

    if not selected_units:
        return JsonResponse({'warning': 'هیچ واحدی انتخاب نشده است.'})

    try:
        with transaction.atomic():
            content_type = ContentType.objects.get_for_model(AreaCharge)

            # رکوردهایی که باید غیرفعال شوند
            if selected_units == ['all']:
                qs = UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    is_paid=False,
                    send_notification=True  # فقط رکوردهای فعال
                )
            else:
                try:
                    selected_unit_ids = [int(uid) for uid in selected_units]
                except ValueError:
                    return JsonResponse({'error': 'شناسه واحد نامعتبر است.'}, status=400)

                qs = UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    unit_id__in=selected_unit_ids,
                    is_paid=False,
                    send_notification=True  # فقط رکوردهای فعال
                )

            updated_count = qs.update(
                send_notification=False,
                send_notification_date=None
            )

            # اگر هیچ رکوردی با send_notification=True باقی نماند → شارژ را غیرفعال کن
            if not UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    send_notification=True
            ).exists():
                charge.send_notification = False
                charge.save()

        if updated_count:
            return JsonResponse({'success': f'{updated_count} اطلاعیه غیرفعال شد.'})
        else:
            return JsonResponse({'info': 'رکوردی برای غیرفعال کردن یافت نشد.'})

    except Exception as e:
        return JsonResponse({'error': f'خطایی هنگام غیرفعال کردن اطلاعیه‌ها رخ داد: {str(e)}'}, status=500)


# ======================= Person Charge ===============
@method_decorator(middle_admin_required, name='dispatch')
class MiddlePersonChargeCreateView(CreateView):
    model = PersonCharge
    template_name = 'middleCharge/person_charge_template.html'
    form_class = PersonChargeForm
    success_url = reverse_lazy('middle_add_person_charge')

    def form_valid(self, form):
        charge_name = form.cleaned_data.get('name')

        # گرفتن کاربران تحت مدیریت
        managed_users = self.request.user.managed_users.all()

        unit_count = UnifiedCharge.objects.filter(
            user=self.request.user,
            unit__is_active=True
        ).values('unit').distinct().count()
        form.instance.unit_count = unit_count

        units = Unit.objects.filter(
            is_active=True
        ).filter(
            Q(user=self.request.user) | Q(user__in=managed_users)
        ).distinct()

        total_people = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).aggregate(total=Sum('people_count'))['total'] or 0
        form.instance.total_people = total_people

        if not units.exists():
            messages.error(
                self.request,
                'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدها را ثبت کنید.'
            )
            return redirect('middle_manage_unit')

        # ذخیره FixCharge
        person_charge = form.save(commit=False)
        person_charge.user = self.request.user
        person_charge.name = charge_name
        person_charge.save()

        # انتخاب Calculator
        calculator = CALCULATORS.get(person_charge.charge_type)
        if not calculator:
            messages.error(self.request, 'نوع شارژ پشتیبانی نمی‌شود')
            return redirect(self.success_url)

        unified_charges = []

        for unit in units:
            # محاسبه مبلغ پایه برای هر واحد
            base_amount = calculator.calculate(unit, person_charge)

            # مطمئن شدن که فیلدهای عددی عدد هستند
            civil_amount = person_charge.civil or 0
            other_amount = person_charge.other_cost_amount or 0
            total_monthly_charge = base_amount + civil_amount + other_amount

            unified_charges.append(
                UnifiedCharge(
                    user=self.request.user,
                    unit=unit,
                    bank=None,
                    house=unit.myhouse,
                    charge_type=person_charge.charge_type,
                    amount=base_amount,
                    base_charge=total_monthly_charge,
                    main_charge=person_charge,
                    penalty_percent=person_charge.payment_penalty_amount,
                    civil=civil_amount,
                    other_cost_amount=other_amount,
                    penalty_amount=0,
                    total_charge_month=total_monthly_charge,
                    details=person_charge.details or '',
                    title=person_charge.name,
                    send_notification=False,  # ⛔ اعلان ارسال نشده
                    send_notification_date=None,
                    payment_deadline_date=person_charge.payment_deadline,
                    content_type=ContentType.objects.get_for_model(PersonCharge),
                    object_id=person_charge.id,
                )
            )

        # ایجاد همه UnifiedCharge ها در دیتابیس یکجا
        UnifiedCharge.objects.bulk_create(unified_charges)

        messages.success(self.request, 'شارژ با موفقیت ثبت گردید.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        managed_users = self.request.user.managed_users.all()
        unit_count = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).count()
        context['unit_count'] = unit_count
        total_people = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).aggregate(
            total=Sum('people_count'))['total'] or 0
        context['total_people'] = total_people

        charges = PersonCharge.objects.filter(user=self.request.user).annotate(
            notified_count=Count(
                'unified_charges',
                filter=Q(unified_charges__send_notification=True)
            ),
            total_units=Count('unified_charges')
        ).order_by('-created_at')
        context['charges'] = charges
        paginate_by = self.request.GET.get('paginate', '20')

        if paginate_by == '1000':  # نمایش همه
            paginator = Paginator(charges, charges.count() or 20)
        else:
            paginate_by = int(paginate_by)
            paginator = Paginator(charges, paginate_by)

        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['charges'] = page_obj
        context['page_obj'] = page_obj
        context['paginate'] = paginate_by

        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_person_charge_edit(request, pk):
    charge = get_object_or_404(PersonCharge, pk=pk, user=request.user)

    # بررسی اینکه برای این شارژ اعلان ارسال شده باشد
    any_notify = UnifiedCharge.objects.filter(
        content_type=ContentType.objects.get_for_model(PersonCharge),
        object_id=charge.id,
        send_notification=True
    ).exists()
    if any_notify:
        messages.error(request, 'برای این شارژ اعلان ارسال شده و قابل ویرایش نیست.')
        return redirect('middle_add_person_charge')

    if request.method == 'POST':
        form = PersonChargeForm(request.POST, request.FILES, instance=charge)
        if form.is_valid():
            with transaction.atomic():
                charge = form.save(commit=False)
                charge.name = charge.name or 'شارژ ثابت'
                charge.save()

                # کاربران و واحدهای تحت مدیریت
                managed_users = request.user.managed_users.all()
                units = Unit.objects.filter(is_active=True, user__in=managed_users)
                if not units.exists():
                    messages.error(request, 'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدها را ثبت کنید.')
                    return redirect('middle_manage_unit')

                # انتخاب Calculator
                calculator = CALCULATORS.get(charge.charge_type)
                if not calculator:
                    messages.error(request, 'نوع شارژ پشتیبانی نمی‌شود.')
                    return redirect('middle_add_person_charge')

                unified_charges = []

                for unit in units:
                    # محاسبه مبلغ پایه برای هر واحد
                    base_amount = calculator.calculate(unit, charge)
                    civil_amount = charge.civil or 0
                    other_amount = charge.other_cost_amount or 0
                    total_monthly = base_amount + civil_amount + other_amount

                    # آپدیت یا ایجاد UnifiedCharge برای این واحد
                    UnifiedCharge.objects.update_or_create(
                        user=request.user,
                        unit=unit,
                        content_type=ContentType.objects.get_for_model(PersonCharge),
                        object_id=charge.id,
                        defaults={
                            'bank': None,
                            'charge_type': charge.charge_type,
                            'amount': base_amount,
                            'base_charge': total_monthly,
                            'main-charge': charge,
                            'penalty_percent': charge.payment_penalty_amount or 0,
                            'civil': civil_amount,
                            'other_cost_amount': other_amount,
                            'penalty_amount': 0,
                            'total_charge_month': total_monthly,
                            'details': charge.details or '',
                            'title': charge.name,
                            'send_notification': False,
                            'send_notification_date': None,
                            'payment_deadline_date': charge.payment_deadline,
                        }
                    )

                messages.success(request, 'شارژ با موفقیت ویرایش شد.')
                return redirect('middle_add_person_charge')
        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
    else:
        form = FixChargeForm(instance=charge)

    return render(request, 'middleCharge/person_charge_template.html', {'form': form, 'charge': charge})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_person_charge_delete(request, pk):
    charge = get_object_or_404(PersonCharge, id=pk, user=request.user)

    content_type = ContentType.objects.get_for_model(PersonCharge)

    # بررسی اینکه هیچ رکورد UnifiedCharge با is_paid=True وجود نداشته باشد
    if UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            is_paid=True
    ).exists():
        messages.error(request, "امکان حذف شارژ وجود ندارد چون پرداخت شارژ توسط واحد ثبت شده است.")
        return redirect(reverse('middle_add_person_charge'))

    # چک کردن وجود رکوردهایی که send_notification == True هستند
    if UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            send_notification=True
    ).exists():
        messages.error(request, "برای این شارژ اطلاعیه صادر شده است. ابتدا اطلاعیه شارژ را حذف و مجدداً تلاش نمایید!")
        return redirect(reverse('middle_add_person_charge'))

    try:
        charge.delete()
        messages.success(request, f'{charge.name} با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, "امکان حذف این شارژ به دلیل وابستگی وجود ندارد!")

    return redirect(reverse('middle_add_person_charge'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_person_charge_notification_view(request, pk):
    charge = get_object_or_404(PersonCharge, id=pk, user=request.user)
    content_type = ContentType.objects.get_for_model(PersonCharge)

    # ------------------ واحدها ------------------
    units = Unit.objects.filter(
        is_active=True
    ).filter(
        Q(user=request.user) | Q(user__manager=request.user)
    ).distinct().order_by('unit')

    # ------------------ ساخت UnifiedCharge ------------------
    existing_ids = UnifiedCharge.objects.filter(
        content_type=content_type,
        object_id=charge.id
    ).values_list('unit_id', flat=True)

    new_units = units.exclude(id__in=existing_ids)

    calculator = CALCULATORS.get(charge.charge_type)

    with transaction.atomic():
        for unit in new_units:
            base = calculator.calculate(unit, charge)
            civil = charge.civil or 0
            other = charge.other_cost_amount or 0
            total = base + civil + other

            UnifiedCharge.objects.create(
                user=request.user,
                unit=unit,
                amount=base,
                base_charge=total,
                house=unit.myhouse,
                total_charge_month=total,
                title=charge.name,
                main_charge=charge,
                charge_type=charge.charge_type,
                penalty_percent=charge.payment_penalty_amount,
                civil=civil,
                other_cost_amount=other,
                payment_deadline_date=charge.payment_deadline,
                content_type=content_type,
                object_id=charge.id,
            )

    # ------------------ جستجو ------------------
    q = request.GET.get('search', '').strip()
    if q:
        units = units.filter(
            Q(unit__icontains=q) |
            Q(owner_name__icontains=q) |
            Q(renters__renter_name__icontains=q)
        ).distinct()

    # ------------------ Pagination ------------------
    try:
        per_page = int(request.GET.get('per_page', 30))
    except ValueError:
        per_page = 30

    paginator = Paginator(units, per_page)
    page_units = paginator.get_page(request.GET.get('page'))

    # ------------------ POST: ارسال اطلاعیه یا پیامک ------------------
    if request.method == "POST":
        send_type = request.POST.get("send_type", "notify")
        selected = request.POST.getlist("units")

        if not selected:
            messages.warning(request, "هیچ واحدی انتخاب نشده")
            return redirect(request.path)

        qs = UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            unit_id__in=selected
        ).select_related("unit")

        if not qs.exists():
            messages.info(request, "اطلاعیه‌ای برای ارسال وجود ندارد")
            return redirect(request.path)

        # ثبت اطلاعیه سیستمی
        qs.update(
            send_notification=True,
            send_notification_date=timezone.now().date()
        )

        # ---------- ارسال پیامک ----------
        if send_type == "sms":
            result = SmsService.send_for_unified_charges(
                user=request.user,
                unified_charges=qs,
                meta_callback=lambda total_sms, total_price: qs.update(
                    send_sms=True,
                    send_sms_date=timezone.now().date(),
                    sms_count=total_sms,
                    sms_price=Decimal(settings.SMS_PRICE),
                    sms_total_price=total_price
                )
            )

            if result.success:
                messages.success(
                    request,
                    f"اطلاعیه سیستمی و پیامکی برای {qs.count()} واحد ارسال شد"
                )
            else:
                messages.error(request, result.message)

        else:
            messages.success(
                request,
                f"اطلاعیه سیستمی برای {qs.count()} واحد ثبت شد"
            )

        return redirect(request.path)

    # ------------------ آماده‌سازی داده‌ها برای قالب ------------------
    uc_map = {
        uc.unit_id: uc
        for uc in UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            unit__in=page_units
        )
    }

    # دیگه نیازی به uc_dict نیست
    for i, unit in enumerate(page_units):
        uc = uc_map.get(unit.id)  # ← همینجا درست شد
        renter = unit.renters.filter(renter_is_active=True).first()
        page_units.object_list[i] = {
            'unit': unit,
            'renter': renter,
            'is_paid': uc.is_paid if uc else False,
            'is_notified': uc.send_notification if uc else False,
            'send_sms': uc.send_sms if uc else False,
            'sms_date': uc.send_sms_date if uc else None,
            'total_charge': uc.total_charge_month if uc else 0,
        }

    return render(request, "middleCharge/notify_person_charge_template.html", {
        "charge": charge,
        "page_obj": page_units,
        # "paginator": paginator,
    })


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_remove_send_notification_person(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'فقط درخواست‌های POST مجاز است.'}, status=400)

    charge = get_object_or_404(PersonCharge, id=pk, user=request.user)
    selected_units = request.POST.getlist('units[]')

    if not selected_units:
        return JsonResponse({'warning': 'هیچ واحدی انتخاب نشده است.'})

    try:
        with transaction.atomic():
            content_type = ContentType.objects.get_for_model(PersonCharge)

            # رکوردهایی که باید غیرفعال شوند
            if selected_units == ['all']:
                qs = UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    is_paid=False,
                    send_notification=True  # فقط رکوردهای فعال
                )
            else:
                try:
                    selected_unit_ids = [int(uid) for uid in selected_units]
                except ValueError:
                    return JsonResponse({'error': 'شناسه واحد نامعتبر است.'}, status=400)

                qs = UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    unit_id__in=selected_unit_ids,
                    is_paid=False,
                    send_notification=True  # فقط رکوردهای فعال
                )

            updated_count = qs.update(
                send_notification=False,
                send_notification_date=None
            )

            # اگر هیچ رکوردی با send_notification=True باقی نماند → شارژ را غیرفعال کن
            if not UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    send_notification=True
            ).exists():
                charge.send_notification = False
                charge.save()

        if updated_count:
            return JsonResponse({'success': f'{updated_count} اطلاعیه غیرفعال شد.'})
        else:
            return JsonResponse({'info': 'رکوردی برای غیرفعال کردن یافت نشد.'})

    except Exception as e:
        return JsonResponse({'error': f'خطایی هنگام غیرفعال کردن اطلاعیه‌ها رخ داد: {str(e)}'}, status=500)


# ==================== Fix Area Charge    =============================
@method_decorator(middle_admin_required, name='dispatch')
class MiddleFixAreaChargeCreateView(CreateView):
    model = FixAreaCharge
    template_name = 'middleCharge/fix_area_charge_template.html'
    form_class = FixAreaChargeForm
    success_url = reverse_lazy('middle_add_fix_area_charge')

    def form_valid(self, form):
        charge_name = form.cleaned_data.get('name')

        # گرفتن کاربران تحت مدیریت
        managed_users = self.request.user.managed_users.all()

        unit_count = UnifiedCharge.objects.filter(
            user=self.request.user,
            unit__is_active=True
        ).values('unit').distinct().count()
        form.instance.unit_count = unit_count

        units = Unit.objects.filter(
            is_active=True
        ).filter(
            Q(user=self.request.user) | Q(user__in=managed_users)
        ).distinct()
        total_area = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).aggregate(total=Sum('area'))['total'] or 0
        form.instance.total_area = total_area

        total_people = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).aggregate(total=Sum('people_count'))['total'] or 0
        form.instance.total_people = total_people

        if not units.exists():
            messages.error(
                self.request,
                'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدها را ثبت کنید.'
            )
            return redirect('middle_manage_unit')

        # ذخیره FixCharge
        fix_area_charge = form.save(commit=False)
        fix_area_charge.user = self.request.user
        fix_area_charge.name = charge_name
        fix_area_charge.save()

        # انتخاب Calculator
        calculator = CALCULATORS.get(fix_area_charge.charge_type)
        if not calculator:
            messages.error(self.request, 'نوع شارژ پشتیبانی نمی‌شود')
            return redirect(self.success_url)

        unified_charges = []

        for unit in units:
            # محاسبه مبلغ پایه برای هر واحد
            base_amount = calculator.calculate(unit, fix_area_charge)

            # مطمئن شدن که فیلدهای عددی عدد هستند
            civil_amount = fix_area_charge.civil or 0
            other_amount = fix_area_charge.other_cost_amount or 0
            total_monthly_charge = base_amount + civil_amount + other_amount

            unified_charges.append(
                UnifiedCharge(
                    user=self.request.user,
                    unit=unit,
                    bank=None,
                    house=unit.myhouse,
                    charge_type=fix_area_charge.charge_type,
                    main_charge=fix_area_charge,
                    amount=base_amount,
                    base_charge=total_monthly_charge,
                    penalty_percent=fix_area_charge.payment_penalty_amount,
                    civil=civil_amount,
                    other_cost_amount=other_amount,
                    penalty_amount=0,
                    total_charge_month=total_monthly_charge,
                    details=fix_area_charge.details or '',
                    title=fix_area_charge.name,
                    send_notification=False,  # ⛔ اعلان ارسال نشده
                    send_notification_date=None,
                    payment_deadline_date=fix_area_charge.payment_deadline,
                    content_type=ContentType.objects.get_for_model(FixAreaCharge),
                    object_id=fix_area_charge.id,
                )
            )

        # ایجاد همه UnifiedCharge ها در دیتابیس یکجا
        UnifiedCharge.objects.bulk_create(unified_charges)

        messages.success(self.request, 'شارژ با موفقیت ثبت گردید.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        managed_users = self.request.user.managed_users.all()
        unit_count = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).count()
        context['unit_count'] = unit_count
        total_people = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).aggregate(
            total=Sum('people_count'))['total'] or 0
        context['total_people'] = total_people
        context['total_area'] = \
            Unit.objects.filter(Q(user=self.request.user) | Q(user__in=managed_users), is_active=True).aggregate(
                total=Sum('area'))[
                'total'] or 0

        charges = FixAreaCharge.objects.filter(user=self.request.user).annotate(
            notified_count=Count(
                'unified_charges',
                filter=Q(unified_charges__send_notification=True)
            ),
            total_units=Count('unified_charges')
        ).order_by('-created_at')
        context['charges'] = charges
        paginate_by = self.request.GET.get('paginate', '20')

        if paginate_by == '1000':  # نمایش همه
            paginator = Paginator(charges, charges.count() or 20)
        else:
            paginate_by = int(paginate_by)
            paginator = Paginator(charges, paginate_by)

        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['charges'] = page_obj
        context['page_obj'] = page_obj
        context['paginate'] = paginate_by
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_fix_area_charge_edit(request, pk):
    charge = get_object_or_404(FixAreaCharge, pk=pk, user=request.user)

    # بررسی اینکه برای این شارژ اعلان ارسال شده باشد
    any_notify = UnifiedCharge.objects.filter(
        content_type=ContentType.objects.get_for_model(FixAreaCharge),
        object_id=charge.id,
        send_notification=True
    ).exists()
    if any_notify:
        messages.error(request, 'برای این شارژ اعلان ارسال شده و قابل ویرایش نیست.')
        return redirect('middle_add_fix_area_charge')

    if request.method == 'POST':
        form = FixAreaChargeForm(request.POST, request.FILES, instance=charge)
        if form.is_valid():
            with transaction.atomic():
                charge = form.save(commit=False)
                charge.name = charge.name or 'شارژ ثابت'
                charge.save()

                # کاربران و واحدهای تحت مدیریت
                managed_users = request.user.managed_users.all()
                units = Unit.objects.filter(is_active=True, user__in=managed_users)
                if not units.exists():
                    messages.error(request, 'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدها را ثبت کنید.')
                    return redirect('middle_manage_unit')

                # انتخاب Calculator
                calculator = CALCULATORS.get(charge.charge_type)
                if not calculator:
                    messages.error(request, 'نوع شارژ پشتیبانی نمی‌شود.')
                    return redirect('middle_add_fix_area_charge')

                unified_charges = []

                for unit in units:
                    # محاسبه مبلغ پایه برای هر واحد
                    base_amount = calculator.calculate(unit, charge)
                    civil_amount = charge.civil or 0
                    other_amount = charge.other_cost_amount or 0
                    total_monthly = base_amount + civil_amount + other_amount

                    # آپدیت یا ایجاد UnifiedCharge برای این واحد
                    UnifiedCharge.objects.update_or_create(
                        user=request.user,
                        unit=unit,
                        house=unit.myhouse,
                        content_type=ContentType.objects.get_for_model(FixAreaCharge),
                        object_id=charge.id,
                        defaults={
                            'bank': None,
                            'charge_type': charge.charge_type,
                            'main_charge': charge,
                            'amount': base_amount,
                            'base_charge': total_monthly,
                            'penalty_percent': charge.payment_penalty_amount or 0,
                            'civil': civil_amount,
                            'other_cost_amount': other_amount,
                            'penalty_amount': 0,
                            'total_charge_month': total_monthly,
                            'details': charge.details or '',
                            'title': charge.name,
                            'send_notification': False,
                            'send_notification_date': None,
                            'payment_deadline_date': charge.payment_deadline,
                        }
                    )

                messages.success(request, 'شارژ با موفقیت ویرایش شد.')
                return redirect('middle_add_fix_area_charge')
        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
    else:
        form = FixChargeForm(instance=charge)

    return render(request, 'middleCharge/fix_area_charge_template.html', {'form': form, 'charge': charge})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_fix_area_charge_delete(request, pk):
    charge = get_object_or_404(FixAreaCharge, id=pk, user=request.user)

    content_type = ContentType.objects.get_for_model(FixAreaCharge)

    # بررسی اینکه هیچ رکورد UnifiedCharge با is_paid=True وجود نداشته باشد
    if UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            is_paid=True
    ).exists():
        messages.error(request, "امکان حذف شارژ وجود ندارد چون پرداخت شارژ توسط واحد ثبت شده است.")
        return redirect(reverse('middle_add_fix_area_charge'))

    # چک کردن وجود رکوردهایی که send_notification == True هستند
    if UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            send_notification=True
    ).exists():
        messages.error(request, "برای این شارژ اطلاعیه صادر شده است. ابتدا اطلاعیه شارژ را حذف و مجدداً تلاش نمایید!")
        return redirect(reverse('middle_add_fix_area_charge'))

    try:
        charge.delete()
        messages.success(request, f'{charge.name} با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, "امکان حذف این شارژ به دلیل وابستگی وجود ندارد!")

    return redirect(reverse('middle_add_fix_area_charge'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_show_fix_area_charge_notification_form(request, pk):
    charge = get_object_or_404(FixAreaCharge, id=pk, user=request.user)
    content_type = ContentType.objects.get_for_model(FixAreaCharge)

    # ------------------ واحدها ------------------
    units = Unit.objects.filter(
        is_active=True
    ).filter(
        Q(user=request.user) | Q(user__manager=request.user)
    ).distinct().order_by('unit')

    # ------------------ ساخت UnifiedCharge ------------------
    existing_ids = UnifiedCharge.objects.filter(
        content_type=content_type,
        object_id=charge.id
    ).values_list('unit_id', flat=True)

    new_units = units.exclude(id__in=existing_ids)

    calculator = CALCULATORS.get(charge.charge_type)

    with transaction.atomic():
        for unit in new_units:
            base = calculator.calculate(unit, charge)
            civil = charge.civil or 0
            other = charge.other_cost_amount or 0
            total = base + civil + other

            UnifiedCharge.objects.create(
                user=request.user,
                unit=unit,
                amount=base,
                house=unit.myhouse,
                base_charge=total,
                total_charge_month=total,
                title=charge.name,
                main_charge=charge,
                charge_type=charge.charge_type,
                penalty_percent=charge.payment_penalty_amount,
                civil=civil,
                other_cost_amount=other,
                payment_deadline_date=charge.payment_deadline,
                content_type=content_type,
                object_id=charge.id,
            )

    # جستجو
    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    # ------------------ Pagination ------------------
    try:
        per_page = int(request.GET.get('per_page', 30))
    except ValueError:
        per_page = 30

    paginator = Paginator(units, per_page)
    page_units = paginator.get_page(request.GET.get('page'))

    # ------------------ POST: ارسال اطلاعیه یا پیامک ------------------
    if request.method == "POST":
        send_type = request.POST.get("send_type", "notify")
        selected = request.POST.getlist("units")

        if not selected:
            messages.warning(request, "هیچ واحدی انتخاب نشده")
            return redirect(request.path)

        qs = UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            unit_id__in=selected
        ).select_related("unit")

        if not qs.exists():
            messages.info(request, "اطلاعیه‌ای برای ارسال وجود ندارد")
            return redirect(request.path)

        # ثبت اطلاعیه سیستمی
        qs.update(
            send_notification=True,
            send_notification_date=timezone.now().date()
        )

        # ---------- ارسال پیامک ----------
        if send_type == "sms":
            result = SmsService.send_for_unified_charges(
                user=request.user,
                unified_charges=qs,
                meta_callback=lambda total_sms, total_price: qs.update(
                    send_sms=True,
                    send_sms_date=timezone.now().date(),
                    sms_count=total_sms,
                    sms_price=Decimal(settings.SMS_PRICE),
                    sms_total_price=total_price
                )
            )

            if result.success:
                messages.success(
                    request,
                    f"اطلاعیه سیستمی و پیامکی برای {qs.count()} واحد ارسال شد"
                )
            else:
                messages.error(request, result.message)

        else:
            messages.success(
                request,
                f"اطلاعیه سیستمی برای {qs.count()} واحد ثبت شد"
            )

        return redirect(request.path)

    # آماده‌سازی داده‌ها برای قالب
    uc_map = {
        uc.unit_id: uc
        for uc in UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            unit__in=page_units
        )
    }

    # دیگه نیازی به uc_dict نیست
    for i, unit in enumerate(page_units):
        uc = uc_map.get(unit.id)  # ← همینجا درست شد
        renter = unit.renters.filter(renter_is_active=True).first()
        page_units.object_list[i] = {
            'unit': unit,
            'renter': renter,
            'is_paid': uc.is_paid if uc else False,
            'is_notified': uc.send_notification if uc else False,
            'send_sms': uc.send_sms if uc else False,
            'sms_date': uc.send_sms_date if uc else None,
            'total_charge': uc.total_charge_month if uc else 0,
        }

    context = {
        'charge': charge,
        'page_obj': page_units,
        # 'paginator': paginator,
    }

    return render(request, 'middleCharge/notify_area_fix_charge_template.html', context)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_remove_send_notification_fix_area(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'فقط درخواست‌های POST مجاز است.'}, status=400)

    charge = get_object_or_404(FixAreaCharge, id=pk, user=request.user)
    selected_units = request.POST.getlist('units[]')

    if not selected_units:
        return JsonResponse({'warning': 'هیچ واحدی انتخاب نشده است.'})

    try:
        with transaction.atomic():
            content_type = ContentType.objects.get_for_model(FixAreaCharge)

            # رکوردهایی که باید غیرفعال شوند
            if selected_units == ['all']:
                qs = UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    is_paid=False,
                    send_notification=True  # فقط رکوردهای فعال
                )
            else:
                try:
                    selected_unit_ids = [int(uid) for uid in selected_units]
                except ValueError:
                    return JsonResponse({'error': 'شناسه واحد نامعتبر است.'}, status=400)

                qs = UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    unit_id__in=selected_unit_ids,
                    is_paid=False,
                    send_notification=True  # فقط رکوردهای فعال
                )

            updated_count = qs.update(
                send_notification=False,
                send_notification_date=None
            )

            # اگر هیچ رکوردی با send_notification=True باقی نماند → شارژ را غیرفعال کن
            if not UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    send_notification=True
            ).exists():
                charge.send_notification = False
                charge.save()

        if updated_count:
            return JsonResponse({'success': f'{updated_count} اطلاعیه غیرفعال شد.'})
        else:
            return JsonResponse({'info': 'رکوردی برای غیرفعال کردن یافت نشد.'})

    except Exception as e:
        return JsonResponse({'error': f'خطایی هنگام غیرفعال کردن اطلاعیه‌ها رخ داد: {str(e)}'}, status=500)


# ======================= Fix Person Charge  ==========================
@method_decorator(middle_admin_required, name='dispatch')
class MiddleFixPersonChargeCreateView(CreateView):
    model = FixPersonCharge
    template_name = 'middleCharge/fix_person_charge_template.html'
    form_class = FixPersonChargeForm
    success_url = reverse_lazy('middle_add_fix_person_charge')

    def form_valid(self, form):
        charge_name = form.cleaned_data.get('name')

        # گرفتن کاربران تحت مدیریت
        managed_users = self.request.user.managed_users.all()

        unit_count = UnifiedCharge.objects.filter(
            user=self.request.user,
            unit__is_active=True
        ).values('unit').distinct().count()
        form.instance.unit_count = unit_count

        units = Unit.objects.filter(
            is_active=True
        ).filter(
            Q(user=self.request.user) | Q(user__in=managed_users)
        ).distinct()
        total_area = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).aggregate(total=Sum('area'))['total'] or 0
        form.instance.total_area = total_area

        total_people = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).aggregate(total=Sum('people_count'))['total'] or 0
        form.instance.total_people = total_people

        if not units.exists():
            messages.error(
                self.request,
                'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدها را ثبت کنید.'
            )
            return redirect('middle_manage_unit')

        # ذخیره FixCharge
        fix_person_charge = form.save(commit=False)
        fix_person_charge.user = self.request.user
        fix_person_charge.name = charge_name
        fix_person_charge.save()

        # انتخاب Calculator
        calculator = CALCULATORS.get(fix_person_charge.charge_type)
        if not calculator:
            messages.error(self.request, 'نوع شارژ پشتیبانی نمی‌شود')
            return redirect(self.success_url)

        unified_charges = []

        for unit in units:
            # محاسبه مبلغ پایه برای هر واحد
            base_amount = calculator.calculate(unit, fix_person_charge)
            # مطمئن شدن که فیلدهای عددی عدد هستند
            civil_amount = fix_person_charge.civil or 0
            other_amount = fix_person_charge.other_cost_amount or 0
            total_monthly_charge = base_amount + civil_amount + other_amount

            unified_charges.append(
                UnifiedCharge(
                    user=self.request.user,
                    unit=unit,
                    bank=None,
                    house=unit.myhouse,
                    charge_type=fix_person_charge.charge_type,
                    main_charge=fix_person_charge,
                    amount=base_amount,
                    base_charge=total_monthly_charge,
                    penalty_percent=fix_person_charge.payment_penalty_amount,
                    civil=civil_amount,
                    other_cost_amount=other_amount,
                    penalty_amount=0,
                    total_charge_month=total_monthly_charge,
                    details=fix_person_charge.details or '',
                    title=fix_person_charge.name,
                    send_notification=False,  # ⛔ اعلان ارسال نشده
                    send_notification_date=None,
                    payment_deadline_date=fix_person_charge.payment_deadline,
                    content_type=ContentType.objects.get_for_model(FixPersonCharge),
                    object_id=fix_person_charge.id,
                )
            )

        # ایجاد همه UnifiedCharge ها در دیتابیس یکجا
        UnifiedCharge.objects.bulk_create(unified_charges)

        messages.success(self.request, 'شارژ با موفقیت ثبت گردید.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        managed_users = self.request.user.managed_users.all()
        unit_count = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).count()
        context['unit_count'] = unit_count
        total_people = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).aggregate(
            total=Sum('people_count'))['total'] or 0
        context['total_people'] = total_people
        context['total_area'] = \
            Unit.objects.filter(Q(user=self.request.user) | Q(user__in=managed_users), is_active=True).aggregate(
                total=Sum('area'))[
                'total'] or 0

        charges = FixPersonCharge.objects.filter(user=self.request.user).annotate(
            notified_count=Count(
                'unified_charges',
                filter=Q(unified_charges__send_notification=True)
            ),
            total_units=Count('unified_charges')
        ).order_by('-created_at')
        context['charges'] = charges
        paginate_by = self.request.GET.get('paginate', '20')

        if paginate_by == '1000':  # نمایش همه
            paginator = Paginator(charges, charges.count() or 20)
        else:
            paginate_by = int(paginate_by)
            paginator = Paginator(charges, paginate_by)

        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['charges'] = page_obj
        context['page_obj'] = page_obj
        context['paginate'] = paginate_by
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_fix_person_charge_edit(request, pk):
    charge = get_object_or_404(FixPersonCharge, pk=pk, user=request.user)

    # بررسی اینکه برای این شارژ اعلان ارسال شده باشد
    any_notify = UnifiedCharge.objects.filter(
        content_type=ContentType.objects.get_for_model(FixPersonCharge),
        object_id=charge.id,
        send_notification=True
    ).exists()
    if any_notify:
        messages.error(request, 'برای این شارژ اعلان ارسال شده و قابل ویرایش نیست.')
        return redirect('middle_add_fix_person_charge')

    if request.method == 'POST':
        form = FixPersonChargeForm(request.POST, request.FILES, instance=charge)
        if form.is_valid():
            with transaction.atomic():
                charge = form.save(commit=False)
                charge.name = charge.name or 'شارژ ثابت'
                charge.save()

                # کاربران و واحدهای تحت مدیریت
                managed_users = request.user.managed_users.all()
                units = Unit.objects.filter(is_active=True, user__in=managed_users)
                if not units.exists():
                    messages.error(request, 'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدها را ثبت کنید.')
                    return redirect('middle_manage_unit')

                # انتخاب Calculator
                calculator = CALCULATORS.get(charge.charge_type)
                if not calculator:
                    messages.error(request, 'نوع شارژ پشتیبانی نمی‌شود.')
                    return redirect('middle_add_fix_person_charge')

                unified_charges = []

                for unit in units:
                    # محاسبه مبلغ پایه برای هر واحد
                    base_amount = calculator.calculate(unit, charge)
                    civil_amount = charge.civil or 0
                    other_amount = charge.other_cost_amount or 0
                    total_monthly = base_amount + civil_amount + other_amount

                    # آپدیت یا ایجاد UnifiedCharge برای این واحد
                    UnifiedCharge.objects.update_or_create(
                        user=request.user,
                        unit=unit,
                        house=unit.myhouse,
                        content_type=ContentType.objects.get_for_model(FixPersonCharge),
                        object_id=charge.id,
                        defaults={
                            'bank': None,
                            'charge_type': charge.charge_type,
                            'main_charge': charge,
                            'amount': base_amount,
                            'base_charge': base_amount,
                            'penalty_percent': charge.payment_penalty_amount or 0,
                            'civil': civil_amount,
                            'other_cost_amount': other_amount,
                            'penalty_amount': 0,
                            'total_charge_month': total_monthly,
                            'details': charge.details or '',
                            'title': charge.name,
                            'send_notification': False,
                            'send_notification_date': None,
                            'payment_deadline_date': charge.payment_deadline,
                        }
                    )

                messages.success(request, 'شارژ با موفقیت ویرایش شد.')
                return redirect('middle_add_fix_person_charge')
        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
    else:
        form = FixChargeForm(instance=charge)

    return render(request, 'middleCharge/fix_person_charge_template.html', {'form': form, 'charge': charge})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_fix_person_charge_delete(request, pk):
    charge = get_object_or_404(FixPersonCharge, id=pk, user=request.user)
    content_type = ContentType.objects.get_for_model(FixPersonCharge)

    # بررسی اینکه هیچ رکورد UnifiedCharge با is_paid=True وجود نداشته باشد
    if UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            is_paid=True
    ).exists():
        messages.error(request, "امکان حذف شارژ وجود ندارد چون پرداخت شارژ توسط واحد ثبت شده است.")
        return redirect(reverse('middle_add_fix_person_charge'))

    # چک کردن وجود رکوردهایی که send_notification == True هستند
    if UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            send_notification=True
    ).exists():
        messages.error(request, "برای این شارژ اطلاعیه صادر شده است. ابتدا اطلاعیه شارژ را حذف و مجدداً تلاش نمایید!")
        return redirect(reverse('middle_add_fix_person_charge'))

    try:
        charge.delete()
        messages.success(request, f'{charge.name} با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, "امکان حذف این شارژ به دلیل وابستگی وجود ندارد!")

    return redirect(reverse('middle_add_fix_person_charge'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_show_fix_person_charge_notification_form(request, pk):
    charge = get_object_or_404(FixPersonCharge, id=pk, user=request.user)
    content_type = ContentType.objects.get_for_model(FixPersonCharge)

    # ------------------ واحدها ------------------
    units = Unit.objects.filter(
        is_active=True
    ).filter(
        Q(user=request.user) | Q(user__manager=request.user)
    ).distinct().order_by('unit')

    # ------------------ ساخت UnifiedCharge ------------------
    existing_ids = UnifiedCharge.objects.filter(
        content_type=content_type,
        object_id=charge.id
    ).values_list('unit_id', flat=True)

    new_units = units.exclude(id__in=existing_ids)

    calculator = CALCULATORS.get(charge.charge_type)

    with transaction.atomic():
        for unit in new_units:
            base = calculator.calculate(unit, charge)
            civil = charge.civil or 0
            other = charge.other_cost_amount or 0
            total = base + civil + other

            UnifiedCharge.objects.create(
                user=request.user,
                unit=unit,
                amount=base,
                base_charge=total,
                house=unit.myhouse,
                total_charge_month=total,
                title=charge.name,
                main_charge=charge,
                charge_type=charge.charge_type,
                penalty_percent=charge.payment_penalty_amount,
                civil=civil,
                other_cost_amount=other,
                payment_deadline_date=charge.payment_deadline,
                content_type=content_type,
                object_id=charge.id,
            )

    # جستجو
    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

        # ------------------ Pagination ------------------
    try:
        per_page = int(request.GET.get('per_page', 30))
    except ValueError:
        per_page = 30

    paginator = Paginator(units, per_page)
    page_units = paginator.get_page(request.GET.get('page'))

    # ------------------ POST: ارسال اطلاعیه یا پیامک ------------------
    if request.method == "POST":
        send_type = request.POST.get("send_type", "notify")
        selected = request.POST.getlist("units")

        if not selected:
            messages.warning(request, "هیچ واحدی انتخاب نشده")
            return redirect(request.path)

        qs = UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            unit_id__in=selected
        ).select_related("unit")

        if not qs.exists():
            messages.info(request, "اطلاعیه‌ای برای ارسال وجود ندارد")
            return redirect(request.path)

        # ثبت اطلاعیه سیستمی
        qs.update(
            send_notification=True,
            send_notification_date=timezone.now().date()
        )

        # ---------- ارسال پیامک ----------
        if send_type == "sms":
            result = SmsService.send_for_unified_charges(
                user=request.user,
                unified_charges=qs,
                meta_callback=lambda total_sms, total_price: qs.update(
                    send_sms=True,
                    send_sms_date=timezone.now().date(),
                    sms_count=total_sms,
                    sms_price=Decimal(settings.SMS_PRICE),
                    sms_total_price=total_price
                )
            )

            if result.success:
                messages.success(
                    request,
                    f"اطلاعیه سیستمی و پیامکی برای {qs.count()} واحد ارسال شد"
                )
            else:
                messages.error(request, result.message)

        else:
            messages.success(
                request,
                f"اطلاعیه سیستمی برای {qs.count()} واحد ثبت شد"
            )

        return redirect(request.path)

    # آماده‌سازی داده‌ها برای قالب
    uc_map = {
        uc.unit_id: uc
        for uc in UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            unit__in=page_units
        )
    }

    # دیگه نیازی به uc_dict نیست
    for i, unit in enumerate(page_units):
        uc = uc_map.get(unit.id)  # ← همینجا درست شد
        renter = unit.renters.filter(renter_is_active=True).first()
        page_units.object_list[i] = {
            'unit': unit,
            'renter': renter,
            'is_paid': uc.is_paid if uc else False,
            'is_notified': uc.send_notification if uc else False,
            'send_sms': uc.send_sms if uc else False,
            'sms_date': uc.send_sms_date if uc else None,
            'total_charge': uc.total_charge_month if uc else 0,
        }

    context = {
        'charge': charge,
        'page_obj': page_units,  # حالا فقط واحدهای دارای UnifiedCharge هستند
        # 'paginator': paginator,
    }
    return render(request, 'middleCharge/notify_person_fix_charge_template.html', context)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_remove_send_notification_fix_person(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'فقط درخواست‌های POST مجاز است.'}, status=400)

    charge = get_object_or_404(FixPersonCharge, id=pk, user=request.user)
    selected_units = request.POST.getlist('units[]')

    if not selected_units:
        return JsonResponse({'warning': 'هیچ واحدی انتخاب نشده است.'})

    try:
        with transaction.atomic():
            content_type = ContentType.objects.get_for_model(FixPersonCharge)

            # رکوردهایی که باید غیرفعال شوند
            if selected_units == ['all']:
                qs = UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    is_paid=False,
                    send_notification=True  # فقط رکوردهای فعال
                )
            else:
                try:
                    selected_unit_ids = [int(uid) for uid in selected_units]
                except ValueError:
                    return JsonResponse({'error': 'شناسه واحد نامعتبر است.'}, status=400)

                qs = UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    unit_id__in=selected_unit_ids,
                    is_paid=False,
                    send_notification=True  # فقط رکوردهای فعال
                )

            updated_count = qs.update(
                send_notification=False,
                send_notification_date=None
            )

            # اگر هیچ رکوردی با send_notification=True باقی نماند → شارژ را غیرفعال کن
            if not UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    send_notification=True
            ).exists():
                charge.send_notification = False
                charge.save()

        if updated_count:
            return JsonResponse({'success': f'{updated_count} اطلاعیه غیرفعال شد.'})
        else:
            return JsonResponse({'info': 'رکوردی برای غیرفعال کردن یافت نشد.'})

    except Exception as e:
        return JsonResponse({'error': f'خطایی هنگام غیرفعال کردن اطلاعیه‌ها رخ داد: {str(e)}'}, status=500)


# ============================== Person Area Charge ============================
@method_decorator(middle_admin_required, name='dispatch')
class MiddlePersonAreaChargeCreateView(CreateView):
    model = ChargeByPersonArea
    template_name = 'middleCharge/person_area_charge_template.html'
    form_class = PersonAreaChargeForm
    success_url = reverse_lazy('middle_add_person_area_charge')

    def form_valid(self, form):
        charge_name = form.cleaned_data.get('name')

        # گرفتن کاربران تحت مدیریت
        managed_users = self.request.user.managed_users.all()

        unit_count = UnifiedCharge.objects.filter(
            user=self.request.user,
            unit__is_active=True
        ).values('unit').distinct().count()
        form.instance.unit_count = unit_count

        units = Unit.objects.filter(
            is_active=True
        ).filter(
            Q(user=self.request.user) | Q(user__in=managed_users)
        ).distinct()
        total_area = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).aggregate(total=Sum('area'))['total'] or 0
        form.instance.total_area = total_area

        total_people = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).aggregate(total=Sum('people_count'))['total'] or 0
        form.instance.total_people = total_people

        if not units.exists():
            messages.error(
                self.request,
                'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدها را ثبت کنید.'
            )
            return redirect('middle_manage_unit')

        # ذخیره FixCharge
        person_area_charge = form.save(commit=False)
        person_area_charge.user = self.request.user
        person_area_charge.name = charge_name
        person_area_charge.save()

        # انتخاب Calculator
        calculator = CALCULATORS.get(person_area_charge.charge_type)
        if not calculator:
            messages.error(self.request, 'نوع شارژ پشتیبانی نمی‌شود')
            return redirect(self.success_url)

        unified_charges = []

        for unit in units:
            # محاسبه مبلغ پایه برای هر واحد
            base_amount = calculator.calculate(unit, person_area_charge)
            # مطمئن شدن که فیلدهای عددی عدد هستند
            civil_amount = person_area_charge.civil or 0
            other_amount = person_area_charge.other_cost_amount or 0
            total_monthly_charge = base_amount + civil_amount + other_amount

            unified_charges.append(
                UnifiedCharge(
                    user=self.request.user,
                    unit=unit,
                    bank=None,
                    house=unit.myhouse,
                    charge_type=person_area_charge.charge_type,
                    main_charge=person_area_charge,
                    amount=base_amount,
                    base_charge=total_monthly_charge,
                    penalty_percent=person_area_charge.payment_penalty_amount,
                    civil=civil_amount,
                    other_cost_amount=other_amount,
                    penalty_amount=0,
                    total_charge_month=total_monthly_charge,
                    details=person_area_charge.details or '',
                    title=person_area_charge.name,
                    send_notification=False,  # ⛔ اعلان ارسال نشده
                    send_notification_date=None,
                    payment_deadline_date=person_area_charge.payment_deadline,
                    content_type=ContentType.objects.get_for_model(ChargeByPersonArea),
                    object_id=person_area_charge.id,
                )
            )

        # ایجاد همه UnifiedCharge ها در دیتابیس یکجا
        UnifiedCharge.objects.bulk_create(unified_charges)

        messages.success(self.request, 'شارژ با موفقیت ثبت گردید.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        managed_users = self.request.user.managed_users.all()
        unit_count = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).count()
        context['unit_count'] = unit_count
        total_people = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).aggregate(
            total=Sum('people_count'))['total'] or 0
        context['total_people'] = total_people
        context['total_area'] = \
            Unit.objects.filter(Q(user=self.request.user) | Q(user__in=managed_users), is_active=True).aggregate(
                total=Sum('area'))[
                'total'] or 0

        charges = ChargeByPersonArea.objects.filter(user=self.request.user).annotate(
            notified_count=Count(
                'unified_charges',
                filter=Q(unified_charges__send_notification=True)
            ),
            total_units=Count('unified_charges')
        ).order_by('-created_at')
        context['charges'] = charges
        paginate_by = self.request.GET.get('paginate', '20')

        if paginate_by == '1000':  # نمایش همه
            paginator = Paginator(charges, charges.count() or 20)
        else:
            paginate_by = int(paginate_by)
            paginator = Paginator(charges, paginate_by)

        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['charges'] = page_obj
        context['page_obj'] = page_obj
        context['paginate'] = paginate_by
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_person_area_charge_edit(request, pk):
    charge = get_object_or_404(ChargeByPersonArea, pk=pk, user=request.user)

    # بررسی اینکه برای این شارژ اعلان ارسال شده باشد
    any_notify = UnifiedCharge.objects.filter(
        content_type=ContentType.objects.get_for_model(ChargeByPersonArea),
        object_id=charge.id,
        send_notification=True
    ).exists()
    if any_notify:
        messages.error(request, 'برای این شارژ اعلان ارسال شده و قابل ویرایش نیست.')
        return redirect('middle_add_person_area_charge')

    if request.method == 'POST':
        form = PersonAreaChargeForm(request.POST, request.FILES, instance=charge)
        if form.is_valid():
            with transaction.atomic():
                charge = form.save(commit=False)
                charge.name = charge.name or 'شارژ ثابت'
                charge.save()

                # کاربران و واحدهای تحت مدیریت
                managed_users = request.user.managed_users.all()
                units = Unit.objects.filter(is_active=True, user__in=managed_users)
                if not units.exists():
                    messages.error(request, 'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدها را ثبت کنید.')
                    return redirect('middle_manage_unit')

                # انتخاب Calculator
                calculator = CALCULATORS.get(charge.charge_type)
                if not calculator:
                    messages.error(request, 'نوع شارژ پشتیبانی نمی‌شود.')
                    return redirect('middle_add_fix_person_charge')

                unified_charges = []

                for unit in units:
                    # محاسبه مبلغ پایه برای هر واحد
                    base_amount = calculator.calculate(unit, charge)
                    civil_amount = charge.civil or 0
                    other_amount = charge.other_cost_amount or 0
                    total_monthly = base_amount + civil_amount + other_amount

                    # آپدیت یا ایجاد UnifiedCharge برای این واحد
                    UnifiedCharge.objects.update_or_create(
                        user=request.user,
                        house=unit.myhouse,
                        unit=unit,
                        content_type=ContentType.objects.get_for_model(ChargeByPersonArea),
                        object_id=charge.id,
                        defaults={
                            'bank': None,
                            'charge_type': charge.charge_type,
                            'main_charge': charge,
                            'amount': base_amount,
                            'base_charge': total_monthly,
                            'penalty_percent': charge.payment_penalty_amount or 0,
                            'civil': civil_amount,
                            'other_cost_amount': other_amount,
                            'penalty_amount': 0,
                            'total_charge_month': total_monthly,
                            'details': charge.details or '',
                            'title': charge.name,
                            'send_notification': False,
                            'send_notification_date': None,
                            'payment_deadline_date': charge.payment_deadline,
                        }
                    )

                messages.success(request, 'شارژ با موفقیت ویرایش شد.')
                return redirect('middle_add_person_area_charge')
        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
    else:
        form = FixChargeForm(instance=charge)

    return render(request, 'middleCharge/person_area_charge_template.html', {'form': form, 'charge': charge})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_person_area_charge_delete(request, pk):
    charge = get_object_or_404(ChargeByPersonArea, id=pk, user=request.user)
    content_type = ContentType.objects.get_for_model(ChargeByPersonArea)

    # بررسی اینکه هیچ رکورد UnifiedCharge با is_paid=True وجود نداشته باشد
    if UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            is_paid=True
    ).exists():
        messages.error(request, "امکان حذف شارژ وجود ندارد چون پرداخت شارژ توسط واحد ثبت شده است.")
        return redirect(reverse('middle_add_person_area_charge'))

    # چک کردن وجود رکوردهایی که send_notification == True هستند
    if UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            send_notification=True
    ).exists():
        messages.error(request, "برای این شارژ اطلاعیه صادر شده است. ابتدا اطلاعیه شارژ را حذف و مجدداً تلاش نمایید!")
        return redirect(reverse('middle_add_person_area_charge'))

    try:
        charge.delete()
        messages.success(request, f'{charge.name} با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, "امکان حذف این شارژ به دلیل وابستگی وجود ندارد!")

    return redirect(reverse('middle_add_person_area_charge'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_show_person_area_charge_notification_form(request, pk):
    charge = get_object_or_404(ChargeByPersonArea, id=pk, user=request.user)
    content_type = ContentType.objects.get_for_model(ChargeByPersonArea)

    # ------------------ واحدها ------------------
    units = Unit.objects.filter(
        is_active=True
    ).filter(
        Q(user=request.user) | Q(user__manager=request.user)
    ).distinct().order_by('unit')

    # ------------------ ساخت UnifiedCharge ------------------
    existing_ids = UnifiedCharge.objects.filter(
        content_type=content_type,
        object_id=charge.id
    ).values_list('unit_id', flat=True)

    new_units = units.exclude(id__in=existing_ids)

    calculator = CALCULATORS.get(charge.charge_type)

    with transaction.atomic():
        for unit in new_units:
            base = calculator.calculate(unit, charge)
            civil = charge.civil or 0
            other = charge.other_cost_amount or 0
            total = base + civil + other

            UnifiedCharge.objects.create(
                user=request.user,
                unit=unit,
                amount=base,
                house=unit.myhouse,
                base_charge=total,
                total_charge_month=total,
                title=charge.name,
                main_charge=charge,
                charge_type=charge.charge_type,
                penalty_percent=charge.payment_penalty_amount,
                civil=civil,
                other_cost_amount=other,
                payment_deadline_date=charge.payment_deadline,
                content_type=content_type,
                object_id=charge.id,
            )

    # جستجو
    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    # ------------------ Pagination ------------------
    try:
        per_page = int(request.GET.get('per_page', 30))
    except ValueError:
        per_page = 30

    paginator = Paginator(units, per_page)
    page_units = paginator.get_page(request.GET.get('page'))

    # ------------------ POST: ارسال اطلاعیه یا پیامک ------------------
    if request.method == "POST":
        send_type = request.POST.get("send_type", "notify")
        selected = request.POST.getlist("units")

        if not selected:
            messages.warning(request, "هیچ واحدی انتخاب نشده")
            return redirect(request.path)

        qs = UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            unit_id__in=selected
        ).select_related("unit")

        if not qs.exists():
            messages.info(request, "اطلاعیه‌ای برای ارسال وجود ندارد")
            return redirect(request.path)

        # ثبت اطلاعیه سیستمی
        qs.update(
            send_notification=True,
            send_notification_date=timezone.now().date()
        )

        # ---------- ارسال پیامک ----------
        if send_type == "sms":
            result = SmsService.send_for_unified_charges(
                user=request.user,
                unified_charges=qs,
                meta_callback=lambda total_sms, total_price: qs.update(
                    send_sms=True,
                    send_sms_date=timezone.now().date(),
                    sms_count=total_sms,
                    sms_price=Decimal(settings.SMS_PRICE),
                    sms_total_price=total_price
                )
            )

            if result.success:
                messages.success(
                    request,
                    f"اطلاعیه سیستمی و پیامکی برای {qs.count()} واحد ارسال شد"
                )
            else:
                messages.error(request, result.message)

        else:
            messages.success(
                request,
                f"اطلاعیه سیستمی برای {qs.count()} واحد ثبت شد"
            )

        return redirect(request.path)

    # آماده‌سازی داده‌ها برای قالب
    uc_map = {
        uc.unit_id: uc
        for uc in UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            unit__in=page_units
        )
    }

    # دیگه نیازی به uc_dict نیست
    for i, unit in enumerate(page_units):
        uc = uc_map.get(unit.id)  # ← همینجا درست شد
        renter = unit.renters.filter(renter_is_active=True).first()
        page_units.object_list[i] = {
            'unit': unit,
            'renter': renter,
            'is_paid': uc.is_paid if uc else False,
            'is_notified': uc.send_notification if uc else False,
            'send_sms': uc.send_sms if uc else False,
            'sms_date': uc.send_sms_date if uc else None,
            'total_charge': uc.total_charge_month if uc else 0,
        }
    context = {
        'charge': charge,
        'page_obj': page_units,  # حالا فقط واحدهای دارای UnifiedCharge هستند
        # 'paginator': paginator,
    }
    return render(request, 'middleCharge/notify_person_area_charge_template.html', context)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_remove_send_notification_person_area(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'فقط درخواست‌های POST مجاز است.'}, status=400)

    charge = get_object_or_404(ChargeByPersonArea, id=pk, user=request.user)
    selected_units = request.POST.getlist('units[]')

    if not selected_units:
        return JsonResponse({'warning': 'هیچ واحدی انتخاب نشده است.'})

    try:
        with transaction.atomic():
            content_type = ContentType.objects.get_for_model(ChargeByPersonArea)

            # رکوردهایی که باید غیرفعال شوند
            if selected_units == ['all']:
                qs = UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    is_paid=False,
                    send_notification=True  # فقط رکوردهای فعال
                )
            else:
                try:
                    selected_unit_ids = [int(uid) for uid in selected_units]
                except ValueError:
                    return JsonResponse({'error': 'شناسه واحد نامعتبر است.'}, status=400)

                qs = UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    unit_id__in=selected_unit_ids,
                    is_paid=False,
                    send_notification=True  # فقط رکوردهای فعال
                )

            updated_count = qs.update(
                send_notification=False,
                send_notification_date=None
            )

            # اگر هیچ رکوردی با send_notification=True باقی نماند → شارژ را غیرفعال کن
            if not UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    send_notification=True
            ).exists():
                charge.send_notification = False
                charge.save()

        if updated_count:
            return JsonResponse({'success': f'{updated_count} اطلاعیه غیرفعال شد.'})
        else:
            return JsonResponse({'info': 'رکوردی برای غیرفعال کردن یافت نشد.'})

    except Exception as e:
        return JsonResponse({'error': f'خطایی هنگام غیرفعال کردن اطلاعیه‌ها رخ داد: {str(e)}'}, status=500)


# ==========================Fix Person Area Charge ================================
@method_decorator(middle_admin_required, name='dispatch')
class MiddlePersonAreaFixChargeCreateView(CreateView):
    model = ChargeByFixPersonArea
    template_name = 'middleCharge/person_area_fix_charge_template.html'
    form_class = PersonAreaFixChargeForm
    success_url = reverse_lazy('middle_add_person_area_fix_charge')

    def form_valid(self, form):
        charge_name = form.cleaned_data.get('name')

        # گرفتن کاربران تحت مدیریت
        managed_users = self.request.user.managed_users.all()

        unit_count = UnifiedCharge.objects.filter(
            user=self.request.user,
            unit__is_active=True
        ).values('unit').distinct().count()
        form.instance.unit_count = unit_count

        units = Unit.objects.filter(
            is_active=True
        ).filter(
            Q(user=self.request.user) | Q(user__in=managed_users)
        ).distinct()
        total_area = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).aggregate(total=Sum('area'))['total'] or 0
        form.instance.total_area = total_area

        total_people = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).aggregate(total=Sum('people_count'))['total'] or 0
        form.instance.total_people = total_people

        if not units.exists():
            messages.error(
                self.request,
                'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدها را ثبت کنید.'
            )
            return redirect('middle_manage_unit')

        # ذخیره FixCharge
        fix_person_area_charge = form.save(commit=False)
        fix_person_area_charge.user = self.request.user
        fix_person_area_charge.name = charge_name
        fix_person_area_charge.save()

        # انتخاب Calculator
        calculator = CALCULATORS.get(fix_person_area_charge.charge_type)
        if not calculator:
            messages.error(self.request, 'نوع شارژ پشتیبانی نمی‌شود')
            return redirect(self.success_url)

        unified_charges = []

        for unit in units:
            # محاسبه مبلغ پایه برای هر واحد
            base_amount = calculator.calculate(unit, fix_person_area_charge)
            # مطمئن شدن که فیلدهای عددی عدد هستند
            civil_amount = fix_person_area_charge.civil or 0
            other_amount = fix_person_area_charge.other_cost_amount or 0
            total_monthly_charge = base_amount + civil_amount + other_amount

            unified_charges.append(
                UnifiedCharge(
                    user=self.request.user,
                    unit=unit,
                    bank=None,
                    house=unit.myhouse,
                    charge_type=fix_person_area_charge.charge_type,
                    main_charge=fix_person_area_charge,
                    amount=base_amount,
                    base_charge=total_monthly_charge,
                    penalty_percent=fix_person_area_charge.payment_penalty_amount,
                    civil=civil_amount,
                    other_cost_amount=other_amount,
                    penalty_amount=0,
                    total_charge_month=total_monthly_charge,
                    details=fix_person_area_charge.details or '',
                    title=fix_person_area_charge.name,
                    send_notification=False,  # ⛔ اعلان ارسال نشده
                    send_notification_date=None,
                    payment_deadline_date=fix_person_area_charge.payment_deadline,
                    content_type=ContentType.objects.get_for_model(ChargeByFixPersonArea),
                    object_id=fix_person_area_charge.id,
                )
            )

        # ایجاد همه UnifiedCharge ها در دیتابیس یکجا
        UnifiedCharge.objects.bulk_create(unified_charges)

        messages.success(self.request, 'شارژ با موفقیت ثبت گردید.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        managed_users = self.request.user.managed_users.all()
        unit_count = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).count()
        context['unit_count'] = unit_count
        total_people = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).aggregate(
            total=Sum('people_count'))['total'] or 0
        context['total_people'] = total_people
        context['total_area'] = \
            Unit.objects.filter(Q(user=self.request.user) | Q(user__in=managed_users), is_active=True).aggregate(
                total=Sum('area'))[
                'total'] or 0

        charges = ChargeByFixPersonArea.objects.filter(user=self.request.user).annotate(
            notified_count=Count(
                'unified_charges',
                filter=Q(unified_charges__send_notification=True)
            ),
            total_units=Count('unified_charges')
        ).order_by('-created_at')
        context['charges'] = charges
        paginate_by = self.request.GET.get('paginate', '20')

        if paginate_by == '1000':  # نمایش همه
            paginator = Paginator(charges, charges.count() or 20)
        else:
            paginate_by = int(paginate_by)
            paginator = Paginator(charges, paginate_by)

        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['charges'] = page_obj
        context['page_obj'] = page_obj
        context['paginate'] = paginate_by
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_person_area_fix_charge_edit(request, pk):
    charge = get_object_or_404(ChargeByFixPersonArea, pk=pk, user=request.user)

    # بررسی اینکه برای این شارژ اعلان ارسال شده باشد
    any_notify = UnifiedCharge.objects.filter(
        content_type=ContentType.objects.get_for_model(ChargeByFixPersonArea),
        object_id=charge.id,
        send_notification=True
    ).exists()
    if any_notify:
        messages.error(request, 'برای این شارژ اعلان ارسال شده و قابل ویرایش نیست.')
        return redirect('middle_add_person_area_fix_charge')

    if request.method == 'POST':
        form = PersonAreaFixChargeForm(request.POST, request.FILES, instance=charge)
        if form.is_valid():
            with transaction.atomic():
                charge = form.save(commit=False)
                charge.name = charge.name or 'شارژ ثابت'
                charge.save()

                # کاربران و واحدهای تحت مدیریت
                managed_users = request.user.managed_users.all()
                units = Unit.objects.filter(is_active=True, user__in=managed_users)
                if not units.exists():
                    messages.error(request, 'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدها را ثبت کنید.')
                    return redirect('middle_manage_unit')

                # انتخاب Calculator
                calculator = CALCULATORS.get(charge.charge_type)
                if not calculator:
                    messages.error(request, 'نوع شارژ پشتیبانی نمی‌شود.')
                    return redirect('middle_add_person_area_fix_charge')

                unified_charges = []

                for unit in units:
                    # محاسبه مبلغ پایه برای هر واحد
                    base_amount = calculator.calculate(unit, charge)
                    civil_amount = charge.civil or 0
                    other_amount = charge.other_cost_amount or 0
                    total_monthly = base_amount + civil_amount + other_amount

                    # آپدیت یا ایجاد UnifiedCharge برای این واحد
                    UnifiedCharge.objects.update_or_create(
                        user=request.user,
                        unit=unit,
                        house=unit.myhouse,
                        content_type=ContentType.objects.get_for_model(ChargeByFixPersonArea),
                        object_id=charge.id,
                        defaults={
                            'bank': None,
                            'charge_type': charge.charge_type,
                            'main_charge': charge,
                            'amount': base_amount,
                            'base_charge': total_monthly,
                            'penalty_percent': charge.payment_penalty_amount or 0,
                            'civil': civil_amount,
                            'other_cost_amount': other_amount,
                            'penalty_amount': 0,
                            'total_charge_month': total_monthly,
                            'details': charge.details or '',
                            'title': charge.name,
                            'send_notification': False,
                            'send_notification_date': None,
                            'payment_deadline_date': charge.payment_deadline,
                        }
                    )

                messages.success(request, 'شارژ با موفقیت ویرایش شد.')
                return redirect('middle_add_person_area_fix_charge')
        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
    else:
        form = FixChargeForm(instance=charge)
        return render(request, 'middleCharge/person_area_fix_charge_template.html',
                      {'form': form, 'charge': charge})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_person_area_fix_delete(request, pk):
    charge = get_object_or_404(ChargeByFixPersonArea, id=pk, user=request.user)
    content_type = ContentType.objects.get_for_model(ChargeByFixPersonArea)

    # بررسی اینکه هیچ رکورد UnifiedCharge با is_paid=True وجود نداشته باشد
    if UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            is_paid=True
    ).exists():
        messages.error(request, "امکان حذف شارژ وجود ندارد چون پرداخت شارژ توسط واحد ثبت شده است.")
        return redirect(reverse('middle_add_person_area_fix_charge'))

    # چک کردن وجود رکوردهایی که send_notification == True هستند
    if UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            send_notification=True
    ).exists():
        messages.error(request, "برای این شارژ اطلاعیه صادر شده است. ابتدا اطلاعیه شارژ را حذف و مجدداً تلاش نمایید!")
        return redirect(reverse('middle_add_person_area_fix_charge'))

    try:
        charge.delete()
        messages.success(request, f'{charge.name} با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, "امکان حذف این شارژ به دلیل وابستگی وجود ندارد!")

    return redirect(reverse('middle_add_person_area_fix_charge'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_show_fix_person_area_charge_notification_form(request, pk):
    charge = get_object_or_404(ChargeByFixPersonArea, id=pk, user=request.user)
    content_type = ContentType.objects.get_for_model(ChargeByFixPersonArea)

    # ------------------ واحدها ------------------
    units = Unit.objects.filter(
        is_active=True
    ).filter(
        Q(user=request.user) | Q(user__manager=request.user)
    ).distinct().order_by('unit')

    # ------------------ ساخت UnifiedCharge ------------------
    existing_ids = UnifiedCharge.objects.filter(
        content_type=content_type,
        object_id=charge.id
    ).values_list('unit_id', flat=True)

    new_units = units.exclude(id__in=existing_ids)

    calculator = CALCULATORS.get(charge.charge_type)

    with transaction.atomic():
        for unit in new_units:
            base = calculator.calculate(unit, charge)
            civil = charge.civil or 0
            other = charge.other_cost_amount or 0
            total = base + civil + other

            UnifiedCharge.objects.create(
                user=request.user,
                unit=unit,
                amount=base,
                house=unit.myhouse,
                base_charge=total,
                total_charge_month=total,
                title=charge.name,
                main_charge=charge,
                charge_type=charge.charge_type,
                penalty_percent=charge.payment_penalty_amount,
                civil=civil,
                other_cost_amount=other,
                payment_deadline_date=charge.payment_deadline,
                content_type=content_type,
                object_id=charge.id,
            )

    # جستجو
    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    # ------------------ Pagination ------------------
    try:
        per_page = int(request.GET.get('per_page', 30))
    except ValueError:
        per_page = 30

    paginator = Paginator(units, per_page)
    page_units = paginator.get_page(request.GET.get('page'))

    # ------------------ POST: ارسال اطلاعیه یا پیامک ------------------
    if request.method == "POST":
        send_type = request.POST.get("send_type", "notify")
        selected = request.POST.getlist("units")

        if not selected:
            messages.warning(request, "هیچ واحدی انتخاب نشده")
            return redirect(request.path)

        qs = UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            unit_id__in=selected
        ).select_related("unit")

        if not qs.exists():
            messages.info(request, "اطلاعیه‌ای برای ارسال وجود ندارد")
            return redirect(request.path)

        # ثبت اطلاعیه سیستمی
        qs.update(
            send_notification=True,
            send_notification_date=timezone.now().date()
        )

        # ---------- ارسال پیامک ----------
        if send_type == "sms":
            result = SmsService.send_for_unified_charges(
                user=request.user,
                unified_charges=qs,
                meta_callback=lambda total_sms, total_price: qs.update(
                    send_sms=True,
                    send_sms_date=timezone.now().date(),
                    sms_count=total_sms,
                    sms_price=Decimal(settings.SMS_PRICE),
                    sms_total_price=total_price
                )
            )

            if result.success:
                messages.success(
                    request,
                    f"اطلاعیه سیستمی و پیامکی برای {qs.count()} واحد ارسال شد"
                )
            else:
                messages.error(request, result.message)

        else:
            messages.success(
                request,
                f"اطلاعیه سیستمی برای {qs.count()} واحد ثبت شد"
            )

        return redirect(request.path)

    # آماده‌سازی داده‌ها برای قالب
    uc_map = {
        uc.unit_id: uc
        for uc in UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            unit__in=page_units
        )
    }

    # دیگه نیازی به uc_dict نیست
    for i, unit in enumerate(page_units):
        uc = uc_map.get(unit.id)  # ← همینجا درست شد
        renter = unit.renters.filter(renter_is_active=True).first()
        page_units.object_list[i] = {
            'unit': unit,
            'renter': renter,
            'is_paid': uc.is_paid if uc else False,
            'is_notified': uc.send_notification if uc else False,
            'send_sms': uc.send_sms if uc else False,
            'sms_date': uc.send_sms_date if uc else None,
            'total_charge': uc.total_charge_month if uc else 0,
        }

    context = {
        'charge': charge,
        'page_obj': page_units,  # حالا فقط واحدهای دارای UnifiedCharge هستند
        # 'paginator': paginator,
    }
    return render(request, 'middleCharge/notify_fix_person_area_charge_template.html', context)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_remove_send_notification_fix_person_area(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'فقط درخواست‌های POST مجاز است.'}, status=400)

    charge = get_object_or_404(ChargeByFixPersonArea, id=pk, user=request.user)
    selected_units = request.POST.getlist('units[]')

    if not selected_units:
        return JsonResponse({'warning': 'هیچ واحدی انتخاب نشده است.'})

    try:
        with transaction.atomic():
            content_type = ContentType.objects.get_for_model(ChargeByFixPersonArea)

            # رکوردهایی که باید غیرفعال شوند
            if selected_units == ['all']:
                qs = UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    is_paid=False,
                    send_notification=True  # فقط رکوردهای فعال
                )
            else:
                try:
                    selected_unit_ids = [int(uid) for uid in selected_units]
                except ValueError:
                    return JsonResponse({'error': 'شناسه واحد نامعتبر است.'}, status=400)

                qs = UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    unit_id__in=selected_unit_ids,
                    is_paid=False,
                    send_notification=True  # فقط رکوردهای فعال
                )

            updated_count = qs.update(
                send_notification=False,
                send_notification_date=None
            )

            # اگر هیچ رکوردی با send_notification=True باقی نماند → شارژ را غیرفعال کن
            if not UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    send_notification=True
            ).exists():
                charge.send_notification = False
                charge.save()

        if updated_count:
            return JsonResponse({'success': f'{updated_count} اطلاعیه غیرفعال شد.'})
        else:
            return JsonResponse({'info': 'رکوردی برای غیرفعال کردن یافت نشد.'})

    except Exception as e:
        return JsonResponse({'error': f'خطایی هنگام غیرفعال کردن اطلاعیه‌ها رخ داد: {str(e)}'}, status=500)


# =========================ّFix Variable Charge =================================
@method_decorator(middle_admin_required, name='dispatch')
class MiddleVariableFixChargeCreateView(CreateView):
    model = ChargeFixVariable
    template_name = 'middleCharge/variable_fix_charge_template.html'
    form_class = VariableFixChargeForm
    success_url = reverse_lazy('middle_add_variable_fix_charge')

    def form_valid(self, form):
        charge_name = form.cleaned_data.get('name')

        # گرفتن کاربران تحت مدیریت
        managed_users = self.request.user.managed_users.all()

        unit_count = UnifiedCharge.objects.filter(
            user=self.request.user,
            unit__is_active=True
        ).values('unit').distinct().count()
        form.instance.unit_count = unit_count

        units = Unit.objects.filter(
            is_active=True
        ).filter(
            Q(user=self.request.user) | Q(user__in=managed_users)
        ).distinct()
        total_area = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).aggregate(total=Sum('area'))['total'] or 0
        form.instance.total_area = total_area

        total_people = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).aggregate(total=Sum('people_count'))['total'] or 0
        form.instance.total_people = total_people

        if not units.exists():
            messages.error(
                self.request,
                'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدها را ثبت کنید.'
            )
            return redirect('middle_manage_unit')

        # ذخیره FixCharge
        fix_variable = form.save(commit=False)
        fix_variable.user = self.request.user
        fix_variable.name = charge_name
        fix_variable.save()

        # انتخاب Calculator
        calculator = CALCULATORS.get(fix_variable.charge_type)
        if not calculator:
            messages.error(self.request, 'نوع شارژ پشتیبانی نمی‌شود')
            return redirect(self.success_url)

        unified_charges = []

        for unit in units:
            # محاسبه مبلغ پایه برای هر واحد
            base_amount = calculator.calculate(unit, fix_variable)
            # مطمئن شدن که فیلدهای عددی عدد هستند
            civil_amount = fix_variable.civil or 0
            other_amount = fix_variable.other_cost_amount or 0
            parking_count = getattr(unit, 'parking_counts', 0) or 0

            parking_price = fix_variable.extra_parking_amount or 0
            parking_total = parking_count * parking_price

            total_monthly_charge = base_amount + civil_amount + other_amount + parking_total

            unified_charges.append(
                UnifiedCharge(
                    user=self.request.user,
                    unit=unit,
                    bank=None,
                    house=unit.myhouse,
                    charge_type=fix_variable.charge_type,
                    extra_parking_price=parking_total,
                    main_charge=fix_variable,
                    amount=base_amount,
                    base_charge=total_monthly_charge,
                    penalty_percent=fix_variable.payment_penalty_amount,
                    civil=civil_amount,
                    other_cost_amount=other_amount,
                    penalty_amount=0,
                    total_charge_month=total_monthly_charge,
                    details=fix_variable.details or '',
                    title=fix_variable.name,
                    send_notification=False,  # ⛔ اعلان ارسال نشده
                    send_notification_date=None,
                    payment_deadline_date=fix_variable.payment_deadline,
                    content_type=ContentType.objects.get_for_model(ChargeFixVariable),
                    object_id=fix_variable.id,
                )
            )

        # ایجاد همه UnifiedCharge ها در دیتابیس یکجا
        UnifiedCharge.objects.bulk_create(unified_charges)

        messages.success(self.request, 'شارژ با موفقیت ثبت گردید.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        managed_users = self.request.user.managed_users.all()
        unit_count = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).count()
        context['unit_count'] = unit_count
        total_people = Unit.objects.filter(
            Q(user=self.request.user) | Q(user__in=managed_users),
            is_active=True,
        ).aggregate(
            total=Sum('people_count'))['total'] or 0
        context['total_people'] = total_people
        context['total_area'] = \
            Unit.objects.filter(Q(user=self.request.user) | Q(user__in=managed_users), is_active=True).aggregate(
                total=Sum('area'))[
                'total'] or 0

        charges = ChargeFixVariable.objects.filter(user=self.request.user).annotate(
            notified_count=Count(
                'unified_charges',
                filter=Q(unified_charges__send_notification=True)
            ),
            total_units=Count('unified_charges')
        ).order_by('-created_at')
        context['charges'] = charges
        paginate_by = self.request.GET.get('paginate', '20')

        if paginate_by == '1000':  # نمایش همه
            paginator = Paginator(charges, charges.count() or 20)
        else:
            paginate_by = int(paginate_by)
            paginator = Paginator(charges, paginate_by)

        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['charges'] = page_obj
        context['page_obj'] = page_obj
        context['paginate'] = paginate_by
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_variable_fix_charge_edit(request, pk):
    charge = get_object_or_404(ChargeFixVariable, pk=pk, user=request.user)

    # بررسی اینکه برای این شارژ اعلان ارسال شده باشد
    any_notify = UnifiedCharge.objects.filter(
        content_type=ContentType.objects.get_for_model(ChargeFixVariable),
        object_id=charge.id,
        send_notification=True
    ).exists()
    if any_notify:
        messages.error(request, 'برای این شارژ اعلان ارسال شده و قابل ویرایش نیست.')
        return redirect('middle_add_variable_fix_charge')

    if request.method == 'POST':
        form = VariableFixChargeForm(request.POST, request.FILES, instance=charge)
        if form.is_valid():
            with transaction.atomic():
                charge = form.save(commit=False)
                charge.name = charge.name or 'شارژ ثابت'
                charge.save()

                # کاربران و واحدهای تحت مدیریت
                managed_users = request.user.managed_users.all()
                units = Unit.objects.filter(is_active=True, user__in=managed_users)
                if not units.exists():
                    messages.error(request, 'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدها را ثبت کنید.')
                    return redirect('middle_manage_unit')

                # انتخاب Calculator
                calculator = CALCULATORS.get(charge.charge_type)
                if not calculator:
                    messages.error(request, 'نوع شارژ پشتیبانی نمی‌شود.')
                    return redirect('middle_add_variable_fix_charge')

                unified_charges = []

                for unit in units:
                    # محاسبه مبلغ پایه برای هر واحد
                    base_amount = calculator.calculate(unit, charge)
                    civil_amount = charge.civil or 0
                    other_amount = charge.other_cost_amount or 0
                    parking_count = getattr(unit, 'parking_counts', 0) or 0
                    parking_price = charge.extra_parking_amount or 0
                    parking_total = parking_count * parking_price

                    total_monthly = base_amount + civil_amount + other_amount + parking_total

                    # آپدیت یا ایجاد UnifiedCharge برای این واحد
                    UnifiedCharge.objects.update_or_create(
                        user=request.user,
                        unit=unit,
                        house=unit.myhouse,
                        content_type=ContentType.objects.get_for_model(ChargeFixVariable),
                        object_id=charge.id,
                        defaults={
                            'bank': None,
                            'charge_type': charge.charge_type,
                            'main_charge': charge,
                            'amount': base_amount,
                            'base_charge': total_monthly,
                            'extra_parking_price': parking_total,
                            'penalty_percent': charge.payment_penalty_amount or 0,
                            'civil': civil_amount,
                            'other_cost_amount': other_amount,
                            'penalty_amount': 0,
                            'total_charge_month': total_monthly,
                            'details': charge.details or '',
                            'title': charge.name,
                            'send_notification': False,
                            'send_notification_date': None,
                            'payment_deadline_date': charge.payment_deadline,
                        }
                    )

                messages.success(request, 'شارژ با موفقیت ویرایش شد.')
                return redirect('middle_add_variable_fix_charge')
        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
    else:
        form = FixChargeForm(instance=charge)
        return render(request, 'middleCharge/variable_fix_charge_template.html',
                      {'form': form, 'charge': charge})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_variable_fix_charge_delete(request, pk):
    charge = get_object_or_404(ChargeFixVariable, id=pk, user=request.user)
    content_type = ContentType.objects.get_for_model(ChargeFixVariable)

    # بررسی اینکه هیچ رکورد UnifiedCharge با is_paid=True وجود نداشته باشد
    if UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            is_paid=True
    ).exists():
        messages.error(request, "امکان حذف شارژ وجود ندارد چون پرداخت شارژ توسط واحد ثبت شده است.")
        return redirect(reverse('middle_add_variable_fix_charge'))

    # چک کردن وجود رکوردهایی که send_notification == True هستند
    if UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            send_notification=True
    ).exists():
        messages.error(request, "برای این شارژ اطلاعیه صادر شده است. ابتدا اطلاعیه شارژ را حذف و مجدداً تلاش نمایید!")
        return redirect(reverse('middle_add_variable_fix_charge'))

    try:
        charge.delete()
        messages.success(request, f'{charge.name} با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, "امکان حذف این شارژ به دلیل وابستگی وجود ندارد!")

    return redirect(reverse('middle_add_variable_fix_charge'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_show_fix_variable_notification_form(request, pk):
    charge = get_object_or_404(ChargeFixVariable, id=pk, user=request.user)
    content_type = ContentType.objects.get_for_model(ChargeFixVariable)

    # ------------------ واحدها ------------------
    units = Unit.objects.filter(
        is_active=True
    ).filter(
        Q(user=request.user) | Q(user__manager=request.user)
    ).distinct().order_by('unit')

    # ------------------ ساخت UnifiedCharge ------------------
    existing_ids = UnifiedCharge.objects.filter(
        content_type=content_type,
        object_id=charge.id
    ).values_list('unit_id', flat=True)

    new_units = units.exclude(id__in=existing_ids)

    calculator = CALCULATORS.get(charge.charge_type)

    with transaction.atomic():
        for unit in new_units:
            base = calculator.calculate(unit, charge)
            civil = charge.civil or 0
            other = charge.other_cost_amount or 0
            total = base + civil + other

            UnifiedCharge.objects.create(
                user=request.user,
                unit=unit,
                amount=base,
                house=unit.myhouse,
                base_charge=total,
                total_charge_month=total,
                title=charge.name,
                main_charge=charge,
                charge_type=charge.charge_type,
                penalty_percent=charge.payment_penalty_amount,
                civil=civil,
                other_cost_amount=other,
                payment_deadline_date=charge.payment_deadline,
                content_type=content_type,
                object_id=charge.id,
            )

    # جستجو
    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    # ------------------ Pagination ------------------
    try:
        per_page = int(request.GET.get('per_page', 30))
    except ValueError:
        per_page = 30

    paginator = Paginator(units, per_page)
    page_units = paginator.get_page(request.GET.get('page'))

    # ------------------ POST: ارسال اطلاعیه یا پیامک ------------------
    if request.method == "POST":
        send_type = request.POST.get("send_type", "notify")
        selected = request.POST.getlist("units")

        if not selected:
            messages.warning(request, "هیچ واحدی انتخاب نشده")
            return redirect(request.path)

        qs = UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            unit_id__in=selected
        ).select_related("unit")

        if not qs.exists():
            messages.info(request, "اطلاعیه‌ای برای ارسال وجود ندارد")
            return redirect(request.path)

        # ثبت اطلاعیه سیستمی
        qs.update(
            send_notification=True,
            send_notification_date=timezone.now().date()
        )

        # ---------- ارسال پیامک ----------
        if send_type == "sms":
            result = SmsService.send_for_unified_charges(
                user=request.user,
                unified_charges=qs,
                meta_callback=lambda total_sms, total_price: qs.update(
                    send_sms=True,
                    send_sms_date=timezone.now().date(),
                    sms_count=total_sms,
                    sms_price=Decimal(settings.SMS_PRICE),
                    sms_total_price=total_price
                )
            )

            if result.success:
                messages.success(
                    request,
                    f"اطلاعیه سیستمی و پیامکی برای {qs.count()} واحد ارسال شد"
                )
            else:
                messages.error(request, result.message)

        else:
            messages.success(
                request,
                f"اطلاعیه سیستمی برای {qs.count()} واحد ثبت شد"
            )

        return redirect(request.path)

    # آماده‌سازی داده‌ها برای قالب
    uc_map = {
        uc.unit_id: uc
        for uc in UnifiedCharge.objects.filter(
            content_type=content_type,
            object_id=charge.id,
            unit__in=page_units
        )
    }

    # دیگه نیازی به uc_dict نیست
    for i, unit in enumerate(page_units):
        uc = uc_map.get(unit.id)  # ← همینجا درست شد
        renter = unit.renters.filter(renter_is_active=True).first()
        page_units.object_list[i] = {
            'unit': unit,
            'renter': renter,
            'is_paid': uc.is_paid if uc else False,
            'is_notified': uc.send_notification if uc else False,
            'send_sms': uc.send_sms if uc else False,
            'sms_date': uc.send_sms_date if uc else None,
            'total_charge': uc.total_charge_month if uc else 0,
        }

    context = {
        'charge': charge,
        'page_obj': page_units,  # حالا فقط واحدهای دارای UnifiedCharge هستند
        # 'paginator': paginator,
    }
    return render(request, 'middleCharge/notify_fix_variable_charge_template.html', context)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_remove_send_notification_fix_variable(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'فقط درخواست‌های POST مجاز است.'}, status=400)

    charge = get_object_or_404(ChargeFixVariable, id=pk, user=request.user)
    selected_units = request.POST.getlist('units[]')

    if not selected_units:
        return JsonResponse({'warning': 'هیچ واحدی انتخاب نشده است.'})

    try:
        with transaction.atomic():
            content_type = ContentType.objects.get_for_model(ChargeFixVariable)

            # رکوردهایی که باید غیرفعال شوند
            if selected_units == ['all']:
                qs = UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    is_paid=False,
                    send_notification=True  # فقط رکوردهای فعال
                )
            else:
                try:
                    selected_unit_ids = [int(uid) for uid in selected_units]
                except ValueError:
                    return JsonResponse({'error': 'شناسه واحد نامعتبر است.'}, status=400)

                qs = UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    unit_id__in=selected_unit_ids,
                    is_paid=False,
                    send_notification=True  # فقط رکوردهای فعال
                )

            updated_count = qs.update(
                send_notification=False,
                send_notification_date=None
            )

            # اگر هیچ رکوردی با send_notification=True باقی نماند → شارژ را غیرفعال کن
            if not UnifiedCharge.objects.filter(
                    content_type=content_type,
                    object_id=charge.id,
                    send_notification=True
            ).exists():
                charge.send_notification = False
                charge.save()

        if updated_count:
            return JsonResponse({'success': f'{updated_count} اطلاعیه غیرفعال شد.'})
        else:
            return JsonResponse({'info': 'رکوردی برای غیرفعال کردن یافت نشد.'})

    except Exception as e:
        return JsonResponse({'error': f'خطایی هنگام غیرفعال کردن اطلاعیه‌ها رخ داد: {str(e)}'}, status=500)


# ================================================================================================

# class MiddleExpenseCharge(CreateView):
#     model = ChargeByExpense
#     form_class = ExpenseChargeForm
#     template_name = "middleCharge/variable_fix_charge_template.html"
#     success_url = reverse_lazy('middle_add_expense_charge')
#
#     def get_initial(self):
#         # گرفتن دسته‌بندی‌ها
#         try:
#             power_category = ExpenseCategory.objects.get(title='برق', user=self.request.user)
#         except ExpenseCategory.DoesNotExist:
#             power_category = None
#
#         try:
#             water_category = ExpenseCategory.objects.get(title='آب', user=self.request.user)
#         except ExpenseCategory.DoesNotExist:
#             water_category = None
#
#         try:
#             gas_category = ExpenseCategory.objects.get(title='گاز', user=self.request.user)
#         except ExpenseCategory.DoesNotExist:
#             gas_category = None
#
#         # جمع هزینه‌ها
#         total_power = Expense.objects.filter(category=power_category).aggregate(total=Sum('amount'))[
#                           'total'] or 0 if power_category else 0
#         total_water = Expense.objects.filter(category=water_category).aggregate(total=Sum('amount'))[
#                           'total'] or 0 if water_category else 0
#         total_gas = Expense.objects.filter(category=gas_category).aggregate(total=Sum('amount'))[
#                         'total'] or 0 if gas_category else 0
#
#         return {
#             'unit_power_amount': total_power,
#             'unit_water_amount': total_water,
#             'unit_gas_amount': total_gas,
#         }
#
#     def form_valid(self, form):
#         charge = form.save(commit=False)
#         charge.user = self.request.user
#         charge.save()
#
#         units = Unit.objects.filter(is_active=True, user__manager=self.request.user)
#         if not units.exists():
#             messages.error(self.request, "هیچ واحد فعالی پیدا نشد.")
#             return redirect('middle_manage_unit')
#
#         unified_charges = []
#
#         for unit in units:
#             total_amount = (
#                 (form.cleaned_data.get('unit_power_amount') or 0) +
#                 (form.cleaned_data.get('unit_water_amount') or 0) +
#                 (form.cleaned_data.get('unit_gas_amount') or 0) +
#                 (form.cleaned_data.get('civil') or 0) +
#                 (form.cleaned_data.get('other_cost_amount') or 0)
#             )
#
#             unified_charges.append(
#                 UnifiedCharge(
#                     user=self.request.user,
#                     unit=unit,
#                     main_charge=charge,
#                     charge_type=ChargeByExpense.charge_type,
#                     amount=total_amount,
#                     base_charge=total_amount,
#                     civil=form.cleaned_data.get('civil') or 0,
#                     other_cost_amount=form.cleaned_data.get('other_cost_amount') or 0,
#                     penalty_percent=form.cleaned_data.get('payment_penalty_amount') or 0,
#                     penalty_amount=0,
#                     total_charge_month=total_amount,
#                     extra_parking_price=0,
#                     details=form.cleaned_data.get('details') or '',
#                     title=form.cleaned_data.get('name'),
#                     send_notification=False,
#                     send_notification_date=None,
#                     payment_deadline_date=form.cleaned_data.get('payment_deadline'),
#                     content_type=ContentType.objects.get_for_model(ChargeByExpense),
#                     object_id=charge.id
#                 )
#             )
#
#         UnifiedCharge.objects.bulk_create(unified_charges)
#         messages.success(self.request, "شارژ هزینه‌ها با موفقیت ثبت شد.")
#         return super().form_valid(form)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#
#         # جمع کل هر شارژ
#         charges = ChargeByExpense.objects.annotate(
#             notified_count=Count('unified_charges', filter=Q(unified_charges__send_notification=True)),
#             total_units=Count('unified_charges')
#         ).order_by('-created_at')
#
#         for charge in charges:
#             charge.total_power = charge.unit_power_amount or 0
#             charge.total_water = charge.unit_water_amount or 0
#             charge.total_gas = charge.unit_gas_amount or 0
#             charge.total_civil = charge.civil or 0
#             charge.total_other = charge.other_cost_amount or 0
#
#         context['charges'] = charges
#         context['unit_count'] = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
#         return context


# ==============================================================================================

def get_all_base_charges(user):
    all_charges = chain(
        FixCharge.objects.filter(user=user),
        AreaCharge.objects.filter(user=user),
        PersonCharge.objects.filter(user=user),
        FixPersonCharge.objects.filter(user=user),
        FixAreaCharge.objects.filter(user=user),
        ChargeByPersonArea.objects.filter(user=user),
        ChargeByFixPersonArea.objects.filter(user=user),
        ChargeFixVariable.objects.filter(user=user),
    )
    return sorted(all_charges, key=lambda x: x.created_at, reverse=True)


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def base_charge_list(request):
    query = request.GET.get('q', '').strip()
    paginate = int(request.GET.get('paginate', 20))

    charges = get_all_base_charges(request.user)

    if query:
        charges = [
            c for c in charges
            if (
                    query.lower() in (c.name or '').lower()
                    or query.lower() in (getattr(c, 'name', '') or '').lower()
            )
        ]

    charges_data = []

    for charge in charges:
        data = charge.to_dict()

        # 🔔 تعداد واحدهای نوتیفای‌شده
        data['notified_count'] = (
            charge.unified_charges
            .filter(
                send_notification=True,
                send_notification_date__isnull=False,
                unit__isnull=False
            )
            .values_list('unit_id', flat=True)
            .distinct()
            .count()
        )
        data['paid_count'] = (
            charge.unified_charges
            .filter(
                is_paid=True,
                unit__isnull=False
            )
            .values_list('unit_id', flat=True)
            .distinct()
            .count()
        )

        charges_data.append(data)

    # 📄 pagination
    paginator = Paginator(charges_data, paginate)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'middleCharge/middle_charges_list.html',
        {
            'charges': page_obj,  # 👈 مهم (برای loop)
            'query': query,
            'paginate': paginate,
            'page_obj': page_obj,
        }
    )


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def middle_base_charges_pdf(request):
    house = None
    if request.user.is_authenticated:
        house = MyHouse.objects.filter(
            residents=request.user
        ).order_by('-created_at').first()

    managed_users = request.user.managed_users.all()
    unit_count = Unit.objects.filter(
        is_active=True,
        user__in=managed_users
    ).count()

    # 🔹 همان منبع ویوی لیست
    charges = get_all_base_charges(request.user)

    # 🔍 جستجو
    query = request.GET.get('q', '').strip()
    if query:
        charges = [
            c for c in charges
            if (
                    query.lower() in (c.name or '').lower() or
                    query.lower() in (getattr(c, 'details', '') or '').lower()
            )
        ]

    charges_data = []

    for charge in charges:
        data = charge.to_dict()

        # ✅ محاسبه notified_count (دقیقاً مثل base_charge_list)
        data['notified_count'] = (
            charge.unified_charges
            .filter(
                send_notification=True,
                send_notification_date__isnull=False,
                unit__isnull=False
            )
            .values_list('unit_id', flat=True)
            .distinct()
            .count()
        )

        charges_data.append(data)

    # 🧾 HTML برای PDF
    html_string = render_to_string(
        'middleCharge/middle_charges_list_pdf.html',
        {
            'charges': charges_data,
            'query': query,
            'today': datetime.now(),
            'house': house,
            'unit_count': unit_count,
            'font_url': request.build_absolute_uri('/static/fonts/Vazir.ttf')
        }
    )

    # 🎨 فونت و CSS
    font_url = request.build_absolute_uri(static('fonts/Vazir.ttf'))
    css = CSS(string=f"""
        @page {{ size: A4 landscape; margin: 1cm; }}
        @font-face {{
            font-family: 'Vazir';
            src: url('{font_url}');
        }}
        body {{
            font-family: 'Vazir', sans-serif;
        }}
    """)

    html = HTML(string=html_string)
    pdf_file = html.write_pdf(stylesheets=[css])

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="charge_main.pdf"'
    return response


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_base_charges_excel(request):
    managed_users = request.user.managed_users.all()
    unit_count = Unit.objects.filter(
        is_active=True,
        user__in=managed_users
    ).count()

    # 🔹 منبع یکسان با HTML و PDF
    charges = get_all_base_charges()

    # 🔍 جستجو
    query = request.GET.get('q', '').strip()
    if query:
        charges = [
            c for c in charges
            if (
                    query.lower() in (c.name or '').lower()
                    or query.lower() in (getattr(c, 'details', '') or '').lower()
            )
        ]

    # -------------------------
    # Create Excel workbook
    # -------------------------
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Main Charges"
    ws.sheet_view.rightToLeft = True

    # Title
    title_cell = ws.cell(row=1, column=1, value="لیست شارژهای اصلی ساختمان")
    title_cell.font = Font(bold=True, size=16)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)

    # Headers
    headers = ['#', 'عنوان', 'تاریخ ثبت', 'جریمه دیرکرد(%)', 'مهلت پرداخت', 'توضیحات', 'اعلام شارژ']
    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")
    header_font = Font(bold=True)

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill

    # Data
    row = 3
    for index, charge in enumerate(charges, start=1):
        notified_count = (
            charge.unified_charges
            .filter(
                send_notification=True,
                send_notification_date__isnull=False,
                unit__isnull=False
            )
            .values_list('unit_id', flat=True)
            .distinct()
            .count()
        )

        ws.cell(row=row, column=1, value=index)
        ws.cell(row=row, column=2, value=charge.name)
        ws.cell(row=row, column=3, value=show_jalali(charge.created_at))
        ws.cell(row=row, column=4, value=getattr(charge, 'payment_penalty_amount', None))
        ws.cell(row=row, column=5, value=show_jalali(getattr(charge, 'payment_deadline', None)))
        ws.cell(row=row, column=6, value=getattr(charge, 'details', ''))
        ws.cell(
            row=row,
            column=7,
            value=f"{notified_count} از {unit_count} واحد"
        )
        row += 1

    # -------------------------
    # Response
    # -------------------------
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=main_charges.xlsx'
    wb.save(response)
    return response


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def charge_units_list(request, app_label, model_name, charge_id):
    model = apps.get_model(app_label, model_name)
    charge = get_object_or_404(model, id=charge_id)

    # 🔥 بررسی نوع مدل و گرفتن unified charges
    if hasattr(charge, 'unified_charges'):
        # مدل اصلی شارژ → گرفتن همه UnifiedCharge ها
        unified_qs = charge.unified_charges.all()
    elif model_name.lower() == 'unifiedcharge':
        unified_qs = model.objects.filter(
            content_type=charge.content_type,
            object_id=charge.object_id
        )
    else:
        # هر حالت غیرمنتظره
        unified_qs = model.objects.none()

    # 🔥 آپدیت جریمه همه UnifiedCharge ها
    for uc in unified_qs:
        if hasattr(uc, 'update_penalty'):
            uc.update_penalty(save=True)

    # -------------------------
    # 🔍 جستجو
    # -------------------------
    query = request.GET.get('q', '').strip()

    unified_charges = unified_qs.filter(
        send_notification_date__isnull=False
    ).select_related('unit', 'unit__user')

    if query:
        search_q = (
                Q(unit__unit__icontains=query) |
                Q(unit__user__full_name__icontains=query)
        )

        # اگر عدد بود → جستجو روی مقادیر عددی شارژ
        if query.isdigit():
            search_q |= (
                    Q(penalty_amount=query) |
                    Q(total_charge_month=query) |
                    Q(base_charge=query)
            )

        unified_charges = unified_charges.filter(search_q)

    unified_charges = unified_qs.filter(
        send_notification_date__isnull=False
    ).select_related('unit', 'unit__user').order_by('unit__unit')

    # -------------------------
    # 📄 pagination
    # -------------------------
    paginate = int(request.GET.get('paginate', 20))
    paginator = Paginator(unified_charges, paginate)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # واحدها (مطابق صفحه‌بندی)
    units = [uc.unit for uc in page_obj if uc.unit]

    return render(
        request,
        'middleCharge/middle_charges_detail.html',
        {
            'charge': charge,
            'units': units,
            'unified_charges': page_obj,
            'query': query,
            'paginate': paginate,
            'page_obj': page_obj,
            'app_label': app_label,
            'model_name': model_name,
        }
    )


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def charge_units_list_pdf(request, app_label, model_name, charge_id):
    model = apps.get_model(app_label, model_name)
    charge = get_object_or_404(model, id=charge_id)
    house = None
    if request.user.is_authenticated:
        house = MyHouse.objects.filter(residents=request.user).order_by('-created_at').first()

    unified_qs = charge.unified_charges.all()

    # 🔍 جستجو
    query = request.GET.get('q', '').strip()

    unified_charges = unified_qs.filter(
        send_notification_date__isnull=False
    ).select_related('unit', 'unit__user')

    if query:
        search_q = (
                Q(unit__unit__icontains=query) |
                Q(unit__user__full_name__icontains=query)
        )

        try:
            value = Decimal(query)
            search_q |= (
                    Q(penalty_amount=value) |
                    Q(total_charge_month=value) |
                    Q(base_charge=value)
            )
        except:
            pass

        unified_charges = unified_charges.filter(search_q)

    unified_charges = unified_charges.order_by('-created_at')

    html_string = render_to_string(
        'middleCharge/middle_charges_detail_pdf.html',
        {
            'charge': charge,
            'unified_charges': unified_charges,
            'query': query,
            'today': datetime.now(),
            'house': house,
            'font_url': request.build_absolute_uri('/static/fonts/Vazir.ttf')

        }
    )

    font_url = request.build_absolute_uri(static('fonts/Vazir.ttf'))
    css = CSS(string=f"""
        @page {{ size: A4 landscape; margin: 1cm; }}
        @font-face {{
            font-family: 'Vazir';
            src: url('{font_url}');
        }}
        body {{
            font-family: 'Vazir', sans-serif;
        }}
    """)

    pdf = HTML(string=html_string).write_pdf(stylesheets=[css])

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="charge_units.pdf"'
    return response


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def charge_units_list_excel(request, app_label, model_name, charge_id):
    model = apps.get_model(app_label, model_name)
    charge = get_object_or_404(model, id=charge_id)

    unified_qs = charge.unified_charges.all()

    # 🔍 جستجو
    query = request.GET.get('q', '').strip()

    unified_charges = unified_qs.filter(
        send_notification_date__isnull=False
    ).select_related('unit', 'unit__user')

    if query:
        search_q = (
                Q(unit__unit__icontains=query) |
                Q(unit__user__full_name__icontains=query)
        )

        try:
            value = Decimal(query)
            search_q |= (
                    Q(penalty_amount=value) |
                    Q(total_charge_month=value) |
                    Q(base_charge=value)
            )
        except:
            pass

        unified_charges = unified_charges.filter(search_q)

    unified_charges = unified_charges.order_by('-created_at')

    # Excel
    # -------------------------
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Charge Units"
    ws.sheet_view.rightToLeft = True

    # عنوان اصلی
    title_cell = ws.cell(row=1, column=1, value="لیست تراکنش های من")
    title_cell.font = Font(bold=True, size=18)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=9)  # 9 ستون

    # هدرها
    headers = [
        '#', 'واحد', 'مالک / مستاجر', 'مبلغ پایه', 'جریمه',
        'مبلغ نهایی', 'تاریخ اعلام', 'مهلت پرداخت', 'وضعیت پرداخت'
    ]
    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")
    header_font = Font(bold=True, color="000000")
    for col_num, column_title in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_num, value=column_title)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # داده‌ها
    row = 3  # داده‌ها از ردیف بعد از هدر شروع می‌شوند
    for index, uc in enumerate(unified_charges, start=1):
        ws.cell(row=row, column=1, value=index)
        ws.cell(row=row, column=2, value=uc.title)
        ws.cell(row=row, column=3, value=uc.unit.get_label())
        ws.cell(row=row, column=4, value=uc.base_charge)
        ws.cell(row=row, column=5, value=uc.penalty_amount)
        ws.cell(row=row, column=6, value=uc.total_charge_month)
        ws.cell(row=row, column=7, value=show_jalali(uc.send_notification_date))
        ws.cell(row=row, column=8, value=show_jalali(uc.payment_deadline_date))
        ws.cell(row=row, column=9, value="پرداخت شده" if uc.is_paid else "پرداخت نشده")
        row += 1

    # پاسخ Excel
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=middle_charge_units.xlsx'
    wb.save(response)
    return response


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def charge_units_pdf(request, charge_id):
    charge = get_object_or_404(UnifiedCharge, id=charge_id)
    units = Unit.objects.filter(unified_charges=charge, is_active=True).order_by('unit')
    house = None
    if request.user.is_authenticated:
        house = MyHouse.objects.filter(residents=request.user).order_by('-created_at').first()
    bank = Bank.get_default(request.user, house)
    html_string = render_to_string('middleCharge/single_charge_pdf.html', {
        'charge': charge,
        'units': units,
        'house': house,
        'bank': bank,
        'font_url': request.build_absolute_uri('/static/fonts/Vazir.ttf')
    })
    css = CSS(string=f"""
        @page {{ size: A5 portrait; margin: 0.8cm; }}
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


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def all_invoices_pdf(request, app_label, model_name, charge_id):
    house = None
    if request.user.is_authenticated:
        house = MyHouse.objects.filter(residents=request.user).order_by('-created_at').first()

    model = apps.get_model(app_label, model_name)
    charge = get_object_or_404(model, id=charge_id)

    charges = (
        charge.unified_charges
        .filter(send_notification_date__isnull=False)
        .select_related('unit', 'unit__user')
        .order_by('unit__unit')
    )
    bank = Bank.get_default(request.user, house)

    html_string = render_to_string(
        'middleCharge/all_invoices_pdf.html',
        {
            'charge': charge,
            'charges': charges,
            'today': datetime.now(),
            'house': house,
            'bank': bank,
            'font_url': request.build_absolute_uri('/static/fonts/Vazir.ttf')
        }
    )

    font_base = request.build_absolute_uri('/static/fonts/')
    css = CSS(string=f"""
        @page {{
            size: A5 portrait;
            margin: 1cm;
        }}
        
    @font-face {{
        font-family: 'Vazir';
        src: url('{font_base}Vazir-Regular.ttf') format('truetype');
        font-weight: 400;
    }}

    @font-face {{
        font-family: 'Vazir';
        src: url('{font_base}Vazir-Bold.ttf') format('truetype');
        font-weight: 700;
    }}


    body {{
        font-family: 'Vazir';
        direction: rtl;
    }}

    h1, h2, h3 {{
        font-weight: 700;
    }}

    .page-break {{
        page-break-after: always;
    }}
""")

    pdf = HTML(string=html_string).write_pdf(stylesheets=[css])

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="all_invoices.pdf"'
    return response


# =================================================================================================
def add_sms_credit(request):
    current_credit = (
            SmsCredit.objects
            .filter(user=request.user, is_paid=True)
            .aggregate(total=Sum('amount'))['total']
            or Decimal('0')
    )
    context = {
        'current_credit': current_credit
    }
    return render(request, 'middle_admin/middle_credit_sms.html', context)


@method_decorator(middle_admin_required, name='dispatch')
class MiddleSmsManagementView(CreateView):
    model = SmsManagement
    template_name = 'middle_admin/middle_register_sms.html'
    form_class = SmsForm
    success_url = reverse_lazy('middle_register_sms')

    def form_valid(self, form):
        sms = form.save(commit=False)
        sms.user = self.request.user

        try:
            sms.house = MyHouse.objects.filter(user=self.request.user).first()
            sms.save()
            self.object = sms
            messages.success(self.request, 'پیامک موفقیت ثبت گردید')
            return super().form_valid(form)
        except:
            messages.error(self.request, 'خطا در ثبت!')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['all_sms'] = SmsManagement.objects.filter(user=self.request.user, send_notification=False).order_by(
            '-created_at')
        context['units'] = Unit.objects.all()

        return context


@method_decorator(middle_admin_required, name='dispatch')
class MiddleSmsUpdateView(UpdateView):
    model = SmsManagement
    template_name = 'middle_admin/middle_register_sms.html'
    form_class = SmsForm
    success_url = reverse_lazy('middle_register_sms')

    def form_valid(self, form):
        edit_instance = form.instance
        self.object = form.save(commit=False)
        messages.success(self.request, 'پیامک با موفقیت ویرایش گردید!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['all_sms'] = SmsManagement.objects.filter(
            is_active=True,
            user=self.request.user,
            send_notification=False
        ).order_by('-created_at')
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_sms_delete(request, pk):
    sms = get_object_or_404(SmsManagement, id=pk)
    print(sms.id)

    try:
        sms.delete()
        messages.success(request, 'پیامک با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('middle_register_sms'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_show_send_sms_form(request, pk):
    sms = get_object_or_404(SmsManagement, id=pk, user=request.user)
    units = Unit.objects.filter(is_active=True, user__manager=request.user).prefetch_related('renters').order_by('unit')

    units_with_details = []
    for unit in units:
        active_renter = unit.renters.filter(renter_is_active=True).first()
        units_with_details.append({
            'unit': unit,
            'active_renter': active_renter
        })

    return render(request, 'middle_admin/middle_send_sms.html', {
        'sms': sms,
        'units_with_details': units_with_details,
        # 'units_to_notify': units_to_notify
    })


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_send_sms(request, pk):
    sms = get_object_or_404(SmsManagement, id=pk, user=request.user)

    # ❌ اگر قبلاً ارسال شده
    if sms.send_notification:
        messages.warning(request, 'این پیامک قبلاً ارسال شده است.')
        return redirect('middle_sms_management')

    if request.method == "POST":

        selected_units = request.POST.getlist('units')
        if not selected_units:
            messages.warning(request, 'هیچ واحدی انتخاب نشده است.')
            return redirect('middle_register_sms')

        units_qs = Unit.objects.filter(
            is_active=True,
            user__manager=request.user
        )

        if 'all' in selected_units:
            units_to_notify = units_qs
        else:
            units_to_notify = units_qs.filter(id__in=selected_units)

        if not units_to_notify.exists():
            messages.warning(request, 'هیچ واحد معتبری برای ارسال پیامک پیدا نشد.')
            return redirect('middle_register_sms')

        # 1️⃣ محاسبه تعداد پیامک
        unit_count = units_to_notify.count()
        sms_per_message = sms.sms_count
        total_sms_needed = unit_count * sms_per_message

        # 2️⃣ محاسبه مبلغ
        sms_price = Decimal(str(settings.SMS_PRICE))
        total_price = total_sms_needed * sms_price

        # 3️⃣ محاسبه شارژ موجود
        total_credit = SmsCredit.objects.filter(
            user=request.user,
            is_paid=True
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        if total_credit < total_price:
            messages.error(
                request,
                f'شارژ پیامکی کافی نیست. مبلغ مورد نیاز: {total_price:,} تومان'
            )
            return redirect('middle_register_sms')

        # 4️⃣ عملیات اتمیک
        notified_units = []

        with transaction.atomic():

            # 🔻 کسر شارژ (FIFO)
            remaining_price = total_price
            credits = SmsCredit.objects.filter(
                user=request.user,
                is_paid=True,
                amount__gt=0
            ).order_by('created_at')

            for credit in credits:
                if remaining_price <= 0:
                    break

                if credit.amount >= remaining_price:
                    credit.amount -= remaining_price
                    remaining_price = 0
                else:
                    remaining_price -= credit.amount
                    credit.amount = 0

                credit.save()

            # 5️⃣ ارسال پیامک
            for unit in units_to_notify:
                if unit.user and unit.user.mobile:
                    helper.send_sms_to_user(
                        mobile=unit.user.mobile,
                        message=sms.message,
                        full_name=unit.user.full_name,
                    )
                    notified_units.append(unit)

            # 6️⃣ ثبت نهایی
            if notified_units:
                # 6️⃣ ثبت نهایی اطلاعات پیامک
                sms.total_units_sent = unit_count
                sms.sms_per_message = sms_per_message
                sms.total_sms_sent = total_sms_needed
                sms.total_price = total_price

                sms.notified_units.set(notified_units)
                sms.send_notification = True
                sms.send_notification_date = timezone.now().date()
                sms.save()

        messages.success(
            request,
            f'پیامک با موفقیت برای {len(notified_units)} واحد ارسال شد.'
        )
        return redirect('middle_sms_management')

    # GET
    units_with_details = Unit.objects.filter(is_active=True)
    return render(request, 'middle_admin/middle_send_sms.html', {
        'sms': sms,
        'units_with_details': units_with_details,
    })


@method_decorator(middle_admin_required, name='dispatch')
class MiddleSmsListView(ListView):
    model = SmsManagement
    template_name = 'middle_admin/middle_sms_management.html'
    context_object_name = 'all_sms'

    def get_paginate_by(self, queryset):
        paginate = self.request.GET.get('paginate')
        if paginate == '1000':
            return None  # نمایش همه آیتم‌ها
        return int(paginate or 20)

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        queryset = SmsManagement.objects.filter(
            user=self.request.user,
            is_active=True,
            send_notification=True,
        )
        if query:
            queryset = queryset.filter(
                Q(subject__icontains=query) |
                Q(message__icontains=query)
            )
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['paginate'] = self.request.GET.get('paginate', '20')
        context['sms_list'] = SmsManagement.objects.filter(user=self.request.user).annotate(
            unit_number=F('notified_units__unit'),
            user_full_name=F('notified_units__user__full_name')
        )
        return context


# =============================================================================================
@login_required(login_url=settings.LOGIN_URL_ADMIN)
def waive_penalty_bulk(request):
    try:
        ids = request.POST.getlist('charge_ids[]')
        if not ids:
            return JsonResponse({'success': False, 'error': 'هیچ موردی انتخاب نشده'}, status=400)

        charges = UnifiedCharge.objects.filter(id__in=ids, is_paid=False)

        if not charges.exists():
            return JsonResponse({'success': False, 'error': 'شارژی برای حذف جریمه یافت نشد'}, status=400)

        titles = []
        with transaction.atomic():
            for charge in charges:
                result = charge.waive_penalty(request.user)
                if result:
                    titles.append(result['title'])

        first_charge = charges.first()
        # app_label = first_charge._meta.app_label
        # model_name = first_charge._meta.model_name

        redirect_url = reverse(
            'charge_units_list',  # همونی که داری
            args=[
                first_charge._meta.app_label,
                first_charge._meta.model_name,
                first_charge.id  # ❗ حتماً باید باشد
            ]
        )

        return JsonResponse({
            'success': True,
            'titles': titles,
            'redirect_url': redirect_url,
            'message': 'جریمه با موفقیت حذف شد'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def restore_penalty_bulk(request):
    try:
        ids = request.POST.getlist('charge_ids[]')
        if not ids:
            return JsonResponse({'success': False, 'error': 'هیچ موردی انتخاب نشده'}, status=400)

        charges = UnifiedCharge.objects.filter(id__in=ids, is_paid=False)

        if not charges.exists():
            return JsonResponse({'success': False, 'error': 'شارژی برای بازگردانی جریمه یافت نشد'}, status=400)

        titles = []
        with transaction.atomic():
            for charge in charges:
                result = charge.restore_penalty()
                if result:
                    titles.append(result['title'])

        first_charge = charges.first()
        redirect_url = reverse(
            'charge_units_list',  # همونی که داری
            args=[
                first_charge._meta.app_label,
                first_charge._meta.model_name,
                first_charge.id  # ❗ حتماً باید باشد
            ]
        )

        return JsonResponse({
            'success': True,
            'titles': titles,
            'redirect_url': redirect_url,
            'message': 'جریمه با موفقیت بازگردانده شد'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
