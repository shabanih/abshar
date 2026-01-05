import io
import os
import time
from datetime import timezone, datetime
from decimal import Decimal
from itertools import chain

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.apps import apps
from django.conf.urls.static import static
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.utils import timezone
import jdatetime
import openpyxl
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test, login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction, IntegrityError, models
from django.db.models import ProtectedError, Count, Q, Sum, F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template, render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, UpdateView, DetailView, ListView, TemplateView
from openpyxl.styles import PatternFill, Alignment, Font
from pypdf import PdfWriter
from sweetify import sweetify
from weasyprint import CSS, HTML

from admin_panel import helper
from admin_panel.forms import announcementForm, BankForm, UnitForm, ExpenseCategoryForm, ExpenseForm, \
    IncomeCategoryForm, IncomeForm, ReceiveMoneyForm, PayerMoneyForm, PropertyForm, MaintenanceForm, FixChargeForm, \
    FixAreaChargeForm, AreaChargeForm, PersonChargeForm, FixPersonChargeForm, PersonAreaChargeForm, \
    PersonAreaFixChargeForm, VariableFixChargeForm, MyHouseForm, SmsForm, RenterAddForm
from admin_panel.models import Announcement, ExpenseCategory, Expense, Fund, ExpenseDocument, IncomeCategory, Income, \
    IncomeDocument, ReceiveMoney, ReceiveDocument, PayMoney, PayDocument, Property, PropertyDocument, Maintenance, \
    MaintenanceDocument, FixCharge, AreaCharge, PersonCharge, \
    FixAreaCharge, FixPersonCharge, ChargeByPersonArea, \
    ChargeByFixPersonArea, ChargeFixVariable, SmsManagement, \
    UnifiedCharge, Penalty
from admin_panel.services.calculators import CALCULATORS
from admin_panel.views import admin_required
from notifications.models import Notification, SupportUser
from polls.templatetags.poll_extras import show_jalali

from user_app.models import Bank, Unit, User, Renter, MyHouse


def middle_admin_required(view_func):
    return user_passes_test(
        lambda u: u.is_authenticated and getattr(u, 'is_middle_admin', False),
        login_url=settings.LOGIN_URL_MIDDLE_ADMIN
    )(view_func)


@middle_admin_required
def middle_admin_dashboard(request):
    announcements = Announcement.objects.filter(is_active=True, user=request.user).order_by('-created_at')[:3]
    unit_count = Unit.objects.filter(user__manager=request.user).count()
    fund_amount = Fund.objects.filter(user__manager=request.user)
    tickets = SupportUser.objects.filter(user__manager=request.user).order_by('-created_at')[:5]
    context = {
        'announcements': announcements,
        'unit_count': unit_count,
        'fund_amount': fund_amount,
        'tickets': tickets
    }
    return render(request, 'middleShared/home_template.html', context)


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


def logout__middle_admin(request):
    logout(request)
    return redirect('index')


def site_header_component(request):
    context = {
        'user': request.user,
    }
    return render(request, 'middleShared/notification_template.html', context)


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
    success_url = reverse_lazy('middle_send_announcement')

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        # announce_instance = form.instance
        messages.success(self.request, 'اطلاعیه با موفقیت ثبت گردید!')
        return super(MiddleAnnouncementView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['announcements'] = Announcement.objects.filter(user=self.request.user).order_by('-created_at')
        return context


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
    template_name = 'admin_panel/announcement.html'
    form_class = announcementForm
    success_url = reverse_lazy('middle_announcement')

    def form_valid(self, form):
        edit_instance = form.instance
        self.object = form.save(commit=False)
        self.object.user = self.request.user
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
        # ذخیره بانک
        form.instance.user = self.request.user
        response = super().form_valid(form)
        bank = self.object  # بانکی که تازه ساخته شده

        # اگر موجودی اولیه دارد → Fund افتتاحیه
        if bank.initial_fund and bank.initial_fund > 0:
            content_type = ContentType.objects.get_for_model(Bank)

            # جلوگیری از ثبت تکراری
            if not Fund.objects.filter(
                    content_type=content_type,
                    object_id=bank.id,
                    payment_description__icontains='افتتاحیه'
            ).exists():
                Fund.objects.create(
                    user=self.request.user,
                    bank=bank,
                    payer_name=f'{bank.account_holder_name}',
                    receiver_name='صندوق',
                    payment_gateway='پرداخت الکترونیک',
                    content_type=content_type,
                    object_id=bank.id,
                    is_initial=True,
                    amount=Decimal(bank.initial_fund),
                    debtor_amount=Decimal(bank.initial_fund),
                    creditor_amount=Decimal(0),
                    payment_date=bank.create_at.date(),
                    payment_description=f'افتتاحیه حساب بانک {bank.bank_name}'
                )
            messages.success(self.request, 'حساب بانکی با موفقیت ثبت گردید!')
            return super().form_valid(form)

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

        form.instance.user = self.request.user
        response = super().form_valid(form)

        bank.refresh_from_db()  # مقدار جدید
        new_initial_fund = bank.initial_fund

        # اگر موجودی اولیه تغییر نکرده → کاری نکن
        if old_initial_fund == new_initial_fund:
            messages.success(self.request, 'اطلاعات حساب بانکی با موفقیت ویرایش گردید!')
            return response

        # پیدا کردن Fund افتتاحیه
        initial_fund = Fund.objects.filter(
            bank=bank,
            is_initial=True
        ).first()

        # اگر Fund افتتاحیه وجود دارد → ویرایش
        if initial_fund:
            diff = Decimal(new_initial_fund) - Decimal(old_initial_fund)

            initial_fund.debtor_amount = Decimal(new_initial_fund)
            initial_fund.creditor_amount = Decimal(0)
            initial_fund.amount = Decimal(new_initial_fund)
            initial_fund.save()

            # 🔁 بازمحاسبه مانده‌ها از این سند به بعد
            Fund.recalc_final_amounts_from(initial_fund)

        messages.success(self.request, 'اطلاعات حساب بانکی و موجودی افتتاحیه با موفقیت ویرایش شد!')
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
    success_url = reverse_lazy('middle_manage_unit')
    template_name = 'middle_unit_templates/unit_register.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            with transaction.atomic():
                is_renter = str(form.cleaned_data.get('is_renter')).lower() == 'true'

                # فقط یک موبایل داریم (یوزرنیم)
                # تعیین شماره موبایل مناسب
                if is_renter:
                    mobile = form.cleaned_data.get('renter_mobile')
                else:
                    mobile = form.cleaned_data.get('owner_mobile')

                password = form.cleaned_data.get('password')
                full_name = (
                    form.cleaned_data.get('renter_name')
                    if is_renter
                    else form.cleaned_data.get('owner_name')
                )

                # بررسی وجود کاربر با همان موبایل
                if User.objects.filter(mobile=mobile).exists():
                    form.add_error('mobile', 'کاربری با این شماره موبایل قبلاً ثبت شده است.')
                    return self.form_invalid(form)

                # ساخت کاربر
                user = User.objects.create(
                    mobile=mobile,
                    username=mobile,
                    full_name=full_name,
                    is_staff=True,
                    is_active=True,
                    manager=self.request.user,
                    otp_create_time=timezone.now(),
                )

                # ست کردن رمز عبور
                user.set_password(password)
                user.save()

                # اتصال به خانه
                house = MyHouse.objects.filter(user=self.request.user).first()
                if house:
                    house.residents.add(user)

                # ساخت واحد
                unit = form.save(commit=False)
                unit.user = user
                unit.is_renter = is_renter
                unit.save()

                # اگر مستاجر داریم → فقط پروفایل Renter
                first_charge_renter = 0
                if is_renter:
                    Renter.objects.create(
                        unit=unit,
                        user=user,
                        renter_name=form.cleaned_data.get('renter_name'),
                        renter_mobile=mobile,
                        renter_national_code=form.cleaned_data.get('renter_national_code'),
                        renter_people_count=form.cleaned_data.get('renter_people_count'),
                        start_date=form.cleaned_data.get('start_date'),
                        end_date=form.cleaned_data.get('end_date'),
                        contract_number=form.cleaned_data.get('contract_number'),
                        estate_name=form.cleaned_data.get('estate_name'),
                        first_charge_renter=form.cleaned_data.get('first_charge_renter') or 0,
                        renter_details=form.cleaned_data.get('renter_details'),
                        renter_is_active=True,
                        renter_payment_date=form.cleaned_data.get('renter_payment_date'),
                        renter_transaction_no=form.cleaned_data.get('renter_transaction_no'),

                    )

                # شارژ اولیه
                first_charge_owner = int(form.cleaned_data.get('first_charge_owner') or 0)
                first_charge_renter = int(form.cleaned_data.get('first_charge_renter') or 0)

                bank = Bank.objects.first()

                if is_renter and first_charge_renter > 0:
                    Fund.objects.create(
                        user=user,
                        unit=unit,
                        bank=bank,
                        debtor_amount=Decimal(first_charge_renter),
                        creditor_amount=0,
                        amount=Decimal(first_charge_renter),
                        is_initial=True,
                        payment_date=form.cleaned_data.get('renter_payment_date'),
                        payer_name=unit.get_label(),
                        payment_description='شارژ اولیه مستاجر',
                        payment_gateway='پرداخت الکترونیک',
                        content_object=unit,
                        transaction_no=form.cleaned_data.get('renter_transaction_no'),
                    )

                elif not is_renter and first_charge_owner > 0:
                    Fund.objects.create(
                        user=user,
                        unit=unit,
                        bank=bank,
                        debtor_amount=Decimal(first_charge_owner),
                        creditor_amount=0,
                        amount=Decimal(first_charge_owner),
                        is_initial=True,
                        payment_date=form.cleaned_data.get('owner_payment_date'),
                        payer_name=unit.get_label(),
                        payment_description='شارژ اولیه مالک',
                        payment_gateway='پرداخت الکترونیک',
                        content_object=unit,
                        transaction_no=form.cleaned_data.get('owner_transaction_no'),
                    )

            messages.success(self.request, 'واحد با موفقیت ثبت شد')
            return super().form_valid(form)

        except IntegrityError:
            form.add_error(None, 'خطا در ذخیره اطلاعات')
            return self.form_invalid(form)


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
                # غیرفعال کردن مالک قبلی
                # -------------------------
                if unit.user:
                    unit.user.is_active = False
                    unit.user.save()

                # -------------------------
                # غیرفعال کردن مستاجر قبلی
                # -------------------------
                Renter.objects.filter(
                    unit=unit,
                    renter_is_active=True
                ).update(renter_is_active=False)

                # -------------------------
                # گرفتن یا ساخت یوزر مستاجر
                # -------------------------
                renter_user, created = User.objects.get_or_create(
                    mobile=renter_mobile,
                    defaults={
                        'username': renter_mobile,
                        'full_name': form.cleaned_data['renter_name'],
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
                bank = form.cleaned_data.get('bank') or Bank.objects.first()

                # -------------------------
                # ایجاد مستاجر جدید
                # -------------------------
                Renter.objects.create(
                    unit=unit,
                    user=renter_user,
                    bank=bank,
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

                # -------------------------
                # بروزرسانی واحد
                # -------------------------
                unit.is_renter = True
                unit.save()

                # -------------------------
                # ایجاد شارژ اولیه مستاجر
                # -------------------------
                first_charge_renter = int(
                    form.cleaned_data.get('first_charge_renter') or 0
                )

                if first_charge_renter > 0:
                    Fund.objects.create(
                        user=renter_user,
                        unit=unit,
                        bank=bank,
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

    def get_initial(self):
        initial = super().get_initial()
        unit = self.object

        initial['mobile'] = unit.user.mobile
        renter = unit.renters.filter(renter_is_active=True).select_related('bank').first()
        if renter:
            initial.update({
                'is_renter': 'True',
                'bank': renter.bank,
                'renter_name': renter.renter_name,
                'renter_mobile': renter.renter_mobile,
                'renter_national_code': renter.renter_national_code,
                'renter_people_count': renter.renter_people_count,
                'start_date': renter.start_date,
                'end_date': renter.end_date,
                'contract_number': renter.contract_number,
                'estate_name': renter.estate_name,
                'first_charge_renter': renter.first_charge_renter,
                'renter_details': renter.renter_details,
                'renter_payment_date': renter.renter_payment_date,
                'renter_transaction_no': renter.renter_transaction_no,
            })
        else:
            initial['is_renter'] = 'False'
        return initial

    def form_valid(self, form):
        try:
            with transaction.atomic():
                unit = form.save(commit=False)

                # --------- 1️⃣ بررسی تغییر مالک ---------
                owner_changed = False
                if unit.pk:
                    owner_changed = (
                            self.object.owner_name != form.cleaned_data.get('owner_name') or
                            self.object.owner_mobile != form.cleaned_data.get('owner_mobile')
                    )
                    if owner_changed:
                        unit.renters.filter(renter_is_active=True).update(renter_is_active=False)
                        active_renter = None

                # --------- 2️⃣ تعیین مستاجر فعال ---------
                active_renter = unit.renters.filter(renter_is_active=True).first()

                # --------- 3️⃣ بروزرسانی User (مالک یا مستاجر) ---------
                if active_renter:
                    user = active_renter.user
                    new_mobile = form.cleaned_data.get('renter_mobile')
                    new_name = form.cleaned_data.get('renter_name')
                else:
                    user = unit.user
                    new_mobile = form.cleaned_data.get('mobile')
                    new_name = form.cleaned_data.get('owner_name')

                # بروزرسانی موبایل و بررسی تکراری بودن
                if new_mobile and new_mobile != user.mobile:
                    if User.objects.filter(mobile=new_mobile).exclude(pk=user.pk).exists():
                        field = 'renter_mobile' if active_renter else 'mobile'
                        form.add_error(field, 'این شماره موبایل قبلاً ثبت شده است.')
                        return self.form_invalid(form)
                    user.mobile = new_mobile
                    user.username = new_mobile

                if new_name:
                    user.full_name = new_name

                password = form.cleaned_data.get('password')
                if password:
                    user.set_password(password)

                user.save()

                # بروزرسانی session پسورد در صورت تغییر
                if password and self.request.user.pk == user.pk:
                    from django.contrib.auth import update_session_auth_hash
                    update_session_auth_hash(self.request, user)

                # --------- 4️⃣ ذخیره واحد ---------
                unit.is_renter = form.cleaned_data.get('is_renter', False)
                unit.save()

                # --------- 5️⃣ غیرفعال کردن مستاجر در صورت تغییر مالک ---------
                if owner_changed:
                    unit.renters.filter(renter_is_active=True).update(renter_is_active=False)
                    active_renter = None

                # --------- 6️⃣ ایجاد یا جایگزینی مستاجر (فقط اگر مالک تغییر نکرده باشد) ---------
                if unit.is_renter and not owner_changed:
                    renter_mobile = form.cleaned_data.get('renter_mobile')

                    if not active_renter:
                        # ایجاد مستاجر جدید
                        renter_user, _ = User.objects.get_or_create(
                            mobile=renter_mobile,
                            defaults={
                                'username': renter_mobile,
                                'full_name': form.cleaned_data.get('renter_name'),
                                'is_active': True
                            }
                        )
                        if password:
                            renter_user.set_password(password)
                            renter_user.save()

                        active_renter = Renter.objects.create(
                            unit=unit,
                            user=renter_user,
                            bank=form.cleaned_data.get('bank'),
                            renter_name=form.cleaned_data.get('renter_name'),
                            renter_mobile=renter_mobile,
                            renter_national_code=form.cleaned_data.get('renter_national_code'),
                            renter_people_count=form.cleaned_data.get('renter_people_count'),
                            start_date=form.cleaned_data.get('start_date'),
                            end_date=form.cleaned_data.get('end_date'),
                            contract_number=form.cleaned_data.get('contract_number'),
                            estate_name=form.cleaned_data.get('estate_name'),
                            first_charge_renter=form.cleaned_data.get('first_charge_renter') or 0,
                            renter_details=form.cleaned_data.get('renter_details'),
                            renter_payment_date=form.cleaned_data.get('renter_payment_date'),
                            renter_transaction_no=form.cleaned_data.get('renter_transaction_no'),
                            renter_is_active=True,
                        )
                    else:
                        # جایگزینی مستاجر فعلی در صورت تغییر اطلاعات مهم
                        renter_changed = (
                                form.cleaned_data.get('renter_mobile') != active_renter.renter_mobile or
                                form.cleaned_data.get('renter_name') != active_renter.renter_name or
                                form.cleaned_data.get('start_date') != active_renter.start_date or
                                form.cleaned_data.get('end_date') != active_renter.end_date
                        )
                        if renter_changed:
                            active_renter.renter_is_active = False
                            active_renter.save()

                            renter_user, _ = User.objects.get_or_create(
                                mobile=renter_mobile,
                                defaults={
                                    'username': renter_mobile,
                                    'full_name': form.cleaned_data.get('renter_name'),
                                    'is_active': True
                                }
                            )
                            active_renter = Renter.objects.create(
                                unit=unit,
                                user=renter_user,
                                bank=form.cleaned_data.get('bank'),
                                renter_name=form.cleaned_data.get('renter_name'),
                                renter_mobile=renter_mobile,
                                renter_national_code=form.cleaned_data.get('renter_national_code'),
                                renter_people_count=form.cleaned_data.get('renter_people_count'),
                                start_date=form.cleaned_data.get('start_date'),
                                end_date=form.cleaned_data.get('end_date'),
                                contract_number=form.cleaned_data.get('contract_number'),
                                estate_name=form.cleaned_data.get('estate_name'),
                                first_charge_renter=form.cleaned_data.get('first_charge_renter') or 0,
                                renter_details=form.cleaned_data.get('renter_details'),
                                renter_is_active=True,
                            )

                # --------- 7️⃣ شارژ اولیه مستاجر ---------
                first_charge_renter = Decimal(form.cleaned_data.get('first_charge_renter') or 0)
                if unit.is_renter and active_renter and first_charge_renter > 0:
                    Fund.objects.filter(unit=unit, is_initial=True).update(is_initial=False)
                    Fund.objects.create(
                        user=active_renter.user,
                        unit=unit,
                        bank=form.cleaned_data.get('bank'),
                        debtor_amount=first_charge_renter,
                        creditor_amount=0,
                        amount=first_charge_renter,
                        is_initial=True,
                        payment_date=form.cleaned_data.get('renter_payment_date'),
                        payer_name=unit.get_label(),
                        payment_description='شارژ اولیه مستاجر',
                        payment_gateway='پرداخت الکترونیک',
                        content_object=unit,
                        transaction_no=form.cleaned_data.get('renter_transaction_no'),
                    )

                # --------- 8️⃣ شارژ اولیه مالک ---------
                first_charge_owner = Decimal(form.cleaned_data.get('first_charge_owner') or 0)
                if first_charge_owner > 0:
                    fund_user = unit.user
                    fund_owner, created = Fund.objects.get_or_create(
                        unit=unit,
                        user=fund_user,
                        is_initial=True,
                        defaults={
                            'bank': form.cleaned_data.get('bank'),
                            'debtor_amount': first_charge_owner,
                            'creditor_amount': 0,
                            'amount': first_charge_owner,
                            'payment_date': form.cleaned_data.get('owner_payment_date'),
                            'payer_name': unit.get_label(),
                            'payment_description': 'شارژ اولیه مالک',
                            'payment_gateway': 'پرداخت الکترونیک',
                            'content_object': unit,
                            'transaction_no': form.cleaned_data.get('owner_transaction_no'),
                        }
                    )
                    if not created:
                        fund_owner.debtor_amount = first_charge_owner
                        fund_owner.amount = first_charge_owner
                        fund_owner.payment_date = form.cleaned_data.get('owner_payment_date')
                        fund_owner.bank = form.cleaned_data.get('bank')
                        fund_owner.transaction_no = form.cleaned_data.get('owner_transaction_no')
                        fund_owner.save()

                messages.success(self.request, 'اطلاعات واحد با موفقیت ویرایش شد')
                return super().form_valid(form)

        except Exception as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['is_renter'] = self.object.renters.filter(renter_is_active=True).exists()
        return context


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
    try:
        # --- حذف مستاجرها ---
        unit.renters.all().delete()

        # --- حذف کاربر فقط اگر هیچ واحد دیگری نداشته باشد ---
        if unit.user and not Unit.objects.filter(user=unit.user).exclude(pk=unit.pk).exists():
            unit.user.delete()

        # --- حذف خود واحد ---
        unit.delete()
        messages.success(request, 'واحد با موفقیت حذف گردید!')
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
            .filter(user__manager=user)
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

        # اضافه کردن renters فعال به هر واحد
        for unit in qs:
            unit.active_renters = unit.renters.filter(renter_is_active=True)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            'total_units': Unit.objects.filter(
                user__manager=self.request.user
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

    def form_valid(self, form):
        form.instance.user = self.request.user
        try:
            with transaction.atomic():
                self.object = form.save(commit=False)

                # مقدار هزینه
                expense_amount = self.object.amount or 0

                # آخرین Fund کلی
                last_fund = Fund.objects.order_by('-doc_number').first()

                if last_fund and last_fund.final_amount is not None:
                    current_final = last_fund.final_amount
                else:
                    # اگر بانک مشخص شده باشد از initial_fund آن استفاده کن، در غیر این صورت صفر
                    current_final = self.object.bank.initial_fund if self.object.bank else 0

                print(f'Expense Amount: {expense_amount}')
                print(f'Current Final: {current_final}')

                # بررسی موجودی
                if current_final - expense_amount < 0:
                    messages.error(self.request, "موجودی صندوق کافی نیست. ثبت این هزینه ممکن نیست!")
                    return self.form_invalid(form)

                # ثبت هزینه
                self.object.save()

                # ایجاد Fund مرتبط با Expense
                content_type = ContentType.objects.get_for_model(self.object)
                Fund.objects.create(
                    content_type=content_type,
                    object_id=self.object.id,
                    bank=self.object.bank,  # ممکن است None باشد
                    debtor_amount=0,
                    amount=expense_amount,
                    creditor_amount=expense_amount,
                    user=self.request.user,
                    payment_date=self.object.date,
                    payment_gateway='پرداخت الکترونیک',
                    payment_description=f"هزینه: {self.object.description[:50]}",
                )

                # ذخیره فایل‌ها
                files = self.request.FILES.getlist('document')
                for f in files:
                    ExpenseDocument.objects.create(expense=self.object, document=f)

            messages.success(self.request, 'هزینه با موفقیت ثبت گردید')
            return super().form_valid(form)

        except ProtectedError:
            messages.error(self.request, 'خطا در ثبت هزینه!')
            return self.form_invalid(form)

    def get_queryset(self):
        queryset = Expense.objects.filter(user=self.request.user).order_by('-created_at')

        # فیلتر بر اساس category__title
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category__id=category_id)

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
        return queryset

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        expenses = self.get_queryset()  # از get_queryset برای دریافت داده‌های فیلتر شده استفاده می‌کنیم
        paginator = Paginator(expenses, 50)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context['page_obj'] = page_obj
        context['total_expense'] = Expense.objects.filter(user=self.request.user).count()
        context['categories'] = ExpenseCategory.objects.filter(user=self.request.user)
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_expense_edit(request, pk):
    expense = get_object_or_404(Expense, pk=pk)

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

    bank = form.cleaned_data['bank']

    expense_ct = ContentType.objects.get_for_model(Expense)

    with transaction.atomic():
        # دریافت یا ایجاد Fund مرتبط با این Expense
        fund, created = Fund.objects.get_or_create(
            content_type=expense_ct,
            object_id=expense.id,
            defaults={
                'user': expense.user,
                'bank': bank,
                'amount': Decimal(0),
                'debtor_amount': Decimal(0),
                'creditor_amount': Decimal(0),
                'payment_date': expense.date,
                'payment_gateway': 'پرداخت الکترونیک',
                'payment_description': f"هزینه: {(expense.description or '')[:50]}",
            }
        )

        old_creditor = fund.creditor_amount or Decimal(0)
        delta = new_amount - old_creditor  # 🔹 تغییر واقعی

        # محاسبه موجودی فعلی صندوق کلی (بدون بانک)
        last_fund = Fund.objects.order_by('-doc_number').first()
        current_final = Decimal(last_fund.final_amount if last_fund else 0)

        if current_final - delta < 0:
            messages.error(request, "خطا: موجودی صندوق کافی نیست. ویرایش هزینه باعث منفی شدن موجودی می‌شود.")
            return redirect('middle_add_expense')

        # ذخیره Expense
        expense = form.save()

        # ذخیره فایل‌های جدید بدون حذف قبلی
        for f in request.FILES.getlist('document'):
            ExpenseDocument.objects.create(expense=expense, document=f)

        # بروزرسانی Fund با مقدار جدید
        fund.creditor_amount = new_amount
        fund.debtor_amount = Decimal(0)
        fund.amount = new_amount
        fund.bank = bank
        fund.payment_date = expense.date
        fund.payment_gateway = 'پرداخت الکترونیک'
        fund.payment_description = f"هزینه: {(expense.description or '')[:50]}"
        fund.save()

        # بازمحاسبه موجودی کل صندوق
        Fund.recalc_final_amounts_from(fund)

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
def export_expense_pdf(request):
    expenses = Expense.objects.all()

    filter_fields = {
        'category': 'category__id',
        'amount': 'amount__icontains',
        'doc_no': 'doc_no__icontains',
        'description': 'description__icontains',
        'details': 'details__icontains',
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
    template = get_template("expense_templates/expense_pdf.html")
    context = {
        'expenses': expenses,
        'font_path': font_url,
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
def export_expense_excel(request):
    expenses = Expense.objects.all()

    # Filter fields
    filter_fields = {
        'category': 'category__id',
        'amount': 'amount__icontains',
        'doc_no': 'doc_no__icontains',
        'description': 'description__icontains',
        'details': 'details__icontains',
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
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)

    # ✅ Style setup
    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")  # Gold
    header_font = Font(bold=True, color="000000")  # Black bold text

    headers = ['#', 'موضوع هزینه', 'شرح سند', ' شماره سند', 'مبلغ', 'تاریخ سند', 'توضیحات']

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
        jalali_date = jdatetime.date.fromgregorian(date=expense.date).strftime('%Y/%m/%d')
        ws.cell(row=row_num, column=6, value=jalali_date)
        ws.cell(row=row_num, column=7, value=expense.details)

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
        try:
            self.object = form.save()
            content_type = ContentType.objects.get_for_model(self.object)
            payer_name_for_fund = self.object.payer_name if not self.object.unit else f"{self.object.unit}"

            Fund.objects.create(
                user=self.request.user,
                content_type=content_type,
                object_id=self.object.id,
                bank=self.object.bank,
                amount=self.object.amount or 0,
                debtor_amount=self.object.amount or 0,
                creditor_amount=0,
                payer_name=payer_name_for_fund,
                payment_date=self.object.doc_date,
                payment_gateway='پرداخت الکترونیک',
                payment_description=f"درآمد: {self.object.description[:50]}",
            )

            files = self.request.FILES.getlist('document')

            for f in files:
                IncomeDocument.objects.create(income=self.object, document=f)
            messages.success(self.request, 'درآمد با موفقیت ثبت گردید')
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, 'خطا در ثبت درآمد!')
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
def middle_income_edit(request, pk):
    income = get_object_or_404(Income, pk=pk)

    if request.method != 'POST':
        return redirect('middle_add_income')

    form = IncomeForm(request.POST, request.FILES, instance=income, user=request.user)

    if not form.is_valid():
        messages.error(request, 'خطا در ویرایش فرم درآمد. لطفا دوباره تلاش کنید.')
        return redirect('middle_add_income')

    try:
        with transaction.atomic():
            income = form.save()

            # 🔹 بروزرسانی سند مالی
            content_type = ContentType.objects.get_for_model(Income)
            fund = Fund.objects.filter(
                content_type=content_type,
                object_id=income.id
            ).first()

            if fund:
                fund.bank = income.bank
                fund.debtor_amount = income.amount
                fund.amount = income.amount or 0
                fund.creditor_amount = 0
                fund.payment_date = income.doc_date
                fund.payment_gateway = 'پرداخت الکترونیک'
                fund.payment_description = f"درآمد (ویرایش): {(income.description or '')[:50]}"
                fund.save()
                Fund.recalc_final_amounts_from(fund)
            else:
                # اگر قبلاً سند نداشته (حالت غیرمنتظره)
                Fund.objects.create(
                    content_type=content_type,
                    object_id=income.id,
                    bank=income.bank,
                    debtor_amount=income.amount or 0,
                    amount=income.amount or 0,
                    creditor_amount=0,
                    user=request.user,
                    payment_date=income.doc_date,
                    payment_gateway='پرداخت الکترونیک',
                    payment_description=f"درآمد: {(income.description or '')[:50]}",
                )

            # 🔹 ذخیره فایل‌ها
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
    incomes = Income.objects.all()

    filter_fields = {
        'category': 'category__id',
        'amount': 'amount__icontains',
        'doc_number': 'doc_number__icontains',
        'description': 'description__icontains',
        'details': 'details__icontains',
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
    template = get_template("income_templates/income_pdf.html")
    context = {
        'incomes': incomes,
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

    response['Content-Disposition'] = f'attachment; filename="incomes.pdf"'

    pdf_merger.write(response)
    return response


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def export_income_excel(request):
    incomes = Income.objects.all()

    # Filter fields
    filter_fields = {
        'category': 'category__id',
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
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)

    # ✅ Style setup
    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")  # Gold
    header_font = Font(bold=True, color="000000")  # Black bold text

    headers = ['#', 'موضوع درآمد', 'شرح سند', ' شماره سند', 'مبلغ', 'تاریخ سند', 'توضیحات']

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
        jalali_date = jdatetime.date.fromgregorian(date=income.doc_date).strftime('%Y/%m/%d')
        ws.cell(row=row_num, column=6, value=jalali_date)
        ws.cell(row=row_num, column=7, value=income.details)

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
            self.object = form.save()
            content_type = ContentType.objects.get_for_model(self.object)
            payer_name_for_fund = self.object.payer_name if not self.object.unit else f"{self.object.unit}"
            Fund.objects.create(
                user=self.request.user,
                content_type=content_type,
                object_id=self.object.id,
                bank=self.object.bank,
                unit=self.object.unit,
                amount=self.object.amount or 0,
                debtor_amount=self.object.amount or 0,
                creditor_amount=0,
                doc_number=self.object.doc_number,
                payer_name=payer_name_for_fund,
                payment_gateway='پرداخت الکترونیک',
                payment_date=self.object.doc_date,
                payment_description=f"حسابهای دریافتنی: {self.object.description[:50]}",
                is_received=True
            )
            files = self.request.FILES.getlist('document')

            # ذخیره فایل‌ها در مدل ExpenseDocument
            for f in files:
                ReceiveDocument.objects.create(receive=self.object, document=f)
            messages.success(self.request, 'سند دریافت با موفقیت ثبت گردید!')
            return super().form_valid(form)
        except:
            messages.error(self.request, 'خطا در ثبت!')
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
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_receive_edit(request, pk):
    receive = get_object_or_404(ReceiveMoney, pk=pk)

    if request.method == 'POST':
        form = ReceiveMoneyForm(
            request.POST,
            request.FILES,
            instance=receive,
            user=request.user
        )

        if form.is_valid():
            receive = form.save()

            # ✅ تعیین payer_name برای Fund
            if receive.unit:
                payer_name_for_fund = str(receive.unit)
            else:
                payer_name_for_fund = receive.payer_name

            content_type = ContentType.objects.get_for_model(ReceiveMoney)

            fund = Fund.objects.filter(
                content_type=content_type,
                object_id=receive.id
            ).first()

            if fund:
                fund.bank = receive.bank
                fund.unit = receive.unit
                fund.payment_gateway = 'پرداخت الکترونیک'
                fund.amount = receive.amount or 0
                fund.debtor_amount = receive.amount or 0
                fund.creditor_amount = 0
                fund.payment_date = receive.doc_date
                fund.doc_number = receive.doc_number
                fund.payer_name = payer_name_for_fund
                fund.payment_description = f"حسابهای دریافتنی: {(receive.description or '')[:50]}"
                fund.save()

                Fund.recalc_final_amounts_from(fund)

            else:
                Fund.objects.create(
                    user=request.user,
                    content_type=content_type,
                    object_id=receive.id,
                    bank=receive.bank,
                    unit=receive.unit,
                    amount=receive.amount or 0,
                    debtor_amount=receive.amount or 0,
                    creditor_amount=0,
                    payment_date=receive.doc_date,
                    doc_number=receive.doc_number,
                    payment_gateway='پرداخت الکترونیک',
                    payer_name=payer_name_for_fund,
                    payment_description=f"حسابهای دریافتنی: {(receive.description or '')[:50]}",
                    is_received=True
                )

            # 📎 ذخیره فایل‌ها
            files = request.FILES.getlist('document')
            for f in files:
                ReceiveDocument.objects.create(receive=receive, document=f)

            messages.success(request, 'سند با موفقیت ویرایش گردید.')
            return redirect(reverse('middle_add_receive'))

        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفاً دوباره تلاش کنید.')

    else:
        form = ReceiveMoneyForm(instance=receive, user=request.user)

    return render(
        request,
        'MiddleReceiveMoney/add_receive_money.html',
        {'form': form, 'receive': receive}
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
    receives = ReceiveMoney.objects.all()

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
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=8)

    # ✅ Style setup
    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")  # Gold
    header_font = Font(bold=True, color="000000")  # Black bold text

    headers = ['#', 'شماره جساب', 'دریافت کننده', 'شرح سند', ' شماره سند', 'مبلغ', 'تاریخ سند', 'توضیحات']

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
        jalali_date = jdatetime.date.fromgregorian(date=receive.doc_date).strftime('%Y/%m/%d')
        ws.cell(row=row_num, column=7, value=jalali_date)
        ws.cell(row=row_num, column=8, value=receive.details)

    # ✅ Return file
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=receive.xlsx'
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
        try:
            self.object = form.save()
            content_type = ContentType.objects.get_for_model(self.object)
            receiver_name_for_fund = self.object.receiver_name if not self.object.unit else f"{self.object.unit}"

            Fund.objects.create(
                user=self.request.user,
                content_type=content_type,
                object_id=self.object.id,
                bank=self.object.bank,
                unit=self.object.unit,
                amount=self.object.amount,
                debtor_amount=0,
                receiver_name=receiver_name_for_fund,
                creditor_amount=self.object.amount,
                payment_gateway='پرداخت الکترونیک',
                payment_date=self.object.document_date,
                doc_number=self.object.document_number,
                payment_description=f"حسابهای پرداختنی: {self.object.description[:50]}",
                is_paid=True
            )

            files = self.request.FILES.getlist('document')
            for f in files:
                PayDocument.objects.create(payment=self.object, document=f)

            messages.success(self.request, 'سند پرداخت با موفقیت ثبت گردید!')
            return super().form_valid(form)

        except Exception as e:
            messages.error(self.request, f'خطا در ثبت: {e}')
            return self.form_invalid(form)

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
                queryset = queryset.filter(document_date__gte=gregorian_from)

            if to_date_str:
                jalali_to = jdatetime.datetime.strptime(to_date_str, '%Y/%m/%d')
                gregorian_to = jalali_to.togregorian().date()
                queryset = queryset.filter(document_date__lte=gregorian_to)
        except ValueError:
            messages.warning(self.request, 'فرمت تاریخ وارد شده صحیح نیست.')
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
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_pay_edit(request, pk):
    # گرفتن رکورد پرداخت موجود
    payment = get_object_or_404(PayMoney, pk=pk)

    if request.method == 'POST':
        # فرم با instance برای ویرایش
        form = PayerMoneyForm(request.POST, request.FILES, instance=payment, user=request.user)

        if form.is_valid():
            payment = form.save()

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
                    is_paid=True
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


def export_pay_pdf(request):
    payments = PayMoney.objects.all()

    filter_fields = {
        'bank': 'bank__id',
        'receiver_name': 'payer_name',
        'amount': 'amount__icontains',
        'document_number': 'doc_number__icontains',
        'description': 'description__icontains',
        'details': 'details__icontains',
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


def export_pay_excel(request):
    payments = PayMoney.objects.all()

    filter_fields = {
        'bank': 'bank__id',
        'receiver_name': 'receiver_name__icontains',
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
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=8)

    # ✅ Style setup
    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")  # Gold
    header_font = Font(bold=True, color="000000")  # Black bold text

    headers = ['#', 'شماره جساب', 'دریافت کننده', 'شرح سند', ' شماره سند', 'مبلغ', 'تاریخ سند', 'توضیحات']

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
        jalali_date = jdatetime.date.fromgregorian(date=payment.document_date).strftime('%Y/%m/%d')
        ws.cell(row=row_num, column=7, value=jalali_date)
        ws.cell(row=row_num, column=8, value=payment.details)

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

class MiddleMaintenanceCreateView(CreateView):
    model = Maintenance
    template_name = 'middleMaintenance/add_maintenance.html'
    form_class = MaintenanceForm
    success_url = reverse_lazy('middle_add_maintenance')

    def form_valid(self, form):
        form.instance.user = self.request.user
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


def middle_maintenance_delete(request, pk):
    maintenance = get_object_or_404(Maintenance, id=pk)
    try:
        maintenance.delete()
        messages.success(request, ' سند با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('middle_add_maintenance'))


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


def parse_jalali_to_gregorian(date_str):
    try:
        return jdatetime.date.fromisoformat(date_str.strip()).togregorian()
    except Exception:
        return None


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

    allowed_methods = list(
        user.charge_methods.values_list('id', flat=True)
    )

    context = {
        'allowed_methods': allowed_methods
    }
    return render(request, 'middleCharge/add_charge.html', context)


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

        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        form.instance.unit_count = unit_count

        # واحدهای فعال
        units = Unit.objects.filter(
            is_active=True,
            user__in=managed_users
        )

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
        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        context['unit_count'] = unit_count

        charges = FixCharge.objects.filter(user=self.request.user).annotate(
            total_units=Count('unified_charges'),  # همه واحدهای مرتبط
            notified_count=Count(
                'unified_charges',
                filter=Q(unified_charges__send_notification=True)
            )
        ).order_by('-created_at')
        context['charges'] = charges
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
                            'fix_amount': fix_charge.fix_amount,
                            'amount': base_amount,
                            'main_charge': fix_charge,
                            'charge_by_person_amount': 0,
                            'charge_by_area_amount': 0,
                            'fix_person_variable_amount': 0,
                            'fix_area_variable_amount': 0,
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
    managed_users = request.user.managed_users.all()

    # واحدهای فعال تحت مدیریت
    units = Unit.objects.filter(is_active=True, user__in=managed_users)

    # جستجو
    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    # Pagination
    per_page = request.GET.get('per_page', 30)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 30
    paginator = Paginator(units, per_page)
    page_number = request.GET.get('page')
    page_units = paginator.get_page(page_number)

    if request.method == 'POST':
        selected_units = request.POST.getlist('units')
        if selected_units:
            # فقط واحدهایی که هنوز send_notification=False هستند
            qs = UnifiedCharge.objects.filter(
                content_type=ContentType.objects.get_for_model(FixCharge),
                object_id=charge.id,
                unit_id__in=selected_units,
                send_notification=False
            )
            updated_count = qs.update(
                send_notification=True,
                send_notification_date=timezone.now()
            )

            if updated_count:
                messages.success(request, f'اطلاعیه شارژ برای {updated_count} واحد ارسال شد')
            else:
                messages.info(request, 'اطلاعیه جدیدی برای ارسال وجود ندارد')

        else:
            messages.warning(request, 'هیچ واحدی انتخاب نشده است')
        return redirect(request.path)

    # آماده‌سازی داده‌ها برای قالب
    uc_map = UnifiedCharge.objects.filter(
        content_type=ContentType.objects.get_for_model(FixCharge),
        object_id=charge.id,
        unit__in=page_units
    ).select_related('unit', 'unit__user', 'bank')

    items = []
    for uc in uc_map:
        renter = uc.unit.renters.filter(renter_is_active=True).first()
        items.append({
            'unit': uc.unit,
            'renter': renter,
            'is_paid': uc.is_paid,
            'is_notified': uc.send_notification,
            'total_charge': uc.total_charge_month,
        })

    context = {
        'charge': charge,
        'page_obj': items,  # حالا فقط واحدهای دارای UnifiedCharge هستند
        'paginator': paginator,
    }

    return render(request, 'middleCharge/notify_fix_charge_template.html', context)


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
        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        form.instance.unit_count = unit_count
        total_area = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('area'))['total'] or 0
        form.instance.total_area = total_area

        # total_people = Unit.objects.filter(
        #     is_active=True,
        #     user=self.request.user
        # ).aggregate(total=Sum('people_count'))['total'] or 0
        # form.instance.total_people = total_people

        # واحدهای فعال
        units = Unit.objects.filter(
            is_active=True,
            user__in=managed_users
        )

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

        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        context['unit_count'] = unit_count

        total_area = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('area'))['total'] or 0
        context['total_area'] = total_area

        # total_people = Unit.objects.filter(
        #     is_active=True,
        #     user=self.request.user
        # ).aggregate(total=Sum('people_count'))['total'] or 0
        # context['total_people'] = total_people

        charges = AreaCharge.objects.annotate(
            notified_count=Count(
                'unified_charges',
                filter=Q(unified_charges__send_notification=True)
            ),
            total_units=Count('unified_charges')
        ).order_by('-created_at')

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
        content_type=ContentType.objects.get_for_model(FixCharge),
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
                units = Unit.objects.filter(is_active=True, user__in=managed_users)
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
    managed_users = request.user.managed_users.all()

    # واحدهای فعال تحت مدیریت
    units = Unit.objects.filter(is_active=True, user__in=managed_users)

    # جستجو
    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    # Pagination
    per_page = request.GET.get('per_page', 30)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 30
    paginator = Paginator(units, per_page)
    page_number = request.GET.get('page')
    page_units = paginator.get_page(page_number)

    if request.method == 'POST':
        selected_units = request.POST.getlist('units')
        if selected_units:
            # فقط واحدهایی که هنوز send_notification=False هستند
            qs = UnifiedCharge.objects.filter(
                content_type=ContentType.objects.get_for_model(AreaCharge),
                object_id=charge.id,
                unit_id__in=selected_units,
                send_notification=False
            )
            updated_count = qs.update(
                send_notification=True,
                send_notification_date=timezone.now()
            )

            if updated_count:
                messages.success(request, f'اطلاعیه شارژ برای {updated_count} واحد ارسال شد')
            else:
                messages.info(request, 'اطلاعیه جدیدی برای ارسال وجود ندارد')

        else:
            messages.warning(request, 'هیچ واحدی انتخاب نشده است')
        return redirect(request.path)

    # آماده‌سازی داده‌ها برای قالب
    uc_map = UnifiedCharge.objects.filter(
        content_type=ContentType.objects.get_for_model(AreaCharge),
        object_id=charge.id,
        unit__in=page_units
    ).select_related('unit', 'unit__user', 'bank')

    items = []
    for uc in uc_map:
        renter = uc.unit.renters.filter(renter_is_active=True).first()
        items.append({
            'unit': uc.unit,
            'renter': renter,
            'is_paid': uc.is_paid,
            'is_notified': uc.send_notification,
            'total_charge': uc.total_charge_month,
        })

    context = {
        'charge': charge,
        'page_obj': items,  # حالا فقط واحدهای دارای UnifiedCharge هستند
        'paginator': paginator,
    }

    return render(request, 'middleCharge/notify_area_charge_template.html', context)


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
        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        form.instance.unit_count = unit_count
        # total_area = Unit.objects.filter(
        #     is_active=True,
        #     user__manager=self.request.user
        # ).aggregate(total=Sum('area'))['total'] or 0
        # form.instance.total_area = total_area

        total_people = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('people_count'))['total'] or 0
        form.instance.total_people = total_people

        # واحدهای فعال
        units = Unit.objects.filter(
            is_active=True,
            user__in=managed_users
        )

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
        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        context['unit_count'] = unit_count
        total_people = Unit.objects.filter(is_active=True, user__manager=self.request.user).aggregate(
            total=Sum('people_count'))['total'] or 0
        context['total_people'] = total_people

        charges = PersonCharge.objects.annotate(
            notified_count=Count(
                'unified_charges',
                filter=Q(unified_charges__send_notification=True)
            ),
            total_units=Count('unified_charges')
        ).order_by('-created_at')
        context['charges'] = charges
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
    managed_users = request.user.managed_users.all()

    # واحدهای فعال تحت مدیریت
    units = Unit.objects.filter(is_active=True, user__in=managed_users)

    # جستجو
    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    # Pagination
    per_page = request.GET.get('per_page', 30)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 30
    paginator = Paginator(units, per_page)
    page_number = request.GET.get('page')
    page_units = paginator.get_page(page_number)

    if request.method == 'POST':
        selected_units = request.POST.getlist('units')
        if selected_units:
            # فقط واحدهایی که هنوز send_notification=False هستند
            qs = UnifiedCharge.objects.filter(
                content_type=ContentType.objects.get_for_model(PersonCharge),
                object_id=charge.id,
                unit_id__in=selected_units,
                send_notification=False
            )
            updated_count = qs.update(
                send_notification=True,
                send_notification_date=timezone.now()
            )

            if updated_count:
                messages.success(request, f'اطلاعیه شارژ برای {updated_count} واحد ارسال شد')
            else:
                messages.info(request, 'اطلاعیه جدیدی برای ارسال وجود ندارد')

        else:
            messages.warning(request, 'هیچ واحدی انتخاب نشده است')
        return redirect(request.path)

    # آماده‌سازی داده‌ها برای قالب
    uc_map = UnifiedCharge.objects.filter(
        content_type=ContentType.objects.get_for_model(PersonCharge),
        object_id=charge.id,
        unit__in=page_units
    ).select_related('unit', 'unit__user', 'bank')

    items = []
    for uc in uc_map:
        renter = uc.unit.renters.filter(renter_is_active=True).first()
        items.append({
            'unit': uc.unit,
            'renter': renter,
            'is_paid': uc.is_paid,
            'is_notified': uc.send_notification,
            'total_charge': uc.total_charge_month,
        })

    context = {
        'charge': charge,
        'page_obj': items,  # حالا فقط واحدهای دارای UnifiedCharge هستند
        'paginator': paginator,
    }

    return render(request, 'middleCharge/notify_person_charge_template.html', context)


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
        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        form.instance.unit_count = unit_count
        total_area = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('area'))['total'] or 0
        form.instance.total_area = total_area

        total_people = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('people_count'))['total'] or 0
        form.instance.total_people = total_people

        # واحدهای فعال
        units = Unit.objects.filter(
            is_active=True,
            user__in=managed_users
        )

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
        context['unit_count'] = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        context['total_area'] = \
            Unit.objects.filter(is_active=True, user__manager=self.request.user).aggregate(total=Sum('area'))[
                'total'] or 0

        charges = FixAreaCharge.objects.annotate(
            notified_count=Count(
                'unified_charges',
                filter=Q(unified_charges__send_notification=True)
            ),
            total_units=Count('unified_charges')
        ).order_by('-created_at')
        context['charges'] = charges
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
    managed_users = request.user.managed_users.all()

    # واحدهای فعال تحت مدیریت
    units = Unit.objects.filter(is_active=True, user__in=managed_users)

    # جستجو
    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    # Pagination
    per_page = request.GET.get('per_page', 30)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 30
    paginator = Paginator(units, per_page)
    page_number = request.GET.get('page')
    page_units = paginator.get_page(page_number)

    if request.method == 'POST':
        selected_units = request.POST.getlist('units')
        if selected_units:
            # فقط واحدهایی که هنوز send_notification=False هستند
            qs = UnifiedCharge.objects.filter(
                content_type=ContentType.objects.get_for_model(FixAreaCharge),
                object_id=charge.id,
                unit_id__in=selected_units,
                send_notification=False
            )
            updated_count = qs.update(
                send_notification=True,
                send_notification_date=timezone.now()
            )

            if updated_count:
                messages.success(request, f'اطلاعیه شارژ برای {updated_count} واحد ارسال شد')
            else:
                messages.info(request, 'اطلاعیه جدیدی برای ارسال وجود ندارد')

        else:
            messages.warning(request, 'هیچ واحدی انتخاب نشده است')
        return redirect(request.path)

    # آماده‌سازی داده‌ها برای قالب
    uc_map = UnifiedCharge.objects.filter(
        content_type=ContentType.objects.get_for_model(FixAreaCharge),
        object_id=charge.id,
        unit__in=page_units
    ).select_related('unit', 'unit__user', 'bank')

    items = []
    for uc in uc_map:
        renter = uc.unit.renters.filter(renter_is_active=True).first()
        items.append({
            'unit': uc.unit,
            'renter': renter,
            'is_paid': uc.is_paid,
            'is_notified': uc.send_notification,
            'total_charge': uc.total_charge_month,
        })

    context = {
        'charge': charge,
        'page_obj': items,  # حالا فقط واحدهای دارای UnifiedCharge هستند
        'paginator': paginator,
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
        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        form.instance.unit_count = unit_count
        total_area = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('area'))['total'] or 0
        form.instance.total_area = total_area

        total_people = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('people_count'))['total'] or 0
        form.instance.total_people = total_people

        # واحدهای فعال
        units = Unit.objects.filter(
            is_active=True,
            user__in=managed_users
        )

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
        context['unit_count'] = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        context['total_area'] = Unit.objects.filter(is_active=True).aggregate(total=Sum('area'))['total'] or 0
        context['total_people'] = Unit.objects.filter(is_active=True, user__manager=self.request.user
                                                      ).aggregate(total=Sum('people_count'))['total'] or 0

        charges = FixPersonCharge.objects.annotate(
            notified_count=Count(
                'unified_charges',
                filter=Q(unified_charges__send_notification=True)
            ),
            total_units=Count('unified_charges')
        ).order_by('-created_at')
        context['charges'] = charges
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
    managed_users = request.user.managed_users.all()

    # واحدهای فعال تحت مدیریت
    units = Unit.objects.filter(is_active=True, user__in=managed_users)

    # جستجو
    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    # Pagination
    per_page = request.GET.get('per_page', 30)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 30
    paginator = Paginator(units, per_page)
    page_number = request.GET.get('page')
    page_units = paginator.get_page(page_number)

    if request.method == 'POST':
        selected_units = request.POST.getlist('units')
        if selected_units:
            # فقط واحدهایی که هنوز send_notification=False هستند
            qs = UnifiedCharge.objects.filter(
                content_type=ContentType.objects.get_for_model(FixPersonCharge),
                object_id=charge.id,
                unit_id__in=selected_units,
                send_notification=False
            )
            updated_count = qs.update(
                send_notification=True,
                send_notification_date=timezone.now()
            )

            if updated_count:
                messages.success(request, f'اطلاعیه شارژ برای {updated_count} واحد ارسال شد')
            else:
                messages.info(request, 'اطلاعیه جدیدی برای ارسال وجود ندارد')

        else:
            messages.warning(request, 'هیچ واحدی انتخاب نشده است')
        return redirect(request.path)

    # آماده‌سازی داده‌ها برای قالب
    uc_map = UnifiedCharge.objects.filter(
        content_type=ContentType.objects.get_for_model(FixPersonCharge),
        object_id=charge.id,
        unit__in=page_units
    ).select_related('unit', 'unit__user', 'bank')

    items = []
    for uc in uc_map:
        renter = uc.unit.renters.filter(renter_is_active=True).first()
        items.append({
            'unit': uc.unit,
            'renter': renter,
            'is_paid': uc.is_paid,
            'is_notified': uc.send_notification,
            'total_charge': uc.total_charge_month,
        })

    context = {
        'charge': charge,
        'page_obj': items,  # حالا فقط واحدهای دارای UnifiedCharge هستند
        'paginator': paginator,
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
        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        form.instance.unit_count = unit_count
        total_area = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('area'))['total'] or 0
        form.instance.total_area = total_area

        total_people = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('people_count'))['total'] or 0
        form.instance.total_people = total_people

        # واحدهای فعال
        units = Unit.objects.filter(
            is_active=True,
            user__in=managed_users
        )

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
        context['unit_count'] = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        context['total_area'] = \
            Unit.objects.filter(is_active=True, user__manager=self.request.user).aggregate(total=Sum('area'))[
                'total'] or 0
        context['total_people'] = \
            Unit.objects.filter(is_active=True, user__manager=self.request.user).aggregate(total=Sum('people_count'))[
                'total'] or 0

        charges = ChargeByPersonArea.objects.annotate(
            notified_count=Count(
                'unified_charges',
                filter=Q(unified_charges__send_notification=True)
            ),
            total_units=Count('unified_charges')
        ).order_by('-created_at')
        context['charges'] = charges
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
    managed_users = request.user.managed_users.all()

    # واحدهای فعال تحت مدیریت
    units = Unit.objects.filter(is_active=True, user__in=managed_users)

    # جستجو
    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    # Pagination
    per_page = request.GET.get('per_page', 30)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 30
    paginator = Paginator(units, per_page)
    page_number = request.GET.get('page')
    page_units = paginator.get_page(page_number)

    if request.method == 'POST':
        selected_units = request.POST.getlist('units')
        if selected_units:
            # فقط واحدهایی که هنوز send_notification=False هستند
            qs = UnifiedCharge.objects.filter(
                content_type=ContentType.objects.get_for_model(ChargeByPersonArea),
                object_id=charge.id,
                unit_id__in=selected_units,
                send_notification=False
            )
            updated_count = qs.update(
                send_notification=True,
                send_notification_date=timezone.now()
            )

            if updated_count:
                messages.success(request, f'اطلاعیه شارژ برای {updated_count} واحد ارسال شد')
            else:
                messages.info(request, 'اطلاعیه جدیدی برای ارسال وجود ندارد')

        else:
            messages.warning(request, 'هیچ واحدی انتخاب نشده است')
        return redirect(request.path)

    # آماده‌سازی داده‌ها برای قالب
    uc_map = UnifiedCharge.objects.filter(
        content_type=ContentType.objects.get_for_model(ChargeByPersonArea),
        object_id=charge.id,
        unit__in=page_units
    ).select_related('unit', 'unit__user', 'bank')

    items = []
    for uc in uc_map:
        renter = uc.unit.renters.filter(renter_is_active=True).first()
        items.append({
            'unit': uc.unit,
            'renter': renter,
            'is_paid': uc.is_paid,
            'is_notified': uc.send_notification,
            'total_charge': uc.total_charge_month,
        })

    context = {
        'charge': charge,
        'page_obj': items,  # حالا فقط واحدهای دارای UnifiedCharge هستند
        'paginator': paginator,
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
        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        form.instance.unit_count = unit_count
        total_area = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('area'))['total'] or 0
        form.instance.total_area = total_area

        total_people = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('people_count'))['total'] or 0
        form.instance.total_people = total_people

        # واحدهای فعال
        units = Unit.objects.filter(
            is_active=True,
            user__in=managed_users
        )

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
        context['unit_count'] = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        context['total_area'] = Unit.objects.filter(is_active=True, user__manager=self.request.user
                                                    ).aggregate(total=Sum('area'))['total'] or 0
        context['total_people'] = Unit.objects.filter(is_active=True, user__manager=self.request.user
                                                      ).aggregate(total=Sum('people_count'))['total'] or 0

        charges = ChargeByFixPersonArea.objects.annotate(
            notified_count=Count(
                'unified_charges',
                filter=Q(unified_charges__send_notification=True)
            ),
            total_units=Count('unified_charges')
        ).order_by('-created_at')
        context['charges'] = charges
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
    managed_users = request.user.managed_users.all()

    # واحدهای فعال تحت مدیریت
    units = Unit.objects.filter(is_active=True, user__in=managed_users)

    # جستجو
    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    # Pagination
    per_page = request.GET.get('per_page', 30)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 30
    paginator = Paginator(units, per_page)
    page_number = request.GET.get('page')
    page_units = paginator.get_page(page_number)

    if request.method == 'POST':
        selected_units = request.POST.getlist('units')
        if selected_units:
            # فقط واحدهایی که هنوز send_notification=False هستند
            qs = UnifiedCharge.objects.filter(
                content_type=ContentType.objects.get_for_model(ChargeByFixPersonArea),
                object_id=charge.id,
                unit_id__in=selected_units,
                send_notification=False
            )
            updated_count = qs.update(
                send_notification=True,
                send_notification_date=timezone.now()
            )

            if updated_count:
                messages.success(request, f'اطلاعیه شارژ برای {updated_count} واحد ارسال شد')
            else:
                messages.info(request, 'اطلاعیه جدیدی برای ارسال وجود ندارد')

        else:
            messages.warning(request, 'هیچ واحدی انتخاب نشده است')
        return redirect(request.path)

    # آماده‌سازی داده‌ها برای قالب
    uc_map = UnifiedCharge.objects.filter(
        content_type=ContentType.objects.get_for_model(ChargeByFixPersonArea),
        object_id=charge.id,
        unit__in=page_units
    ).select_related('unit', 'unit__user', 'bank')

    items = []
    for uc in uc_map:
        renter = uc.unit.renters.filter(renter_is_active=True).first()
        items.append({
            'unit': uc.unit,
            'renter': renter,
            'is_paid': uc.is_paid,
            'is_notified': uc.send_notification,
            'total_charge': uc.total_charge_month,
        })

    context = {
        'charge': charge,
        'page_obj': items,  # حالا فقط واحدهای دارای UnifiedCharge هستند
        'paginator': paginator,
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
        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        form.instance.unit_count = unit_count
        total_area = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('area'))['total'] or 0
        form.instance.total_area = total_area

        total_people = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('people_count'))['total'] or 0
        form.instance.total_people = total_people

        # واحدهای فعال
        units = Unit.objects.filter(
            is_active=True,
            user__in=managed_users
        )

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
                    charge_type=fix_variable.charge_type,
                    extra_parking_price= parking_total,
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
        context['unit_count'] = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        context['total_area'] = Unit.objects.filter(is_active=True, user__manager=self.request.user
                                                    ).aggregate(total=Sum('area'))['total'] or 0
        context['total_people'] = Unit.objects.filter(is_active=True, user__manager=self.request.user
                                                      ).aggregate(total=Sum('people_count'))['total'] or 0

        charges = ChargeFixVariable.objects.annotate(
            notified_count=Count(
                'unified_charges',
                filter=Q(unified_charges__send_notification=True)
            ),
            total_units=Count('unified_charges')
        ).order_by('-created_at')
        context['charges'] = charges
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
    managed_users = request.user.managed_users.all()

    # واحدهای فعال تحت مدیریت
    units = Unit.objects.filter(is_active=True, user__in=managed_users)

    # جستجو
    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    # Pagination
    per_page = request.GET.get('per_page', 30)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 30
    paginator = Paginator(units, per_page)
    page_number = request.GET.get('page')
    page_units = paginator.get_page(page_number)

    if request.method == 'POST':
        selected_units = request.POST.getlist('units')
        if selected_units:
            # فقط واحدهایی که هنوز send_notification=False هستند
            qs = UnifiedCharge.objects.filter(
                content_type=ContentType.objects.get_for_model(ChargeFixVariable),
                object_id=charge.id,
                unit_id__in=selected_units,
                send_notification=False
            )
            updated_count = qs.update(
                send_notification=True,
                send_notification_date=timezone.now()
            )

            if updated_count:
                messages.success(request, f'اطلاعیه شارژ برای {updated_count} واحد ارسال شد')
            else:
                messages.info(request, 'اطلاعیه جدیدی برای ارسال وجود ندارد')

        else:
            messages.warning(request, 'هیچ واحدی انتخاب نشده است')
        return redirect(request.path)

    # آماده‌سازی داده‌ها برای قالب
    uc_map = UnifiedCharge.objects.filter(
        content_type=ContentType.objects.get_for_model(ChargeFixVariable),
        object_id=charge.id,
        unit__in=page_units
    ).select_related('unit', 'unit__user', 'bank')

    items = []
    for uc in uc_map:
        renter = uc.unit.renters.filter(renter_is_active=True).first()
        items.append({
            'unit': uc.unit,
            'renter': renter,
            'is_paid': uc.is_paid,
            'is_notified': uc.send_notification,
            'total_charge': uc.total_charge_month,
        })

    context = {
        'charge': charge,
        'page_obj': items,  # حالا فقط واحدهای دارای UnifiedCharge هستند
        'paginator': paginator,
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


# ==============================================================================================

def get_all_base_charges():
    all_charges = chain(
        FixCharge.objects.all(),
        AreaCharge.objects.all(),
        PersonCharge.objects.all(),
        FixPersonCharge.objects.all(),
        FixAreaCharge.objects.all(),
        ChargeByPersonArea.objects.all(),
        ChargeByFixPersonArea.objects.all(),
        ChargeFixVariable.objects.all(),
    )
    return sorted(all_charges, key=lambda x: x.created_at, reverse=True)


def base_charge_list(request):
    # 🔍 جستجو
    query = request.GET.get('q', '').strip()

    # 📄 تعداد نمایش
    paginate = int(request.GET.get('paginate', 20))

    # 🔹 دریافت همه شارژهای پایه
    charges = get_all_base_charges()

    # 🔍 فیلتر جستجو (سازگار با BaseCharge)
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
    charges = get_all_base_charges()

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


def charge_units_list(request, app_label, model_name, charge_id):
    model = apps.get_model(app_label, model_name)
    charge = get_object_or_404(model, id=charge_id)

    # 🔥 بررسی نوع مدل و گرفتن unified charges
    if hasattr(charge, 'unified_charges'):
        # مدل اصلی شارژ → گرفتن همه UnifiedCharge ها
        unified_qs = charge.unified_charges.all()
    elif model_name.lower() == 'unifiedcharge':
        # خود UnifiedCharge → تبدیل به QuerySet با یک عضو
        unified_qs = model.objects.filter(id=charge.id)
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
# def charge_units_list(request, app_label, model_name, charge_id):
#     model = apps.get_model(app_label, model_name)
#     charge = get_object_or_404(model, id=charge_id)
#
#     # 🔥 آپدیت جریمه همه UnifiedCharge ها
#     unified_qs = charge.unified_charges.all()
#     for uc in unified_qs:
#         uc.update_penalty(save=True)
#
#     # -------------------------
#     # 🔍 جستجو
#     # -------------------------
#     query = request.GET.get('q', '').strip()
#
#     unified_charges = unified_qs.filter(
#         send_notification_date__isnull=False
#     ).select_related('unit', 'unit__user')
#
#     if query:
#         search_q = (
#                 Q(unit__unit__icontains=query) |
#                 Q(unit__user__full_name__icontains=query)
#         )
#
#         # اگر عدد بود → جستجو روی مقادیر عددی شارژ
#         if query.isdigit():
#             search_q |= (
#                     Q(penalty_amount=query) |
#                     Q(total_charge_month=query) |
#                     Q(base_charge=query)
#             )
#
#         unified_charges = unified_charges.filter(search_q)
#
#     # -------------------------
#     # 📄 pagination
#     # -------------------------
#     paginate = int(request.GET.get('paginate', 20))
#     paginator = Paginator(unified_charges, paginate)
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)
#
#     # واحدها (مطابق صفحه‌بندی)
#     units = [uc.unit for uc in page_obj if uc.unit]
#
#     # 🧪 debug (در صورت نیاز)
#     print('ALL:', charge.unified_charges.count())
#     print(
#         charge.unified_charges.values(
#             'id',
#             'send_notification',
#             'send_notification_date'
#         )
#     )
#
#     return render(
#         request,
#         'middleCharge/middle_charges_detail.html',
#         {
#             'charge': charge,
#             'units': units,
#             'unified_charges': page_obj,  # 👈 مهم
#             'query': query,
#             'paginate': paginate,
#             'page_obj': page_obj,
#             'app_label': app_label,
#             'model_name': model_name,
#         }
#     )


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

    # -------------------------
    # Excel
    # -------------------------
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Charge Units"
    ws.sheet_view.rightToLeft = True

    headers = [
        '#', 'واحد', 'مالک / ساکن', 'مبلغ پایه', 'جریمه',
        'مبلغ نهایی', 'تاریخ اعلام', 'وضعیت پرداخت'
    ]
    num_columns = len(headers)

    # عنوان
    title_cell = ws.cell(row=1, column=1, value="لیست شارژ ساختمان")
    title_cell.font = Font(bold=True, size=18)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    title_cell.fill = PatternFill(fill_type="solid")

    # merge سلول‌ها (فقط merge کنید، مقدار فقط در top-left)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_columns)

    row = 2
    for index, uc in enumerate(unified_charges, start=1):
        ws.cell(row=row, column=1, value=index)
        ws.cell(row=row, column=2, value=uc.title)
        ws.cell(row=row, column=3, value=uc.unit.get_label())
        ws.cell(row=row, column=4, value=uc.base_charge)
        ws.cell(row=row, column=5, value=uc.details)
        ws.cell(row=row, column=6, value=show_jalali(uc.send_notification_date))
        ws.cell(row=row, column=7, value=show_jalali(uc.payment_deadline_date))
        ws.cell(row=row, column=8, value=uc.penalty_amount)
        ws.cell(row=row, column=9, value=uc.total_charge_month)
        ws.cell(row=row, column=10, value="پرداخت شده" if uc.is_paid else "پرداخت نشده")

        row += 1

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=charge_units.xlsx'
    wb.save(response)
    return response


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

    pdf = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="charge_{charge.id}_units.pdf"'
    return response


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

    if request.method == "POST":
        selected_units = request.POST.getlist('units')
        if not selected_units:
            messages.warning(request, 'هیچ واحدی انتخاب نشده است.')
            return redirect('middle_register_sms')

        units_qs = Unit.objects.filter(is_active=True, user__manager=request.user)
        if 'all' in selected_units:
            units_to_notify = units_qs
        else:
            units_to_notify = units_qs.filter(id__in=selected_units)

        if not units_to_notify.exists():
            messages.warning(request, 'هیچ واحد معتبری برای ارسال پیامک پیدا نشد.')
            return redirect('middle_register_sms')

        notified_units = []
        with transaction.atomic():
            for unit in units_to_notify:
                if unit.user and unit.user.mobile:
                    helper.send_sms_to_user(
                        mobile=unit.user.mobile,
                        message=sms.message,
                        full_name=unit.user.full_name,
                        otp=None
                    )
                    notified_units.append(unit)  # append instance, NOT string

        if notified_units:
            sms.notified_units.set(notified_units)  # ✅ correct
            sms.send_notification = True
            sms.send_notification_date = timezone.now().date()  # use .date()
            sms.save()
            messages.success(request,
                             f'پیامک برای واحدهای زیر ارسال شد: {", ".join(str(u.unit) for u in notified_units)}')
        else:
            messages.info(request, 'پیامکی ارسال نشد؛ ممکن است شماره موبایل واحدها موجود نباشد.')

        return redirect('middle_register_sms')

    # اگر GET بود، فرم را رندر کن
    units_with_details = Unit.objects.filter(is_active=True)
    return render(request, 'middle_admin/middle_send_sms.html', {
        'sms': sms,
        'units_with_details': units_with_details,
    })


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
        return context



@login_required
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

        # گرفتن app_label و model_name از اولین شیء
        first_charge = charges.first()
        app_label = first_charge._meta.app_label
        model_name = first_charge._meta.model_name
        charge_id = first_charge.id

        return JsonResponse({
            'success': True,
            'titles': titles,
            'app_label': app_label,
            'model_name': model_name,
            'charge_id': charge_id,
            'message': 'جریمه با موفقیت حذف شد'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
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
        app_label = first_charge._meta.app_label
        model_name = first_charge._meta.model_name
        charge_id = first_charge.id

        return JsonResponse({
            'success': True,
            'titles': titles,
            'app_label': app_label,
            'model_name': model_name,
            'charge_id': charge_id,
            'message': 'جریمه با موفقیت بازگردانده شد'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# @require_POST
# @login_required
# def waive_penalty_bulk(request):
#     try:
#         ids = request.POST.getlist('charge_ids[]')
#
#         if not ids:
#             return JsonResponse({'success': False, 'error': 'هیچ موردی انتخاب نشده'}, status=400)
#
#         charges = UnifiedCharge.objects.filter(id__in=ids, is_paid=False)
#
#         titles = []
#         for charge in charges:
#             result = charge.waive_penalty(request.user)
#             if result:
#                 titles.append(result['title'])
#
#         return JsonResponse({
#             'success': True,
#             'titles': titles,
#             'message': 'جریمه با موفقیت حذف شد'
#         })
#
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'error': str(e)
#         }, status=500)
#
#
#
# @require_POST
# @login_required
# def restore_penalty_bulk(request):
#     try:
#         ids = request.POST.getlist('charge_ids[]')
#
#         if not ids:
#             return JsonResponse({'success': False, 'error': 'هیچ موردی انتخاب نشده'}, status=400)
#
#         charges = UnifiedCharge.objects.filter(id__in=ids)
#
#         restored = []
#
#         with transaction.atomic():
#             for charge in charges:
#                 result = charge.restore_penalty()
#                 if result:
#                     restored.append(result)
#
#         return JsonResponse({
#             'success': True,
#             'restored': restored,
#             'message': 'جریمه‌ها با موفقیت بازیابی شدند'
#         })
#
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'error': str(e)
#         }, status=500)
