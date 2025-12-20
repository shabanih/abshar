import io
import os
import time
from datetime import timezone
from decimal import Decimal

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.utils import timezone
import jdatetime
import openpyxl
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction, IntegrityError
from django.db.models import ProtectedError, Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, UpdateView, DetailView, ListView
from openpyxl.styles import PatternFill, Alignment, Font
from pypdf import PdfWriter
from sweetify import sweetify
from weasyprint import CSS, HTML

from admin_panel import helper
from admin_panel.forms import announcementForm, BankForm, UnitForm, ExpenseCategoryForm, ExpenseForm, \
    IncomeCategoryForm, IncomeForm, ReceiveMoneyForm, PayerMoneyForm, PropertyForm, MaintenanceForm, FixChargeForm, \
    FixAreaChargeForm, AreaChargeForm, PersonChargeForm, FixPersonChargeForm, PersonAreaChargeForm, \
    PersonAreaFixChargeForm, VariableFixChargeForm, MyHouseForm, SmsForm
from admin_panel.models import Announcement, ExpenseCategory, Expense, Fund, ExpenseDocument, IncomeCategory, Income, \
    IncomeDocument, ReceiveMoney, ReceiveDocument, PayMoney, PayDocument, Property, PropertyDocument, Maintenance, \
    MaintenanceDocument, FixCharge, FixedChargeCalc, AreaCharge, AreaChargeCalc, PersonCharge, PersonChargeCalc, \
    FixAreaCharge, FixAreaChargeCalc, FixPersonCharge, FixPersonChargeCalc, ChargeByPersonArea, ChargeByPersonAreaCalc, \
    ChargeByFixPersonArea, ChargeByFixPersonAreaCalc, ChargeFixVariable, ChargeFixVariableCalc, SmsManagement, \
    UnifiedCharge
from admin_panel.views import admin_required
from notifications.models import Notification, SupportUser

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

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'اطلاعات حساب بانکی با موفقیت ثبت گردید!')
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

    # ارسال user به فرم
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    # مقدار دادن به user و پیام موفقیت
    def form_valid(self, form):
        form.instance.user = self.request.user  # ← مستقیم به instance بده
        messages.success(self.request, 'اطلاعات حساب بانکی با موفقیت ویرایش گردید!')
        return super().form_valid(form)

    # اضافه کردن لیست بانک‌ها به context
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

    def form_valid(self, form):
        try:
            with transaction.atomic():
                mobile = form.cleaned_data['mobile']
                password = form.cleaned_data['password']
                is_renter = form.cleaned_data.get('is_renter')  # Boolean

                # بررسی وجود کاربر
                user, created = User.objects.get_or_create(mobile=mobile)
                if created:
                    user.set_password(password)
                else:
                    form.add_error('mobile', 'کاربری با این شماره موبایل قبلاً ثبت شده است.')
                    return self.form_invalid(form)

                user.username = mobile
                user.otp_create_time = timezone.now()
                user.is_staff = True
                is_renter = str(form.cleaned_data.get('is_renter')).lower() == 'true'
                user.full_name = form.cleaned_data.get('renter_name') if is_renter else form.cleaned_data.get(
                    'owner_name')
                user.manager = self.request.user  # ثبت مدیر سطح میانی
                user.save()
                house = MyHouse.objects.filter(user=self.request.user).first()
                if house:
                    house.residents.add(user)  # اضافه کردن کاربر جدید به ساکنین

                # ساخت واحد و اتصال به کاربر جدید
                unit = form.save(commit=False)
                unit.user = user  # کاربر ایجاد شده، مالک واحد است
                unit.is_renter = is_renter
                unit.save()

                # اگر مستاجر وجود دارد
                if is_renter:
                    Renter.objects.create(
                        unit=unit,
                        renter_name=form.cleaned_data.get('renter_name'),
                        renter_mobile=form.cleaned_data.get('renter_mobile'),
                        renter_national_code=form.cleaned_data.get('renter_national_code'),
                        renter_people_count=form.cleaned_data.get('renter_people_count'),
                        start_date=form.cleaned_data.get('start_date'),
                        end_date=form.cleaned_data.get('end_date'),
                        contract_number=form.cleaned_data.get('contract_number'),
                        estate_name=form.cleaned_data.get('estate_name'),
                        first_charge=form.cleaned_data.get('first_charge') or 0,
                        renter_details=form.cleaned_data.get('renter_details')
                    )

            messages.success(self.request, 'واحد و کاربر با موفقیت ثبت گردید!')
            return super().form_valid(form)

        except IntegrityError:
            form.add_error(None, "خطا در ذخیره اطلاعات. لطفاً مجدد تلاش کنید.")
            return self.form_invalid(form)


@method_decorator(middle_admin_required, name='dispatch')
class MiddleUnitUpdateView(LoginRequiredMixin, UpdateView):
    model = Unit
    form_class = UnitForm
    template_name = 'middle_unit_templates/edit_unit.html'
    success_url = reverse_lazy('middle_manage_unit')  # Redirect where you want after update

    def form_valid(self, form):
        try:
            with transaction.atomic():
                self.object = form.save(commit=False)

                # Don't change self.object.user (the original unit owner)
                unit_owner = self.object.user  # Correct user to edit

                new_mobile = form.cleaned_data.get('mobile')
                new_password = form.cleaned_data.get('password')
                is_renter = form.cleaned_data.get('is_renter')

                if new_mobile and new_mobile != unit_owner.mobile:
                    if User.objects.filter(mobile=new_mobile).exclude(pk=unit_owner.pk).exists():
                        form.add_error('mobile', 'این شماره موبایل قبلاً ثبت شده است.')
                        return self.form_invalid(form)

                    unit_owner.mobile = new_mobile
                    unit_owner.username = new_mobile
                is_renter = str(form.cleaned_data.get('is_renter')).lower() == 'true'
                unit_owner.full_name = form.cleaned_data.get('renter_name') if is_renter else form.cleaned_data.get(
                    'owner_name')
                if new_password:
                    unit_owner.set_password(new_password)

                unit_owner.save()
                self.object.save()  # Save the unit after confirming no issues

                house = MyHouse.objects.filter(user=self.request.user).first()  # یا روش دقیق‌تر برای خانه
                if house and unit_owner not in house.residents.all():
                    house.residents.add(unit_owner)

                # Renter logic...
                if is_renter:
                    current_renter = Renter.objects.filter(unit=self.object, renter_is_active=True).first()

                    def normalize(val):
                        if val is None:
                            return ''
                        if isinstance(val, str):
                            return val.strip()
                        return str(val)

                    renter_fields_changed = (
                            current_renter is None or
                            normalize(current_renter.renter_name) != normalize(form.cleaned_data.get('renter_name')) or
                            normalize(current_renter.renter_mobile) != normalize(
                        form.cleaned_data.get('renter_mobile')) or
                            normalize(current_renter.renter_national_code) != normalize(
                        form.cleaned_data.get('renter_national_code')) or
                            normalize(current_renter.renter_people_count) != normalize(
                        form.cleaned_data.get('renter_people_count')) or
                            current_renter.start_date != form.cleaned_data.get('start_date') or
                            current_renter.end_date != form.cleaned_data.get('end_date') or
                            normalize(current_renter.contract_number) != normalize(
                        form.cleaned_data.get('contract_number')) or
                            normalize(current_renter.estate_name) != normalize(form.cleaned_data.get('estate_name')) or
                            int(current_renter.first_charge or 0) != int(form.cleaned_data.get('first_charge') or 0) or
                            normalize(current_renter.renter_details) != normalize(
                        form.cleaned_data.get('renter_details'))
                    )

                    if renter_fields_changed:
                        Renter.objects.filter(unit=self.object, renter_is_active=True).update(renter_is_active=False)
                        Renter.objects.create(
                            unit=self.object,
                            renter_name=form.cleaned_data.get('renter_name'),
                            renter_mobile=form.cleaned_data.get('renter_mobile'),
                            renter_national_code=form.cleaned_data.get('renter_national_code'),
                            renter_people_count=form.cleaned_data.get('renter_people_count'),
                            start_date=form.cleaned_data.get('start_date'),
                            end_date=form.cleaned_data.get('end_date'),
                            contract_number=form.cleaned_data.get('contract_number'),
                            estate_name=form.cleaned_data.get('estate_name'),
                            first_charge=form.cleaned_data.get('first_charge') or 0,
                            renter_details=form.cleaned_data.get('renter_details'),
                            renter_is_active=True
                        )

                messages.success(self.request, f'واحد {self.object.unit} با موفقیت به‌روزرسانی شد.')
                if is_renter and renter_fields_changed:
                    messages.success(self.request, 'اطلاعات مستأجر جدید ثبت شد.')

                return super().form_valid(form)

        except Exception as e:
            form.add_error(None, f"خطا در ذخیره اطلاعات: {str(e)}")
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['units'] = Unit.objects.all()
        return context

    def get_initial(self):
        initial = super().get_initial()

        if self.object.user:
            initial['mobile'] = self.object.user.mobile
        try:
            renter = Renter.objects.get(unit=self.object, renter_is_active=True)

            if renter.renter_name:
                initial.update({
                    'is_owner': 'True',
                    'renter_name': renter.renter_name,
                    'renter_mobile': renter.renter_mobile,
                    'renter_national_code': renter.renter_national_code,
                    'renter_people_count': renter.renter_people_count,
                    'start_date': renter.start_date,
                    'end_date': renter.end_date,
                    'contract_number': renter.contract_number,
                    'estate_name': renter.estate_name,
                    'first_charge': renter.first_charge,
                    'renter_details': renter.renter_details,
                })
            else:
                initial['is_renter'] = 'False'
        except Renter.DoesNotExist:
            initial['is_renter'] = 'False'
        return initial


@method_decorator(middle_admin_required, name='dispatch')
class MiddleUnitInfoView(DetailView):
    model = Unit
    template_name = 'middle_unit_templates/unit_info.html'
    context_object_name = 'unit'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        unit = self.object
        context['renters'] = unit.renters.exclude(first_charge=0).order_by('-renter_is_active', '-start_date')
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

        return queryset.filter(filters).distinct().order_by('unit')

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
            ws.cell(row=row_num, column=22, value=renter.first_charge)

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
                jalali_from = jdatetime.datetime.strptime(from_date_str, '%Y/%m/%d')
                gregorian_from = jalali_from.togregorian().date()
                queryset = queryset.filter(date__gte=gregorian_from)

            if to_date_str:
                jalali_to = jdatetime.datetime.strptime(to_date_str, '%Y/%m/%d')
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

            Fund.objects.create(
                user=self.request.user,
                content_type=content_type,
                object_id=self.object.id,
                bank=self.object.bank,
                amount=self.object.amount or 0,
                debtor_amount=self.object.amount or 0,
                creditor_amount=0,
                payment_date=self.object.doc_date,
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        incomes = self.get_queryset()  # از get_queryset برای دریافت داده‌های فیلتر شده استفاده می‌کنیم
        paginator = Paginator(incomes, 50)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context['page_obj'] = page_obj
        context['total_incomes'] = Income.objects.filter(user=self.request.user).count()
        context['categories'] = IncomeCategory.objects.filter(user=self.request.user)

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
                payer_name=payer_name_for_fund,
                payment_gateway='کارت به کارت',
                payment_date=self.object.doc_date,
                payment_description=f"حسابهای دریافتنی: {self.object.description[:50]}",
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

                fund.amount = receive.amount or 0
                fund.debtor_amount = receive.amount or 0
                fund.creditor_amount = 0
                fund.payment_date = receive.doc_date
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
                    payer_name=payer_name_for_fund,
                    payment_description=f"حسابهای دریافتنی: {(receive.description or '')[:50]}",
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
                payment_date=self.object.document_date,
                payment_description=f"حسابهای پرداختنی: {self.object.description[:50]}",
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
                fund.receiver_name = receiver_name_for_fund
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
                    receiver_name= receiver_name_for_fund,
                    payment_date=payment.document_date,
                    payment_description=f"حسابهای پرداختنی: {(payment.description or '')[:50]}"
                )

            # ثبت فایل‌های پیوست جدید
            files = request.FILES.getlist('document')
            for f in files:
                PayDocument.objects.create(payment=payment, document=f)

            messages.success(request, 'سند با موفقیت ویرایش گردید.')
            return redirect(reverse('middle_add_pay'))  # Adjust redirect as necessary

        else:
            messages.error(request, 'خطا در ویرایش فرم درآمد. لطفا دوباره تلاش کنید.')
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
                jalali_from = jdatetime.datetime.strptime(from_date_str, '%Y/%m/%d')
                gregorian_from = jalali_from.togregorian().date()
                queryset = queryset.filter(property_purchase_date__gte=gregorian_from)

            if to_date_str:
                jalali_to = jdatetime.datetime.strptime(to_date_str, '%Y/%m/%d')
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
        units = Unit.objects.filter(is_active=True, user__manager=self.request.user)

        if not units.exists():
            messages.error(self.request,
                           'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدهای ساختمان را ثبت کنید و مجددا تلاش نمایید.')
            return redirect('middle_manage_unit')

        fix_charge = form.save(commit=False)
        fix_charge.name = charge_name
        fix_charge.user = self.request.user

        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        form.instance.unit_count = unit_count

        fix_charge.civil = fix_charge.civil or 0
        fix_charge.payment_penalty_amount = fix_charge.payment_penalty_amount or 0
        fix_charge.other_cost_amount = fix_charge.other_cost_amount or 0
        fix_charge.save()

        messages.success(self.request, 'شارژ با موفقیت ثبت گردید.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # context['charges'] = FixCharge.objects.filter(user=self.request.user).prefetch_related('fix_charge_amount')
        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        context['unit_count'] = unit_count

        charges = FixCharge.objects.filter(user=self.request.user).annotate(
            notified_count=Count(
                'fix_charge_amount',
                filter=Q(fix_charge_amount__send_notification=True)
            ),
            total_units=Count('fix_charge_amount')
        ).order_by('-created_at')
        context['charges'] = charges
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_fix_charge_edit(request, pk):
    charge = get_object_or_404(FixCharge, pk=pk)

    any_paid = FixedChargeCalc.objects.filter(fix_charge=charge, is_paid=True).exists()
    any_notify = FixedChargeCalc.objects.filter(fix_charge=charge, send_notification=True).exists()
    if any_paid:
        return redirect(f"{reverse('middle_add_fixed_charge')}?error=paid")

    if any_notify:
        return redirect(f"{reverse('middle_add_fixed_charge')}?error=notify")

    if request.method == 'POST':
        form = FixChargeForm(request.POST, request.FILES, instance=charge)
        if form.is_valid():
            charge = form.save(commit=False)
            charge.save()

            FixedChargeCalc.objects.filter(fix_charge=charge).update(
                amount=charge.fix_amount,
                civil_charge=charge.civil,
                payment_deadline_date=charge.payment_deadline,
                payment_penalty=charge.payment_penalty_amount,
                charge_name=charge.name,
                unit_count=charge.unit_count,
                details=charge.details,
                base_charge=charge.total_charge_month,
                other_cost=charge.other_cost_amount,
                total_charge_month=charge.total_charge_month
            )
            messages.success(request, 'شارژ با موفقیت ویرایش شد.')
            return redirect('middle_add_fixed_charge')
        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
            return render(request, 'middleCharge/fix_charge_template.html', {'form': form, 'charge': charge})
    else:
        form = FixChargeForm(instance=charge)
        return render(request, 'middleCharge/fix_charge_template.html', {'form': form, 'charge': charge})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_fix_charge_delete(request, pk):
    charge = get_object_or_404(FixCharge, id=pk)

    # بررسی اینکه هیچ رکورد FixedChargeCalc با is_paid=True وجود نداشته باشد
    paid_calc_exists = charge.fix_charge_amount.filter(is_paid=True).exists()
    if paid_calc_exists:
        messages.error(request, "امکان حذف شارژ وجود ندارد چون پرداخت شارژ توسط واحد ثبت شده است.")
        return redirect(reverse('middle_add_fixed_charge'))

    # چک کردن وجود رکوردهایی که send_notification == True هستند
    notification_exists = charge.fix_charge_amount.filter(send_notification=True).exists()
    if notification_exists:
        messages.error(request, "برای این شارژ اطلاعیه صادر شده است.ابتدا اطلاعیه شارژ را حذف و مجددا تلاش نمایید!")
        return redirect(reverse('middle_add_fixed_charge'))
    try:
        charge.delete()
        messages.success(request, f'{charge.name} با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, "امکان حذف این شارژ به دلیل وابستگی وجود ندارد!")
    return redirect(reverse('middle_add_fixed_charge'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_show_fix_charge_notification_form(request, pk):
    charge = get_object_or_404(FixCharge, id=pk)  # شیء اصلی شارژ ثابت
    units = Unit.objects.filter(is_active=True, user__manager=request.user).order_by('unit')

    notified_ids = FixedChargeCalc.objects.filter(
        fix_charge=charge,
        send_notification=True,
        user__manager=request.user
    ).values_list('unit_id', flat=True)

    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    units_with_active_renter = []

    calc_map = {
        (calc.unit_id): calc
        for calc in FixedChargeCalc.objects.filter(fix_charge=charge, user__manager=request.user)
    }
    for unit in units:
        active_renter = unit.renters.filter(renter_is_active=True).first()
        calc = calc_map.get(unit.id)
        total_charge = charge.total_charge_month
        is_paid = calc.is_paid if calc else False
        units_with_active_renter.append((unit, active_renter, is_paid, total_charge))

    # Pagination
    per_page = request.GET.get('per_page', 30)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 30

    paginator = Paginator(units_with_active_renter, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'charge': charge,  # این خط اضافه شد
        'pk': pk,
        'notified_ids': list(notified_ids),  # ارسال به قالب
    }

    return render(request, 'middleCharge/notify_fix_charge_template.html', context)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
@require_POST
def middle_send_notification_fix_charge_to_user(request, pk):
    fix_charge = get_object_or_404(FixCharge, id=pk)
    selected_units = request.POST.getlist('units')
    default_bank = Bank.objects.filter(user=request.user, is_default=True, is_active=True).first()

    if not selected_units:
        messages.warning(request, 'هیچ واحدی انتخاب نشده است.')
        return redirect('middle_show_notification_fix_charge_form', pk=pk)

    units_qs = Unit.objects.filter(is_active=True)

    if 'all' in selected_units:
        units_to_notify = units_qs
    else:
        units_to_notify = units_qs.filter(id__in=selected_units)

    if not units_to_notify.exists():
        messages.warning(request, 'هیچ واحد معتبری برای ارسال اطلاعیه پیدا نشد.')
        return redirect('middle_show_notification_fix_charge_form', pk=pk)

    notified_units = []
    charge_type = 'fixed'  # نوع شارژ (با سیستم شما هماهنگ است)

    with transaction.atomic():
        for unit in units_to_notify:

            fixed_calc, created = FixedChargeCalc.objects.get_or_create(
                unit=unit,
                fix_charge=fix_charge,
                defaults={
                    'user': unit.user,
                    'amount': fix_charge.fix_amount,
                    'civil_charge': fix_charge.civil,
                    'payment_deadline_date': fix_charge.payment_deadline,
                    'payment_penalty': fix_charge.payment_penalty_amount,
                    'charge_name': fix_charge.name,
                    'unit_count': fix_charge.unit_count,
                    'details': fix_charge.details,
                    'base_charge': fix_charge.total_charge_month,
                    'other_cost': fix_charge.other_cost_amount,
                    'send_notification': True,
                    'send_notification_date': timezone.now().date(),
                    'bank': default_bank
                }
            )

            # اگر قبلاً بوده ولی notify نشده بود → فعالش کن
            if not created and not fixed_calc.send_notification:
                fixed_calc.send_notification = True
                fixed_calc.send_notification_date = timezone.now().date()
                fixed_calc.bank = default_bank
                fixed_calc.save()  # ⚡ محاسبه total و penalty انجام می‌شود

            fixed_calc.save()

            # ثبت این واحد در لیست ارسال‌شده‌ها
            notified_units.append(str(unit))

            # ---- ساخت یا آپدیت UnifiedCharge ----
            fixed_calc_ct = ContentType.objects.get_for_model(FixedChargeCalc)

            UnifiedCharge.objects.update_or_create(
                content_type=fixed_calc_ct,
                object_id=fixed_calc.id,
                defaults={
                    'user': fixed_calc.user,
                    'unit': fixed_calc.unit,  # اضافه شد
                    'charge_type': charge_type,
                    'amount': fixed_calc.base_charge or 0,  # شارژ اصلی
                    'penalty_amount': fixed_calc.payment_penalty_price or 0,  # جریمه
                    'total_charge_month': fixed_calc.total_charge_month or 0,  # شارژ ماهانه
                    'title': fixed_calc.charge_name,
                    'details': fix_charge.details,
                    'civil': fixed_calc.civil_charge,
                    'other_cost_amount': fixed_calc.other_cost,
                    'send_notification_date': fixed_calc.send_notification_date,
                    'payment_deadline_date': fixed_calc.payment_deadline_date,
                    'send_notification': True,
                    'bank': default_bank
                }
            )

        # total_charge = fixed_calc.total_charge_month or 0
        # helper.send_notify_user_by_sms(
        #     unit.user.username,
        #     fix_charge=total_charge,
        #     name=unit.user.name,
        #     otp=None
        # )

        fix_charge.send_notification = True
        fix_charge.send_sms = True
        fix_charge.save()

    if notified_units:
        messages.success(request, 'اطلاعیه برای واحدهای انتخابی ارسال شد!')
    else:
        messages.info(request, 'اطلاعیه‌ای ارسال نشد؛ ممکن است قبلاً برای واحد انتخابی ثبت شده باشد.')

    return redirect('middle_show_notification_fix_charge_form', pk=pk)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_remove_send_notification_fix(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'فقط درخواست‌های POST مجاز است.'}, status=400)

    charge = get_object_or_404(FixCharge, id=pk)
    selected_units = request.POST.getlist('units[]')

    if not selected_units:
        return JsonResponse({'warning': 'هیچ واحدی انتخاب نشده است.'})

    charge_type_ct = ContentType.objects.get_for_model(FixedChargeCalc)

    try:
        with transaction.atomic():
            # =========================
            # حذف همه واحدها
            # =========================
            if selected_units == ['all']:
                qs = FixedChargeCalc.objects.filter(
                    fix_charge=charge,
                    is_paid=False
                )

                calc_ids = list(qs.values_list('id', flat=True))
                deleted_count = qs.count()
                qs.delete()

                # حذف UnifiedCharge مربوطه
                UnifiedCharge.objects.filter(
                    content_type=charge_type_ct,
                    object_id__in=calc_ids
                ).delete()

            else:
                # =========================
                # حذف واحدهای مشخص
                # =========================
                try:
                    selected_unit_ids = [int(uid) for uid in selected_units]
                except ValueError:
                    return JsonResponse({'error': 'شناسه واحد نامعتبر است.'}, status=400)

                units_qs = Unit.objects.filter(id__in=selected_unit_ids, is_active=True)

                if not units_qs.exists():
                    return JsonResponse({'warning': 'هیچ واحد معتبری یافت نشد.'})

                qs = FixedChargeCalc.objects.filter(
                    fix_charge=charge,
                    unit__in=units_qs,
                    is_paid=False
                )

                calc_ids = list(qs.values_list('id', flat=True))
                deleted_count = qs.count()
                qs.delete()

                # حذف UnifiedCharge مربوطه
                UnifiedCharge.objects.filter(
                    content_type=charge_type_ct,
                    object_id__in=calc_ids
                ).delete()

            # اگر هیچ رکوردی باقی نماند → اعلان غیرفعال شود
            if not FixedChargeCalc.objects.filter(fix_charge=charge).exists():
                charge.send_notification = False
                charge.save()

        if deleted_count:
            return JsonResponse({'success': f'{deleted_count} اطلاعیه حذف شد.'})
        else:
            return JsonResponse({'info': 'رکوردی برای حذف یافت نشد.'})

    except Exception as e:
        return JsonResponse({'error': f'خطایی هنگام حذف اطلاعیه‌ها رخ داد: {str(e)}'}, status=500)


# ========================================== Area Charge =======================
@method_decorator(middle_admin_required, name='dispatch')
class MiddleAreaChargeCreateView(CreateView):
    model = AreaCharge
    template_name = 'middleCharge/area_charge_template.html'
    form_class = AreaChargeForm
    success_url = reverse_lazy('middle_add_area_charge')

    def form_valid(self, form):
        units = Unit.objects.filter(is_active=True, user__manager=self.request.user)

        if not units.exists():
            messages.error(self.request,
                           'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدهای ساختمان را ثبت کنید و مجددا تلاش نمایید.')
            return redirect('middle_manage_unit')

        area_charge = form.save(commit=False)
        area_charge.name = form.cleaned_data.get('name') or 'بدون عنوان'
        area_charge.user = self.request.user

        area_charge.civil = area_charge.civil or 0
        area_charge.payment_penalty_amount = area_charge.payment_penalty_amount or 0
        area_charge.other_cost_amount = area_charge.other_cost_amount or 0

        area_charge.total_area = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('area'))['total'] or 0

        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        form.instance.unit_count = unit_count

        try:
            area_charge.save()
            messages.success(self.request, 'محاسبه شارژ با موفقیت ثبت گردید')
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'خطا در ثبت! {str(e)}')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        unit_count = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).count()

        total_area = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('area'))['total'] or 0

        total_people = Unit.objects.filter(
            is_active=True,
            user=self.request.user
        ).aggregate(total=Sum('people_count'))['total'] or 0

        charges = AreaCharge.objects.annotate(
            notified_count=Count(
                'area_charge_amount',
                filter=Q(area_charge_amount__send_notification=True)
            ),
            total_units=Count('area_charge_amount')
        ).order_by('-created_at')

        context.update({
            'unit_count': unit_count,
            'total_area': total_area,
            'total_people': total_people,
            'charges': charges,
        })
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_area_charge_edit(request, pk):
    charge = get_object_or_404(AreaCharge, pk=pk)

    any_paid = AreaChargeCalc.objects.filter(area_charge=charge, is_paid=True).exists()
    any_notify = AreaChargeCalc.objects.filter(area_charge=charge, send_notification=True).exists()
    if any_paid:
        return redirect(f"{reverse('middle_add_area_charge')}?error=paid")

    if any_notify:
        return redirect(f"{reverse('middle_add_area_charge')}?error=notify")

    if request.method == 'POST':
        form = AreaChargeForm(request.POST, request.FILES, instance=charge)
        if form.is_valid():
            charge = form.save(commit=False)
            charge.other_cost_amount = charge.other_cost_amount
            charge.details = charge.details
            charge.save()
            messages.success(request, 'شارژ با موفقیت ویرایش شد.')
            return redirect('middle_add_area_charge')
        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
            return render(request, 'middleCharge/area_charge_template.html', {'form': form, 'charge': charge})
    else:
        form = AreaChargeForm(instance=charge)
        return render(request, 'middleCharge/area_charge_template.html', {'form': form, 'charge': charge})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_area_charge_delete(request, pk):
    charge = get_object_or_404(AreaCharge, id=pk)

    # بررسی اینکه هیچ رکورد FixedChargeCalc با is_paid=True وجود نداشته باشد
    paid_calc_exists = charge.area_charge_amount.filter(is_paid=True).exists()
    if paid_calc_exists:
        messages.error(request, "امکان حذف شارژ وجود ندارد چون پرداخت شارژ توسط واحد ثبت شده است.")
        return redirect(reverse('middle_add_area_charge'))

    # چک کردن وجود رکوردهایی که send_notification == True هستند
    notification_exists = charge.area_charge_amount.filter(send_notification=True).exists()
    if notification_exists:
        messages.error(request, "برای این شارژ اطلاعیه صادر شده است.ابتدا اطلاعیه شارژ را حذف و مجددا تلاش نمایید!")
        return redirect(reverse('middle_add_area_charge'))
    try:
        charge.delete()
        messages.success(request, f'{charge.name} با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, "امکان حذف این شارژ به دلیل وابستگی وجود ندارد!")
    return redirect(reverse('middle_add_area_charge'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_calculate_total_charge_area(unit, charge):
    try:
        area = float(unit.area or 0)
        amount = float(charge.area_amount or 0)
        civil = float(charge.civil or 0)
        other_cost = float(charge.other_cost_amount or 0)

    except (TypeError, ValueError):
        area = amount = civil = other_cost = 0.0

    final_area_amount = amount * area
    total_charge = final_area_amount + civil + other_cost
    return total_charge


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_show_area_charge_notification_form(request, pk):
    charge = get_object_or_404(AreaCharge, id=pk)

    units = Unit.objects.filter(
        is_active=True,
        user__manager=request.user
    ).order_by('unit')

    # واحدهایی که نوتیفیکیشن گرفته‌اند
    notified_ids = list(
        AreaChargeCalc.objects.filter(
            area_charge=charge,
            send_notification=True
        ).values_list('unit_id', flat=True)
    )

    # سرچ
    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    # تمام رکوردهای calc یک‌باره گرفته شوند
    calc_map = {
        c.unit_id: c for c in AreaChargeCalc.objects.filter(area_charge=charge)
    }

    units_with_details = []

    for unit in units:
        active_renter = unit.renters.filter(renter_is_active=True).first()

        calc = calc_map.get(unit.id)
        total_charge = middle_calculate_total_charge_area(unit, charge)
        is_paid = calc.is_paid if calc else False

        defaults = {
            'civil_charge': charge.civil,
            'total_area': charge.total_area,
            'unit_count': charge.unit_count,
            'details': charge.details,
            'other_cost': charge.other_cost_amount,
            'charge_name': charge.name,
            'amount': int(charge.area_amount or 0),
            'payment_penalty': charge.payment_penalty_amount,
            'payment_deadline_date': charge.payment_deadline,
            'base_charge': int(total_charge),
            'final_area_amount': int(charge.area_amount or 0) * int(unit.area or 0),
        }

        AreaChargeCalc.objects.update_or_create(
            user=unit.user,
            unit=unit,
            area_charge=charge,
            defaults=defaults
        )

        units_with_details.append((unit, active_renter, is_paid, total_charge))

    # pagination
    try:
        per_page = int(request.GET.get('per_page', 30))
    except ValueError:
        per_page = 30

    paginator = Paginator(units_with_details, per_page)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'charge': charge,
        'pk': pk,
        'notified_ids': notified_ids,
    }
    return render(request, 'middleCharge/notify_area_charge_template.html', context)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
@require_POST
def middle_send_notification_area_charge_to_user(request, pk):
    area_charge = get_object_or_404(AreaCharge, id=pk)
    selected_units = request.POST.getlist('units')

    if not selected_units:
        messages.warning(request, 'هیچ واحدی انتخاب نشده است.')
        return redirect('middle_show_notification_area_charge_form', pk=pk)

    # 🔥 مهم: فقط واحدهای این مدیر
    units_qs = Unit.objects.filter(is_active=True, user__manager=request.user)

    units_to_notify = (
        units_qs if 'all' in selected_units
        else units_qs.filter(id__in=selected_units)
    )

    if not units_to_notify.exists():
        messages.warning(request, 'هیچ واحد معتبری برای ارسال اطلاعیه پیدا نشد.')
        return redirect('middle_show_notification_area_charge_form', pk=pk)

    charge_type = 'area'
    calc_ct = ContentType.objects.get_for_model(AreaChargeCalc)
    default_bank = Bank.objects.filter(user=request.user, is_default=True, is_active=True).first()

    with transaction.atomic():
        for unit in units_to_notify:

            total_charge = middle_calculate_total_charge_area(unit, area_charge)

            calc_obj, created = AreaChargeCalc.objects.get_or_create(
                unit=unit,
                area_charge=area_charge,
                defaults={
                    'user': unit.user,
                    'amount': area_charge.area_amount,
                    'civil_charge': area_charge.civil,
                    'other_cost': area_charge.other_cost_amount,
                    'charge_name': area_charge.name,
                    'details': area_charge.details,
                    'base_charge': total_charge,
                    'final_area_amount': float(area_charge.area_amount or 0) * float(unit.area or 0),
                    'payment_deadline_date': area_charge.payment_deadline,
                    'payment_penalty_price': area_charge.payment_penalty_amount,
                    'send_notification': True,
                    'send_notification_date': timezone.now().date(),
                    'bank': default_bank
                }
            )

            # اگر قبلاً وجود داشته اما notify نشده
            if not created and not calc_obj.send_notification:
                calc_obj.send_notification = True
                calc_obj.send_notification_date = timezone.now().date()
                calc_obj.base_charge = total_charge
                calc_obj.final_area_amount = float(area_charge.area_amount or 0) * float(unit.area or 0)
                calc_obj.bank = default_bank

                # اجرای محاسبه‌های مدل
            calc_obj.save()

            # بروزرسانی UnifiedCharge
            UnifiedCharge.objects.update_or_create(
                content_type=calc_ct,
                object_id=calc_obj.id,
                defaults={
                    'user': calc_obj.user,
                    'unit': calc_obj.unit,
                    'charge_type': charge_type,
                    'amount': calc_obj.base_charge or 0,
                    'penalty_amount': calc_obj.payment_penalty_price or 0,
                    'total_charge_month': calc_obj.total_charge_month or 0,
                    'title': calc_obj.charge_name,
                    'details': calc_obj.details,
                    'civil': calc_obj.civil_charge,
                    'other_cost_amount': calc_obj.other_cost,
                    'send_notification_date': calc_obj.send_notification_date,
                    'payment_deadline_date': calc_obj.payment_deadline_date,
                    'send_notification': True,
                    'bank': default_bank,
                }
            )

        area_charge.send_notification = True
        area_charge.send_sms = True
        area_charge.save()

    messages.success(request, 'اطلاعیه برای واحدهای انتخابی ارسال شد!')
    return redirect('middle_show_notification_area_charge_form', pk=pk)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_remove_send_notification_area(request, pk):
    if request.method != 'POST' or request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'error': 'درخواست نامعتبر است.'}, status=400)

    charge = get_object_or_404(AreaCharge, id=pk)
    unit_ids = request.POST.getlist('units[]')
    charge_type_ct = ContentType.objects.get_for_model(AreaChargeCalc)

    if not unit_ids:
        return JsonResponse({'error': 'هیچ واحدی انتخاب نشده است.'})

    try:
        # ================================
        # ✔ حالت حذف همه
        # ================================
        if 'all' in unit_ids:

            qs = AreaChargeCalc.objects.filter(
                area_charge=charge,
                is_paid=False
            )

            calc_ids = list(qs.values_list('id', flat=True))
            deleted_count = qs.count()

            # حذف AreaChargeCalc
            qs.delete()

            # حذف UnifiedCharge مرتبط
            UnifiedCharge.objects.filter(
                content_type=charge_type_ct,
                object_id__in=calc_ids
            ).delete()

            # اگر هیچ رکوردی نماند → اعلان غیرفعال شود
            if not AreaChargeCalc.objects.filter(area_charge=charge).exists():
                charge.send_notification = False
                charge.save()

            return JsonResponse({'success': f'{deleted_count} اطلاعیه با موفقیت حذف شد.'})

        # ================================
        # ✔ حالت حذف انتخابی
        # ================================
        try:
            selected_ids = [int(uid) for uid in unit_ids]
        except ValueError:
            return JsonResponse({'error': 'شناسه‌های ارسال‌شده معتبر نیستند.'}, status=400)

        # اطلاعیه صادر نشده
        not_send = AreaChargeCalc.objects.filter(
            area_charge=charge,
            unit_id__in=selected_ids,
            send_notification=False
        )
        if not_send.exists():
            return JsonResponse({'error': 'اطلاعیه برای برخی واحدها صادر نشده است.'})

        # پرداخت شده → قابل حذف نیست
        paid_qs = AreaChargeCalc.objects.filter(
            area_charge=charge,
            unit_id__in=selected_ids,
            is_paid=True
        )
        if paid_qs.exists():
            return JsonResponse({'error': 'برخی واحدها پرداخت انجام داده‌اند؛ حذف ممکن نیست.'})

        # حذف رکوردهای انتخاب‌شده
        qs = AreaChargeCalc.objects.filter(
            area_charge=charge,
            unit_id__in=selected_ids,
            is_paid=False
        )

        calc_ids = list(qs.values_list('id', flat=True))
        deleted_count = qs.count()

        qs.delete()

        # حذف UnifiedCharge مربوط
        UnifiedCharge.objects.filter(
            content_type=charge_type_ct,
            object_id__in=calc_ids
        ).delete()

        # اگر همه رکوردها حذف شدند → اعلان غیرفعال شود
        if not AreaChargeCalc.objects.filter(area_charge=charge).exists():
            charge.send_notification = False
            charge.save()

        return JsonResponse({'success': f'{deleted_count} اطلاعیه حذف شد.'})

    except Exception as e:
        return JsonResponse({'error': 'خطایی هنگام حذف اطلاعیه‌ها رخ داد.'}, status=500)


# ======================= Person Charge ===============
@method_decorator(middle_admin_required, name='dispatch')
class MiddlePersonChargeCreateView(CreateView):
    model = PersonCharge
    template_name = 'middleCharge/person_charge_template.html'
    form_class = PersonChargeForm
    success_url = reverse_lazy('middle_add_person_charge')

    def form_valid(self, form):
        units = Unit.objects.filter(is_active=True, user__manager=self.request.user)

        if not units.exists():
            messages.error(self.request,
                           'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدهای ساختمان را ثبت کنید و مجددا تلاش نمایید.')
            return redirect('middle_manage_unit')
        person_charge = form.save(commit=False)
        charge_name = form.cleaned_data.get('name') or 0
        person_charge.name = charge_name
        person_charge.user = self.request.user

        person_charge.civil = person_charge.civil or 0
        person_charge.payment_penalty_amount = person_charge.payment_penalty_amount or 0
        person_charge.other_cost_amount = person_charge.other_cost_amount or 0

        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        form.instance.unit_count = unit_count

        person_charge.total_people = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('people_count'))['total'] or 0

        try:
            person_charge.save()
            self.object = person_charge
            messages.success(self.request, 'محاسبه شارژ با موفقیت ثبت گردید')
            return super().form_valid(form)
        except:
            messages.error(self.request, 'خطا در ثبت!')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # context['charges'] = PersonCharge.objects.all()
        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        context['unit_count'] = unit_count
        total_people = Unit.objects.filter(is_active=True, user__manager=self.request.user).aggregate(
            total=Sum('people_count'))['total'] or 0
        context['total_people'] = total_people

        charges = PersonCharge.objects.annotate(
            notified_count=Count(
                'person_charge_amount',
                filter=Q(person_charge_amount__send_notification=True)
            ),
            total_units=Count('person_charge_amount')
        ).order_by('-created_at')
        context['charges'] = charges
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_person_charge_edit(request, pk):
    charge = get_object_or_404(PersonCharge, pk=pk)

    any_paid = PersonChargeCalc.objects.filter(person_charge=charge, is_paid=True).exists()
    any_notify = PersonChargeCalc.objects.filter(person_charge=charge, send_notification=True).exists()
    if any_paid:
        return redirect(f"{reverse('middle_add_person_charge')}?error=paid")

    if any_notify:
        return redirect(f"{reverse('middle_add_person_charge')}?error=notify")

    if request.method == 'POST':
        form = PersonChargeForm(request.POST, request.FILES, instance=charge)
        if form.is_valid():
            charge = form.save(commit=False)
            charge.other_cost_amount = charge.other_cost_amount
            charge.details = charge.details
            charge.save()
            messages.success(request, 'شارژ با موفقیت ویرایش شد.')
            return redirect('middle_add_person_charge')
        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
            return render(request, 'middleCharge/person_charge_template.html', {'form': form, 'charge': charge})
    else:
        form = PersonChargeForm(instance=charge)
        return render(request, 'middleCharge/person_charge_template.html', {'form': form, 'charge': charge})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_person_charge_delete(request, pk):
    charge = get_object_or_404(PersonCharge, id=pk)

    # بررسی اینکه هیچ رکورد FixedChargeCalc با is_paid=True وجود نداشته باشد
    paid_calc_exists = charge.person_charge_amount.filter(is_paid=True).exists()
    if paid_calc_exists:
        messages.error(request, "امکان حذف شارژ وجود ندارد چون پرداخت شارژ توسط واحد ثبت شده است.")
        return redirect(reverse('middle_add_person_charge'))

    # چک کردن وجود رکوردهایی که send_notification == True هستند
    notification_exists = charge.person_charge_amount.filter(send_notification=True).exists()
    if notification_exists:
        messages.error(request, "برای این شارژ اطلاعیه صادر شده است.ابتدا اطلاعیه شارژ را حذف و مجددا تلاش نمایید!")
        return redirect(reverse('middle_add_person_charge'))
    try:
        charge.delete()
        messages.success(request, f'{charge.name} با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, "امکان حذف این شارژ به دلیل وابستگی وجود ندارد!")
    return redirect(reverse('middle_add_person_charge'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_calculate_total_charge_person(unit, charge):
    try:
        people_count = float(unit.people_count or 0)
        amount = float(charge.person_amount or 0)
        civil = float(charge.civil or 0)
        other_cost = float(charge.other_cost_amount or 0)
    except (TypeError, ValueError):
        people_count = amount = other_cost = civil = 0.0

    final_person_amount = amount * people_count
    total_charge = final_person_amount + civil + other_cost
    return total_charge


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_show_person_charge_notification_form(request, pk):
    charge = get_object_or_404(PersonCharge, id=pk)
    units = Unit.objects.filter(is_active=True, user__manager=request.user).order_by('unit')

    # لیست واحدهایی که قبلاً اعلان دریافت کرده‌اند
    notified_ids = PersonChargeCalc.objects.filter(
        person_charge=charge,
        send_notification=True
    ).values_list('unit_id', flat=True)

    # فیلتر جستجو
    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    # گرفتن رکوردهای موجود در دیتابیس
    existing_calcs = PersonChargeCalc.objects.filter(person_charge=charge, unit__in=units)
    calc_map = {calc.unit_id: calc for calc in existing_calcs}

    # آماده‌سازی لیست برای bulk_create و bulk_update
    to_create = []
    to_update = []

    units_with_details = []

    for unit in units:
        active_renter = unit.renters.filter(renter_is_active=True).first()
        total_charge = middle_calculate_total_charge_person(unit, charge)

        calc = calc_map.get(unit.id)

        defaults = {
            'unit_count': charge.unit_count,
            'details': charge.details,
            'other_cost': charge.other_cost_amount,
            'civil_charge': charge.civil,
            'charge_name': charge.name,
            'total_people': charge.total_people,
            'amount': int(charge.person_amount or 0),
            'payment_penalty': charge.payment_penalty_amount,
            'payment_deadline_date': charge.payment_deadline,
            'base_charge': int(total_charge),
            'final_person_amount': int(charge.person_amount or 0) * int(unit.people_count or 0),
        }

        if calc:
            # آپدیت رکورد موجود
            for field, value in defaults.items():
                setattr(calc, field, value)
            to_update.append(calc)
            is_paid = calc.is_paid
        else:
            # ایجاد رکورد جدید
            to_create.append(PersonChargeCalc(
                user=unit.user,
                unit=unit,
                person_charge=charge,
                **defaults
            ))
            is_paid = False

        units_with_details.append((unit, active_renter, is_paid, total_charge))

    # bulk_update و bulk_create
    if to_update:
        PersonChargeCalc.objects.bulk_update(to_update, fields=list(defaults.keys()))
    if to_create:
        PersonChargeCalc.objects.bulk_create(to_create)

    # Pagination
    try:
        per_page = int(request.GET.get('per_page', 30))
    except ValueError:
        per_page = 30

    paginator = Paginator(units_with_details, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'charge': charge,
        'pk': pk,
        'notified_ids': list(notified_ids),
    }

    return render(request, 'middleCharge/notify_person_charge_template.html', context)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
@require_POST
def middle_send_notification_person_charge_to_user(request, pk):
    person_charge = get_object_or_404(PersonCharge, id=pk)
    selected_units = request.POST.getlist('units')
    default_bank = Bank.objects.filter(user=request.user, is_default=True, is_active=True).first()

    if not selected_units:
        messages.warning(request, 'هیچ واحدی انتخاب نشده است.')
        return redirect('middle_show_notification_person_charge_form', pk=pk)

    # فقط واحدهای زیرمجموعه این مدیر
    units_qs = Unit.objects.filter(is_active=True, user__manager=request.user)

    units_to_notify = (
        units_qs if 'all' in selected_units
        else units_qs.filter(id__in=selected_units)
    )

    if not units_to_notify.exists():
        messages.warning(request, 'هیچ واحد معتبری برای ارسال اطلاعیه پیدا نشد.')
        return redirect('middle_show_notification_person_charge_form', pk=pk)

    calc_ct = ContentType.objects.get_for_model(PersonChargeCalc)
    charge_type = 'person'

    with transaction.atomic():

        for unit in units_to_notify:

            # 🔥 محاسبه پایه شارژ بدون جریمه
            total_charge = middle_calculate_total_charge_person(unit, person_charge)

            calc_obj, created = PersonChargeCalc.objects.get_or_create(
                unit=unit,
                person_charge=person_charge,
                defaults={
                    'user': unit.user,
                    'amount': person_charge.person_amount,
                    'final_person_amount': float(person_charge.person_amount or 0) * float(unit.people_count or 0),
                    'civil_charge': person_charge.civil,
                    'other_cost': person_charge.other_cost_amount,
                    'charge_name': person_charge.name,
                    'details': person_charge.details,
                    'base_charge': total_charge,
                    'payment_deadline_date': person_charge.payment_deadline,
                    'payment_penalty': person_charge.payment_penalty_amount,
                    'send_notification': True,
                    'send_notification_date': timezone.now().date(),
                    'bank': default_bank
                }
            )

            # اگر قبلاً وجود داشته ولی notify نشده بود
            if not created and not calc_obj.send_notification:
                calc_obj.send_notification = True
                calc_obj.send_notification_date = timezone.now().date()
                calc_obj.base_charge = total_charge
                calc_obj.bank = default_bank
                calc_obj.final_person_amount = float(person_charge.person_amount or 0) * float(unit.people_count or 0)

            # 🔥 save() مدل → محاسبه total_charge_month و جریمه
            calc_obj.save()

            # بروزرسانی UnifiedCharge
            UnifiedCharge.objects.update_or_create(
                content_type=calc_ct,
                object_id=calc_obj.id,
                defaults={
                    'user': calc_obj.user,
                    'unit': calc_obj.unit,
                    'charge_type': charge_type,
                    'amount': calc_obj.base_charge or 0,
                    'penalty_amount': calc_obj.payment_penalty_price or 0,
                    'total_charge_month': calc_obj.total_charge_month or 0,
                    'title': calc_obj.charge_name,
                    'details': calc_obj.details,
                    'civil': calc_obj.civil_charge,
                    'other_cost_amount': calc_obj.other_cost,
                    'send_notification_date': calc_obj.send_notification_date,
                    'payment_deadline_date': calc_obj.payment_deadline_date,
                    'send_notification': True,
                    'bank': default_bank
                }
            )

        # فعال‌سازی وضعیت ارسال اطلاعیه
        person_charge.send_notification = True
        person_charge.send_sms = True
        person_charge.save()

    messages.success(request, 'اطلاعیه برای واحدهای انتخابی ارسال شد!')
    return redirect('middle_show_notification_person_charge_form', pk=pk)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_remove_send_notification_person(request, pk):
    if request.method != 'POST' or request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'error': 'درخواست نامعتبر است.'}, status=400)

    charge = get_object_or_404(PersonCharge, id=pk)
    unit_ids = request.POST.getlist('units[]')
    charge_type = 'person'  # نوع برای UnifiedCharge
    charge_type_ct = ContentType.objects.get_for_model(PersonChargeCalc)

    if not unit_ids:
        return JsonResponse({'error': 'هیچ واحدی انتخاب نشده است.'})

    try:
        # ================================
        # ✔ حالت حذف همه
        # ================================
        if 'all' in unit_ids:

            qs = PersonChargeCalc.objects.filter(
                person_charge=charge,
                is_paid=False
            )
            calc_ids = list(qs.values_list('id', flat=True))
            deleted_count = qs.count()

            qs.delete()

            # حذف UnifiedCharge مرتبط
            UnifiedCharge.objects.filter(
                content_type=charge_type_ct,
                object_id__in=calc_ids
            ).delete()

            # اگر هیچ رکوردی نماند → اعلان غیرفعال شود
            if not PersonChargeCalc.objects.filter(person_charge=charge).exists():
                charge.send_notification = False
                charge.save()

            return JsonResponse({'success': f'{deleted_count} اطلاعیه با موفقیت حذف شد.'})

        # ================================
        # ✔ حالت حذف انتخابی
        # ================================
        selected_ids = [int(uid) for uid in unit_ids if uid.isdigit()]

        # اطلاعیه صادر نشده
        not_send = PersonChargeCalc.objects.filter(
            person_charge=charge,
            unit_id__in=selected_ids,
            send_notification=False
        )
        if not_send.exists():
            return JsonResponse({'error': 'اطلاعیه برای برخی واحدها صادر نشده است.'})

        # پرداخت شده → قابل حذف نیست
        paid_qs = PersonChargeCalc.objects.filter(
            person_charge=charge,
            unit_id__in=selected_ids,
            is_paid=True
        )
        if paid_qs.exists():
            return JsonResponse({'error': 'برخی واحدها پرداخت انجام داده‌اند؛ حذف ممکن نیست.'})

        # حذف رکوردهای انتخاب‌شده
        qs = PersonChargeCalc.objects.filter(
            person_charge=charge,
            unit_id__in=selected_ids,
            is_paid=False
        )
        calc_ids = list(qs.values_list('id', flat=True))
        deleted_count = qs.count()
        qs.delete()

        # حذف UnifiedCharge مربوط
        UnifiedCharge.objects.filter(
            content_type=charge_type_ct,
            object_id__in=calc_ids
        ).delete()

        # اگر همه رکوردها حذف شدند → اعلان غیرفعال شود
        if not PersonChargeCalc.objects.filter(person_charge=charge).exists():
            charge.send_notification = False
            charge.save()

        return JsonResponse({'success': f'{deleted_count} اطلاعیه حذف شد.'})

    except Exception as e:
        return JsonResponse({'error': 'خطایی هنگام حذف اطلاعیه‌ها رخ داد.'}, status=500)


# ==================== Fix Area Charge    =============================
@method_decorator(middle_admin_required, name='dispatch')
class MiddleFixAreaChargeCreateView(CreateView):
    model = FixAreaCharge
    template_name = 'middleCharge/fix_area_charge_template.html'
    form_class = FixAreaChargeForm
    success_url = reverse_lazy('middle_add_fix_area_charge')

    def form_valid(self, form):
        units = Unit.objects.filter(is_active=True, user__manager=self.request.user)

        if not units.exists():
            messages.error(self.request,
                           'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدهای ساختمان را ثبت کنید و مجددا تلاش نمایید.')
            return redirect('middle_manage_unit')
        fix_area_charge = form.save(commit=False)

        charge_name = form.cleaned_data.get('name') or 0
        fix_area_charge.name = charge_name
        fix_area_charge.user = self.request.user

        fix_area_charge.civil = fix_area_charge.civil or 0
        fix_area_charge.payment_penalty_amount = fix_area_charge.payment_penalty_amount or 0
        fix_area_charge.other_cost_amount = fix_area_charge.other_cost_amount or 0

        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        form.instance.unit_count = unit_count

        total_area = Unit.objects.filter(is_active=True, user__manager=self.request.user).aggregate(total=Sum('area'))[
                         'total'] or 0
        print(f"Total people count calculated: {total_area}")  # Debug line
        fix_area_charge.total_area = total_area

        try:
            fix_area_charge.save()
            self.object = fix_area_charge
            messages.success(self.request, 'محاسبه شارژ با موفقیت ثبت گردید')
            return super().form_valid(form)
        except:
            messages.error(self.request, 'خطا در ثبت!')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unit_count'] = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        context['total_area'] = \
            Unit.objects.filter(is_active=True, user__manager=self.request.user).aggregate(total=Sum('area'))[
                'total'] or 0

        charges = FixAreaCharge.objects.annotate(
            notified_count=Count(
                'fix_area_charge',
                filter=Q(fix_area_charge__send_notification=True)
            ),
            total_units=Count('fix_area_charge')
        ).order_by('-created_at')
        context['charges'] = charges
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_fix_area_charge_edit(request, pk):
    charge = get_object_or_404(FixAreaCharge, pk=pk)

    any_paid = FixAreaChargeCalc.objects.filter(fix_area=charge, is_paid=True).exists()
    any_notify = FixAreaChargeCalc.objects.filter(fix_area=charge, send_notification=True).exists()
    if any_paid:
        return redirect(f"{reverse('middle_add_fix_area_charge')}?error=paid")

    if any_notify:
        return redirect(f"{reverse('middle_add_fix_area_charge')}?error=notify")

    if request.method == 'POST':
        form = FixAreaChargeForm(request.POST, request.FILES, instance=charge)
        if form.is_valid():
            charge = form.save(commit=False)
            charge.other_cost_amount = charge.other_cost_amount
            charge.details = charge.details
            charge.save()
            messages.success(request, 'شارژ با موفقیت ویرایش شد.')
            return redirect('middle_add_fix_area_charge')
        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
            return render(request, 'middleCharge/fix_area_charge_template.html', {'form': form, 'middleCharge': charge})
    else:
        form = FixAreaChargeForm(instance=charge)
        return render(request, 'middleCharge/fix_area_charge_template.html', {'form': form, 'middleCharge': charge})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_fix_area_charge_delete(request, pk):
    charge = get_object_or_404(FixAreaCharge, id=pk)

    # بررسی اینکه هیچ رکورد FixedChargeCalc با is_paid=True وجود نداشته باشد
    paid_calc_exists = charge.fix_area_charge.filter(is_paid=True).exists()
    if paid_calc_exists:
        messages.error(request, "امکان حذف شارژ وجود ندارد چون پرداخت شارژ توسط واحد ثبت شده است.")
        return redirect(reverse('middle_add_fix_area_charge'))

    # چک کردن وجود رکوردهایی که send_notification == True هستند
    notification_exists = charge.fix_area_charge.filter(send_notification=True).exists()
    if notification_exists:
        messages.error(request, "برای این شارژ اطلاعیه صادر شده است.ابتدا اطلاعیه شارژ را حذف و مجددا تلاش نمایید!")
        return redirect(reverse('middle_add_fix_area_charge'))
    try:
        charge.delete()
        messages.success(request, f'{charge.name} با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, "امکان حذف این شارژ به دلیل وابستگی وجود ندارد!")
    return redirect(reverse('middle_add_fix_area_charge'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_calculate_total_charge_fix_area(unit, charge):
    try:
        area = float(unit.area or 0)
        fix_charge_amount = float(charge.fix_charge_amount or 0)
        amount = float(charge.area_amount or 0)
        civil = float(charge.civil or 0)
        other_cost = float(charge.other_cost_amount or 0)
    except (TypeError, ValueError):
        area = fix_charge_amount = amount = civil = other_cost = 0.0

    final_person_amount = (amount * area) + fix_charge_amount
    total_charge = final_person_amount + civil + other_cost
    return total_charge


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_show_fix_area_charge_notification_form(request, pk):
    charge = get_object_or_404(FixAreaCharge, id=pk)
    units = Unit.objects.filter(is_active=True, user__manager=request.user).order_by('unit')

    notified_ids = FixAreaChargeCalc.objects.filter(
        fix_area=charge,
        send_notification=True
    ).values_list('unit_id', flat=True)

    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    existing_calcs = FixAreaChargeCalc.objects.filter(fix_area=charge, unit__in=units)
    calc_map = {calc.unit_id: calc for calc in existing_calcs}

    units_with_details = []

    for unit in units:
        active_renter = unit.renters.filter(renter_is_active=True).first()
        total_charge = middle_calculate_total_charge_fix_area(unit, charge)

        calc = calc_map.get(unit.id)

        if calc:
            # به روزرسانی رکورد موجود
            calc.unit_count = charge.unit_count
            calc.details = charge.details
            calc.other_cost = charge.other_cost_amount
            calc.civil_charge = charge.civil
            calc.charge_name = charge.name
            calc.amount = int(charge.area_amount or 0)
            calc.total_area = int(charge.total_area)
            calc.fix_charge = int(charge.fix_charge_amount or 0)
            calc.payment_penalty = charge.payment_penalty_amount
            calc.payment_deadline_date = charge.payment_deadline
            calc.base_charge = int(total_charge)
            calc.final_person_amount = int((charge.area_amount or 0) * int(unit.people_count or 0)) + int(
                charge.fix_charge_amount or 0)

            calc.save()  # اینجا save فراخوانی می‌شود و total_charge_month محاسبه می‌شود
            is_paid = calc.is_paid
        else:
            # ایجاد رکورد جدید
            calc = FixAreaChargeCalc(
                user=unit.user,
                unit=unit,
                fix_area=charge,
                unit_count=charge.unit_count,
                details=charge.details,
                other_cost=charge.other_cost_amount,
                civil_charge=charge.civil,
                charge_name=charge.name,
                amount=int(charge.area_amount or 0),
                total_area=int(charge.total_area),
                fix_charge=int(charge.fix_charge_amount or 0),
                payment_penalty=charge.payment_penalty_amount,
                payment_deadline_date=charge.payment_deadline,
                base_charge=int(total_charge),
                final_person_amount=int((charge.area_amount or 0) * int(unit.people_count or 0)) + int(
                    charge.fix_charge_amount or 0),
            )
            calc.save()  # save محاسبات را انجام می‌دهد
            is_paid = False

        units_with_details.append((unit, active_renter, is_paid, total_charge))

    # Pagination
    try:
        per_page = int(request.GET.get('per_page', 30))
    except ValueError:
        per_page = 30

    paginator = Paginator(units_with_details, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'charge': charge,
        'pk': pk,
        'notified_ids': list(notified_ids),
    }
    return render(request, 'middleCharge/notify_area_fix_charge_template.html', context)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
@require_POST
def middle_send_notification_fix_area_charge_to_user(request, pk):
    fix_area_charge = get_object_or_404(FixAreaCharge, id=pk)
    selected_units = [int(uid) for uid in request.POST.getlist('units') if uid.isdigit()]
    charge_type = 'fix_area'
    calc_ct = ContentType.objects.get_for_model(FixAreaChargeCalc)
    default_bank = Bank.objects.filter(user=request.user, is_default=True, is_active=True).first()

    if not selected_units:
        messages.warning(request, 'هیچ واحدی انتخاب نشده است.')
        return redirect('middle_show_notification_fix_area_charge_form', pk=pk)

    units_qs = Unit.objects.filter(is_active=True)
    units_to_notify = units_qs if 'all' in request.POST.getlist('units') else units_qs.filter(id__in=selected_units)

    if not units_to_notify.exists():
        messages.warning(request, 'هیچ واحد معتبری برای ارسال اطلاعیه پیدا نشد.')
        return redirect('middle_show_notification_fix_area_charge_form', pk=pk)

    notified_units = []

    with transaction.atomic():
        for unit in units_to_notify:
            calc_obj, created = FixAreaChargeCalc.objects.update_or_create(
                unit=unit,
                fix_area=fix_area_charge,
                defaults={
                    'user': unit.user,
                    'amount': fix_area_charge.area_amount,
                    'civil_charge': fix_area_charge.civil,
                    'charge_name': fix_area_charge.name,
                    'details': fix_area_charge.details,
                    'payment_deadline_date': fix_area_charge.payment_deadline,
                    'send_notification': True,
                    'send_notification_date': timezone.now().date(),
                    'bank': default_bank
                }
            )
            if not created and not calc_obj.send_notification:
                calc_obj.send_notification = True
                calc_obj.send_notification_date = timezone.now().date()
                calc_obj.bank = default_bank

                calc_obj.save()

            UnifiedCharge.objects.update_or_create(
                content_type=calc_ct,
                object_id=calc_obj.id,
                defaults={
                    'user': calc_obj.user,
                    'unit': calc_obj.unit,
                    'charge_type': charge_type,
                    'amount': calc_obj.base_charge or 0,
                    'penalty_amount': calc_obj.payment_penalty_price or 0,
                    'total_charge_month': calc_obj.total_charge_month or 0,
                    'title': calc_obj.charge_name,
                    'details': calc_obj.details,
                    'civil': calc_obj.civil_charge,
                    'other_cost_amount': calc_obj.other_cost,
                    'send_notification_date': calc_obj.send_notification_date,
                    'payment_deadline_date': calc_obj.payment_deadline_date,
                    'send_notification': True,
                    'bank': default_bank
                }
            )

            notified_units.append(str(unit))

        fix_area_charge.send_notification = True
        fix_area_charge.send_sms = True
        fix_area_charge.save()

    if notified_units:
        messages.success(request, 'اطلاعیه برای واحدهای انتخابی ارسال شد!')
    else:
        messages.info(request, 'اطلاعیه‌ای ارسال نشد؛ ممکن است قبلاً برای واحد انتخابی ثبت شده باشد.')

    return redirect('middle_show_notification_fix_area_charge_form', pk=pk)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_remove_send_notification_fix_area(request, pk):
    if request.method != 'POST' or request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'error': 'درخواست نامعتبر است.'}, status=400)

    charge = get_object_or_404(FixAreaCharge, id=pk)
    unit_ids = request.POST.getlist('units[]')
    charge_type = 'fix_area'  # نوع برای UnifiedCharge
    charge_type_ct = ContentType.objects.get_for_model(FixAreaChargeCalc)

    if not unit_ids:
        return JsonResponse({'error': 'هیچ واحدی انتخاب نشده است.'})

    try:
        # ================================
        # ✔ حالت حذف همه
        # ================================
        if 'all' in unit_ids:

            qs = FixAreaChargeCalc.objects.filter(
                fix_area=charge,
                is_paid=False
            )
            calc_ids = list(qs.values_list('id', flat=True))
            deleted_count = qs.count()

            qs.delete()

            # حذف UnifiedCharge مرتبط
            UnifiedCharge.objects.filter(
                content_type=charge_type_ct,
                object_id__in=calc_ids
            ).delete()

            # اگر هیچ رکوردی نماند → اعلان غیرفعال شود
            if not FixAreaChargeCalc.objects.filter(fix_area=charge).exists():
                charge.send_notification = False
                charge.save()

            return JsonResponse({'success': f'{deleted_count} اطلاعیه با موفقیت حذف شد.'})

        # ================================
        # ✔ حالت حذف انتخابی
        # ================================
        selected_ids = [int(uid) for uid in unit_ids if uid.isdigit()]

        # اطلاعیه صادر نشده
        not_send = FixAreaChargeCalc.objects.filter(
            fix_area=charge,
            unit_id__in=selected_ids,
            send_notification=False
        )
        if not_send.exists():
            return JsonResponse({'error': 'اطلاعیه برای برخی واحدها صادر نشده است.'})

        # پرداخت شده → قابل حذف نیست
        paid_qs = FixAreaChargeCalc.objects.filter(
            fix_area=charge,
            unit_id__in=selected_ids,
            is_paid=True
        )
        if paid_qs.exists():
            return JsonResponse({'error': 'برخی واحدها پرداخت انجام داده‌اند؛ حذف ممکن نیست.'})

        # حذف رکوردهای انتخاب‌شده
        qs = FixAreaChargeCalc.objects.filter(
            fix_area=charge,
            unit_id__in=selected_ids,
            is_paid=False
        )
        calc_ids = list(qs.values_list('id', flat=True))
        deleted_count = qs.count()
        qs.delete()

        # حذف UnifiedCharge مربوط
        UnifiedCharge.objects.filter(
            content_type=charge_type_ct,
            object_id__in=calc_ids
        ).delete()

        # اگر همه رکوردها حذف شدند → اعلان غیرفعال شود
        if not FixAreaChargeCalc.objects.filter(fix_area=charge).exists():
            charge.send_notification = False
            charge.save()

        return JsonResponse({'success': f'{deleted_count} اطلاعیه حذف شد.'})

    except Exception as e:
        return JsonResponse({'error': 'خطایی هنگام حذف اطلاعیه‌ها رخ داد.'}, status=500)


# ======================= Fix Person Charge  ==========================
@method_decorator(middle_admin_required, name='dispatch')
class MiddleFixPersonChargeCreateView(CreateView):
    model = FixPersonCharge
    template_name = 'middleCharge/fix_person_charge_template.html'
    form_class = FixPersonChargeForm
    success_url = reverse_lazy('middle_add_fix_person_charge')

    def form_valid(self, form):
        units = Unit.objects.filter(is_active=True, user__manager=self.request.user)

        if not units.exists():
            messages.error(self.request,
                           'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدهای ساختمان را ثبت کنید و مجددا تلاش نمایید.')
            return redirect('middle_manage_unit')
        fix_person_charge = form.save(commit=False)

        charge_name = form.cleaned_data.get('name') or 0
        fix_person_charge.name = charge_name
        fix_person_charge.user = self.request.user

        fix_person_charge.civil = fix_person_charge.civil or 0
        fix_person_charge.payment_penalty_amount = fix_person_charge.payment_penalty_amount or 0
        fix_person_charge.other_cost_amount = fix_person_charge.other_cost_amount or 0

        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        form.instance.unit_count = unit_count

        total_people_count = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('people_count'))['total'] or 0
        fix_person_charge.total_people = total_people_count

        try:
            fix_person_charge.save()
            self.object = fix_person_charge
            messages.success(self.request, 'محاسبه شارژ با موفقیت ثبت گردید')
            return super().form_valid(form)
        except:
            messages.error(self.request, 'خطا در ثبت!')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unit_count'] = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        context['total_area'] = Unit.objects.filter(is_active=True).aggregate(total=Sum('area'))['total'] or 0
        context['total_people'] = Unit.objects.filter(is_active=True, user__manager=self.request.user
                                                      ).aggregate(total=Sum('people_count'))['total'] or 0

        charges = FixPersonCharge.objects.annotate(
            notified_count=Count(
                'fix_person_charge',
                filter=Q(fix_person_charge__send_notification=True)
            ),
            total_units=Count('fix_person_charge')
        ).order_by('-created_at')
        context['charges'] = charges
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_fix_person_charge_edit(request, pk):
    charge = get_object_or_404(FixPersonCharge, pk=pk)
    any_paid = FixPersonChargeCalc.objects.filter(fix_person=charge, is_paid=True).exists()
    any_notify = FixPersonChargeCalc.objects.filter(fix_person=charge, send_notification=True).exists()
    if any_paid:
        return redirect(f"{reverse('middle_add_fix_person_charge')}?error=paid")

    if any_notify:
        return redirect(f"{reverse('middle_add_fix_person_charge')}?error=notify")

    if request.method == 'POST':
        form = FixPersonChargeForm(request.POST, request.FILES, instance=charge)
        if form.is_valid():
            charge = form.save(commit=False)
            charge.save()
            messages.success(request, 'شارژ با موفقیت ویرایش شد.')
            return redirect('middle_add_fix_person_charge')
        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
            return render(request, 'middleCharge/fix_person_charge_template.html', {'form': form, 'charge': charge})
    else:
        form = FixPersonChargeForm(instance=charge)
        return render(request, 'middleCharge/fix_person_charge_template.html', {'form': form, 'charge': charge})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_fix_person_charge_delete(request, pk):
    charge = get_object_or_404(FixPersonCharge, id=pk)

    # بررسی اینکه هیچ رکورد FixedChargeCalc با is_paid=True وجود نداشته باشد
    paid_calc_exists = charge.fix_person_charge.filter(is_paid=True).exists()
    if paid_calc_exists:
        messages.error(request, "امکان حذف شارژ وجود ندارد چون پرداخت شارژ توسط واحد ثبت شده است.")
        return redirect(reverse('middle_add_fix_person_charge'))

    # چک کردن وجود رکوردهایی که send_notification == True هستند
    notification_exists = charge.fix_person_charge.filter(send_notification=True).exists()
    if notification_exists:
        messages.error(request, "برای این شارژ اطلاعیه صادر شده است.ابتدا اطلاعیه شارژ را حذف و مجددا تلاش نمایید!")
        return redirect(reverse('middle_add_fix_person_charge'))
    try:
        charge.delete()
        messages.success(request, f'{charge.name} با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, "امکان حذف این شارژ به دلیل وابستگی وجود ندارد!")
    return redirect(reverse('middle_add_fix_person_charge'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_calculate_total_charge_fix_person(unit, charge):
    try:
        people_count = float(unit.people_count or 0)
        fix_charge_amount = float(charge.fix_charge_amount or 0)
        amount = float(charge.person_amount or 0)
        civil = float(charge.civil or 0)
        other_cost = float(charge.other_cost_amount or 0)
    except (TypeError, ValueError):
        people_count = fix_charge_amount = amount = other_cost = civil = 0.0

    final_person_amount = (amount * people_count) + fix_charge_amount
    total_charge = final_person_amount + civil + other_cost
    return total_charge


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_show_fix_person_charge_notification_form(request, pk):
    charge = get_object_or_404(FixPersonCharge, id=pk)
    units = Unit.objects.filter(is_active=True, user__manager=request.user).order_by('unit')

    notified_ids = FixPersonChargeCalc.objects.filter(
        fix_person=charge,
        send_notification=True
    ).values_list('unit_id', flat=True)

    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    existing_calcs = FixPersonChargeCalc.objects.filter(fix_person=charge, unit__in=units)
    calc_map = {calc.unit_id: calc for calc in existing_calcs}

    units_with_details = []

    for unit in units:
        active_renter = unit.renters.filter(renter_is_active=True).first()
        total_charge = middle_calculate_total_charge_fix_person(unit, charge)

        calc = calc_map.get(unit.id)

        if calc:
            # آپدیت رکورد موجود
            calc.unit_count = charge.unit_count
            calc.details = charge.details
            calc.other_cost = charge.other_cost_amount
            calc.civil_charge = charge.civil
            calc.charge_name = charge.name
            calc.amount = int(charge.person_amount or 0)
            calc.total_people = int(charge.total_people)
            calc.fix_charge = int(charge.fix_charge_amount or 0)
            calc.payment_penalty = charge.payment_penalty_amount
            calc.payment_deadline_date = charge.payment_deadline
            calc.base_charge = int(total_charge)
            calc.final_person_amount = int((charge.person_amount or 0) * int(unit.people_count or 0)) + int(
                charge.fix_charge_amount or 0)

            calc.save()  # save محاسبات total_charge_month و jریمه را انجام می‌دهد
            is_paid = calc.is_paid
        else:
            # ایجاد رکورد جدید
            calc = FixPersonChargeCalc(
                user=unit.user,
                unit=unit,
                fix_person=charge,
                unit_count=charge.unit_count,
                details=charge.details,
                other_cost=charge.other_cost_amount,
                civil_charge=charge.civil,
                charge_name=charge.name,
                amount=int(charge.person_amount or 0),
                total_people=int(charge.total_people),
                fix_charge=int(charge.fix_charge_amount or 0),
                payment_penalty=charge.payment_penalty_amount,
                payment_deadline_date=charge.payment_deadline,
                base_charge=int(total_charge),
                final_person_amount=int((charge.person_amount or 0) * int(unit.people_count or 0)) + int(
                    charge.fix_charge_amount or 0),
            )
            calc.save()
            is_paid = False

        units_with_details.append((unit, active_renter, is_paid, total_charge))

    # Pagination
    try:
        per_page = int(request.GET.get('per_page', 30))
    except ValueError:
        per_page = 30

    paginator = Paginator(units_with_details, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'charge': charge,
        'pk': pk,
        'notified_ids': list(notified_ids),
    }
    return render(request, 'middleCharge/notify_person_fix_charge_template.html', context)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
@require_POST
def middle_send_notification_fix_person_charge_to_user(request, pk):
    fix_person_charge = get_object_or_404(FixPersonCharge, id=pk)
    selected_units = [int(uid) for uid in request.POST.getlist('units') if uid.isdigit()]
    charge_type = 'fix_person'
    calc_ct = ContentType.objects.get_for_model(FixPersonChargeCalc)
    default_bank = Bank.objects.filter(user=request.user, is_default=True, is_active=True).first()

    if not selected_units:
        messages.error(request, 'هیچ واحدی انتخاب نشده است.')
        return redirect('middle_show_notification_fix_person_charge_form', pk=pk)

    units_qs = Unit.objects.filter(is_active=True)
    units_to_notify = units_qs if 'all' in request.POST.getlist('units') else units_qs.filter(id__in=selected_units)

    if not units_to_notify.exists():
        messages.error(request, 'هیچ واحد معتبری برای ارسال اطلاعیه پیدا نشد.')
        return redirect('middle_show_notification_fix_person_charge_form', pk=pk)

    notified_units = []

    with transaction.atomic():
        for unit in units_to_notify:
            calc_obj, created = FixPersonChargeCalc.objects.update_or_create(
                unit=unit,
                fix_person=fix_person_charge,
                defaults={
                    'user': unit.user,
                    'amount': fix_person_charge.person_amount,
                    'civil_charge': fix_person_charge.civil,
                    'charge_name': fix_person_charge.name,
                    'details': fix_person_charge.details,
                    'payment_deadline_date': fix_person_charge.payment_deadline,
                    'send_notification': True,
                    'send_notification_date': timezone.now().date(),
                    'bank': default_bank
                }
            )

            if not created and not calc_obj.send_notification:
                calc_obj.send_notification = True
                calc_obj.send_notification_date = timezone.now().date()
                calc_obj.bank = default_bank
                calc_obj.save()

            UnifiedCharge.objects.update_or_create(
                content_type=calc_ct,
                object_id=calc_obj.id,
                defaults={
                    'user': calc_obj.user,
                    'unit': calc_obj.unit,
                    'charge_type': charge_type,
                    'amount': calc_obj.base_charge or 0,
                    'penalty_amount': calc_obj.payment_penalty_price or 0,
                    'total_charge_month': calc_obj.total_charge_month or 0,
                    'title': calc_obj.charge_name,
                    'details': calc_obj.details,
                    'civil': calc_obj.civil_charge,
                    'other_cost_amount': calc_obj.other_cost,
                    'send_notification_date': calc_obj.send_notification_date,
                    'payment_deadline_date': calc_obj.payment_deadline_date,
                    'send_notification': True,
                    'bank': default_bank
                }
            )

        notified_units.append(str(unit))

        fix_person_charge.send_notification = True
        fix_person_charge.send_sms = True
        fix_person_charge.save()

    if notified_units:
        messages.success(request, 'اطلاعیه برای واحدهای انتخابی ارسال شد!')
    else:
        messages.info(request, 'اطلاعیه‌ای ارسال نشد؛ ممکن است قبلاً برای واحد انتخابی ثبت شده باشد.')

    return redirect('middle_show_notification_fix_person_charge_form', pk=pk)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_remove_send_notification_fix_person(request, pk):
    if request.method != 'POST' or request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'error': 'درخواست نامعتبر است.'}, status=400)

    unit_ids = request.POST.getlist('units[]')
    if not unit_ids:
        return JsonResponse({'error': 'هیچ واحدی انتخاب نشده است.'})

    charge = get_object_or_404(FixPersonCharge, id=pk)
    charge_type = 'fix_person'
    charge_type_ct = ContentType.objects.get_for_model(FixPersonChargeCalc)

    try:
        # حالت حذف همه
        if 'all' in unit_ids:
            qs = FixPersonChargeCalc.objects.filter(fix_person=charge, is_paid=False)
            calc_ids = list(qs.values_list('id', flat=True))
            deleted_count = qs.count()
            qs.delete()

            # حذف UnifiedCharge مرتبط
            UnifiedCharge.objects.filter(
                content_type=charge_type_ct,
                object_id__in=calc_ids
            ).delete()

            charge.send_notification = False
            charge.save()
            return JsonResponse({'success': f'{deleted_count} اطلاعیه با موفقیت حذف شد.'})

        # حذف انتخابی
        selected_ids = [int(uid) for uid in unit_ids if uid.isdigit()]
        if not selected_ids:
            return JsonResponse({'error': 'هیچ واحد معتبری انتخاب نشده است.'})

        # اطلاعیه صادر نشده
        not_send = FixPersonChargeCalc.objects.filter(
            fix_person=charge,
            unit_id__in=selected_ids,
            send_notification=False
        )
        if not_send.exists():
            return JsonResponse({'error': 'اطلاعیه برای برخی واحدها صادر نشده است.'})

        # پرداخت شده → قابل حذف نیست
        paid_qs = FixPersonChargeCalc.objects.filter(
            fix_person=charge,
            unit_id__in=selected_ids,
            is_paid=True
        )
        if paid_qs.exists():
            return JsonResponse({'error': 'برخی واحدها پرداخت انجام داده‌اند؛ حذف ممکن نیست.'})

        # حذف رکوردهای انتخابی
        qs = FixPersonChargeCalc.objects.filter(
            fix_person=charge,
            unit_id__in=selected_ids,
            is_paid=False
        )
        calc_ids = list(qs.values_list('id', flat=True))
        deleted_count = qs.count()
        qs.delete()

        # حذف UnifiedCharge مرتبط
        UnifiedCharge.objects.filter(
            content_type=charge_type_ct,
            object_id__in=calc_ids
        ).delete()

        # اگر همه رکوردها حذف شدند → اعلان غیرفعال شود
        if not FixPersonChargeCalc.objects.filter(fix_person=charge).exists():
            charge.send_notification = False
            charge.save()

        return JsonResponse({'success': f'{deleted_count} اطلاعیه حذف شد.'})

    except Exception:
        return JsonResponse({'error': 'خطایی هنگام حذف اطلاعیه‌ها رخ داد.'}, status=500)


# ============================== Person Area Charge ============================
@method_decorator(middle_admin_required, name='dispatch')
class MiddlePersonAreaChargeCreateView(CreateView):
    model = ChargeByPersonArea
    template_name = 'middleCharge/person_area_charge_template.html'
    form_class = PersonAreaChargeForm
    success_url = reverse_lazy('middle_add_person_area_charge')

    def form_valid(self, form):
        units = Unit.objects.filter(is_active=True, user__manager=self.request.user)

        if not units.exists():
            messages.error(self.request,
                           'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدهای ساختمان را ثبت کنید و مجددا تلاش نمایید.')
            return redirect('middle_manage_unit')
        person_area_charge = form.save(commit=False)

        charge_name = form.cleaned_data.get('name') or 0
        person_area_charge.name = charge_name
        person_area_charge.user = self.request.user

        person_area_charge.civil = person_area_charge.civil or 0
        person_area_charge.payment_penalty_amount = person_area_charge.payment_penalty_amount or 0
        person_area_charge.other_cost_amount = person_area_charge.other_cost_amount or 0

        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        form.instance.unit_count = unit_count

        person_area_charge.total_area = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('area'))['total'] or 0

        person_area_charge.total_people = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('people_count'))['total'] or 0

        try:
            person_area_charge.save()
            self.object = person_area_charge
            messages.success(self.request, 'محاسبه شارژ با موفقیت ثبت گردید')
            return super().form_valid(form)
        except:
            messages.error(self.request, 'خطا در ثبت!')
            return self.form_invalid(form)

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
                'person_area_charge',
                filter=Q(person_area_charge__send_notification=True)
            ),
            total_units=Count('person_area_charge')
        ).order_by('-created_at')
        context['charges'] = charges
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_person_area_charge_edit(request, pk):
    charge = get_object_or_404(ChargeByPersonArea, pk=pk)

    any_paid = ChargeByPersonAreaCalc.objects.filter(person_area_charge=charge, is_paid=True).exists()
    any_notify = ChargeByPersonAreaCalc.objects.filter(person_area_charge=charge, send_notification=True).exists()
    if any_paid:
        return redirect(f"{reverse('middle_add_person_area_charge')}?error=paid")

    if any_notify:
        return redirect(f"{reverse('middle_add_person_area_charge')}?error=notify")

    if request.method == 'POST':
        form = PersonAreaChargeForm(request.POST, request.FILES, instance=charge)
        if form.is_valid():
            charge = form.save(commit=False)
            charge.save()
            messages.success(request, 'شارژ با موفقیت ویرایش شد.')
            return redirect('middle_add_person_area_charge')
        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
            return render(request, 'middleCharge/person_area_charge_template.html', {'form': form, 'charge': charge})
    else:
        form = PersonAreaChargeForm(instance=charge)
        return render(request, 'middleCharge/person_area_charge_template.html', {'form': form, 'charge': charge})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_person_area_charge_delete(request, pk):
    charge = get_object_or_404(ChargeByPersonArea, id=pk)

    # بررسی اینکه هیچ رکورد FixedChargeCalc با is_paid=True وجود نداشته باشد
    paid_calc_exists = charge.person_area_charge.filter(is_paid=True).exists()
    if paid_calc_exists:
        messages.error(request, "امکان حذف شارژ وجود ندارد چون پرداخت شارژ توسط واحد ثبت شده است.")
        return redirect(reverse('middle_add_person_area_charge'))

    # چک کردن وجود رکوردهایی که send_notification == True هستند
    notification_exists = charge.person_area_charge.filter(send_notification=True).exists()
    if notification_exists:
        messages.error(request, "برای این شارژ اطلاعیه صادر شده است.ابتدا اطلاعیه شارژ را حذف و مجددا تلاش نمایید!")
        return redirect(reverse('middle_add_person_area_charge'))
    try:
        charge.delete()
        messages.success(request, f'{charge.name} با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, "امکان حذف این شارژ به دلیل وابستگی وجود ندارد!")
    return redirect(reverse('middle_add_person_area_charge'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_calculate_total_charge_person_area(unit, charge):
    try:
        area = float(unit.area or 0)
        people = float(unit.people_count or 0)
        area_amount = float(charge.area_amount or 0)
        person_amount = float(charge.person_amount or 0)
        civil = float(charge.civil or 0)
        other_cost = float(charge.other_cost_amount or 0)
    except (TypeError, ValueError):
        area = people = area_amount = person_amount = other_cost = civil = 0.0

    final_person_amount = (area_amount * area) + (person_amount * people)
    total_charge = final_person_amount + civil + other_cost
    return total_charge


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_show_person_area_charge_notification_form(request, pk):
    charge = get_object_or_404(ChargeByPersonArea, id=pk)
    units = Unit.objects.filter(is_active=True, user__manager=request.user).order_by('unit')

    notified_ids = ChargeByPersonAreaCalc.objects.filter(
        person_area_charge=charge,
        send_notification=True
    ).values_list('unit_id', flat=True)

    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    # گرفتن رکوردهای موجود
    existing_calcs = ChargeByPersonAreaCalc.objects.filter(person_area_charge=charge, unit__in=units)
    calc_map = {calc.unit_id: calc for calc in existing_calcs}

    units_with_details = []

    for unit in units:
        active_renter = unit.renters.filter(renter_is_active=True).first()
        total_charge = middle_calculate_total_charge_person_area(unit, charge)
        calc = calc_map.get(unit.id)

        if calc:
            # آپدیت رکورد موجود
            calc.unit_count = charge.unit_count
            calc.details = charge.details
            calc.other_cost = charge.other_cost_amount
            calc.civil_charge = charge.civil
            calc.charge_name = charge.name
            calc.area_charge = int(charge.area_amount or 0)
            calc.person_charge = int(charge.person_amount or 0)
            calc.total_area = int(charge.total_area)
            calc.total_people = int(charge.total_people)
            calc.payment_penalty = charge.payment_penalty_amount
            calc.payment_deadline_date = charge.payment_deadline
            calc.base_charge = int(total_charge)

            calc.save()  # save محاسبات total_charge_month و سایر مقادیر را انجام می‌دهد
            is_paid = calc.is_paid
        else:
            # ایجاد رکورد جدید
            calc = ChargeByPersonAreaCalc(
                user=unit.user,
                unit=unit,
                person_area_charge=charge,
                unit_count=charge.unit_count,
                details=charge.details,
                other_cost=charge.other_cost_amount,
                civil_charge=charge.civil,
                charge_name=charge.name,
                area_charge=int(charge.area_amount or 0),
                person_charge=int(charge.person_amount or 0),
                total_area=int(charge.total_area),
                total_people=int(charge.total_people),
                payment_penalty=charge.payment_penalty_amount,
                payment_deadline_date=charge.payment_deadline,
                base_charge=int(total_charge),
            )
            calc.save()
            is_paid = False

        units_with_details.append((unit, active_renter, is_paid, total_charge))

    # Pagination
    try:
        per_page = int(request.GET.get('per_page', 30))
    except ValueError:
        per_page = 30

    paginator = Paginator(units_with_details, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'charge': charge,
        'pk': pk,
        'notified_ids': list(notified_ids),
    }
    return render(request, 'middleCharge/notify_person_area_charge_template.html', context)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_send_notification_person_area_charge_to_user(request, pk):
    person_area = get_object_or_404(ChargeByPersonArea, id=pk)
    selected_units = [int(uid) for uid in request.POST.getlist('units') if uid.isdigit()]
    charge_type = 'person_area'
    calc_ct = ContentType.objects.get_for_model(ChargeByPersonAreaCalc)
    default_bank = Bank.objects.filter(user=request.user, is_default=True, is_active=True).first()

    if not selected_units:
        messages.warning(request, 'هیچ واحدی انتخاب نشده است.')
        return redirect('middle_show_notification_person_area_charge_form', pk=pk)

    units_qs = Unit.objects.filter(is_active=True)
    units_to_notify = units_qs if 'all' in request.POST.getlist('units') else units_qs.filter(id__in=selected_units)

    if not units_to_notify.exists():
        messages.warning(request, 'هیچ واحد معتبری برای ارسال اطلاعیه پیدا نشد.')
        return redirect('middle_show_notification_person_area_charge_form', pk=pk)

    notified_units = []

    with transaction.atomic():
        for unit in units_to_notify:
            calc_obj, created = ChargeByPersonAreaCalc.objects.update_or_create(
                unit=unit,
                person_area_charge=person_area,
                defaults={
                    'user': unit.user,
                    'area_charge': person_area.area_amount,
                    'person_charge': person_area.person_amount,
                    'civil_charge': person_area.civil,
                    'charge_name': person_area.name,
                    'details': person_area.details,
                    'payment_deadline_date': person_area.payment_deadline,
                    'send_notification': True,
                    'send_notification_date': timezone.now().date(),
                    'bank': default_bank
                }
            )

            # ثبت یا به‌روزرسانی UnifiedCharge
            if not created and not calc_obj.send_notification:
                calc_obj.send_notification = True
                calc_obj.send_notification_date = timezone.now().date()
                calc_obj.bank = default_bank
                calc_obj.save()

            UnifiedCharge.objects.update_or_create(
                content_type=calc_ct,
                object_id=calc_obj.id,
                defaults={
                    'user': calc_obj.user,
                    'unit': calc_obj.unit,
                    'charge_type': charge_type,
                    'amount': calc_obj.base_charge or 0,
                    'penalty_amount': calc_obj.payment_penalty_price or 0,
                    'total_charge_month': calc_obj.total_charge_month or 0,
                    'title': calc_obj.charge_name,
                    'details': calc_obj.details,
                    'civil': calc_obj.civil_charge,
                    'other_cost_amount': calc_obj.other_cost,
                    'send_notification_date': calc_obj.send_notification_date,
                    'payment_deadline_date': calc_obj.payment_deadline_date,
                    'send_notification': True,
                    'bank': default_bank
                }
            )

            notified_units.append(str(unit))

        person_area.send_notification = True
        person_area.send_sms = True
        person_area.save()

    if notified_units:
        messages.success(request, 'اطلاعیه برای واحدهای انتخابی ارسال شد!')
    else:
        messages.info(request, 'اطلاعیه‌ای ارسال نشد؛ ممکن است قبلاً برای واحد انتخابی ثبت شده باشد.')

    return redirect('middle_show_notification_person_area_charge_form', pk=pk)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_remove_send_notification_person_area(request, pk):
    if request.method != 'POST' or request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'error': 'درخواست نامعتبر است.'}, status=400)

    unit_ids = request.POST.getlist('units[]')
    if not unit_ids:
        return JsonResponse({'error': 'هیچ واحدی انتخاب نشده است.'})

    charge = get_object_or_404(ChargeByPersonArea, id=pk)
    charge_type = 'person_area'
    charge_type_ct = ContentType.objects.get_for_model(ChargeByPersonAreaCalc)

    try:
        # ================================
        # حذف همه
        # ================================
        if 'all' in unit_ids:
            qs = ChargeByPersonAreaCalc.objects.filter(person_area_charge=charge, is_paid=False)
            calc_ids = list(qs.values_list('id', flat=True))
            deleted_count = qs.count()
            qs.delete()

            # حذف UnifiedCharge مرتبط
            UnifiedCharge.objects.filter(
                content_type=charge_type_ct,
                object_id__in=calc_ids
            ).delete()

            charge.send_notification = False
            charge.save()
            return JsonResponse({'success': f'{deleted_count} اطلاعیه با موفقیت حذف شد.'})

        # ================================
        # حذف انتخابی
        # ================================
        selected_ids = [int(uid) for uid in unit_ids if uid.isdigit()]
        if not selected_ids:
            return JsonResponse({'error': 'هیچ واحد معتبری انتخاب نشده است.'})

        # اطلاعیه صادر نشده
        not_send = ChargeByPersonAreaCalc.objects.filter(
            person_area_charge=charge,
            unit_id__in=selected_ids,
            send_notification=False
        )
        if not_send.exists():
            return JsonResponse({'error': 'اطلاعیه برای برخی واحدها صادر نشده است.'})

        # پرداخت شده → قابل حذف نیست
        paid_qs = ChargeByPersonAreaCalc.objects.filter(
            person_area_charge=charge,
            unit_id__in=selected_ids,
            is_paid=True
        )
        if paid_qs.exists():
            return JsonResponse({'error': 'برخی واحدها پرداخت انجام داده‌اند؛ حذف ممکن نیست.'})

        # حذف رکوردهای انتخابی
        qs = ChargeByPersonAreaCalc.objects.filter(
            person_area_charge=charge,
            unit_id__in=selected_ids,
            is_paid=False
        )
        calc_ids = list(qs.values_list('id', flat=True))
        deleted_count = qs.count()
        qs.delete()

        # حذف UnifiedCharge مربوط
        UnifiedCharge.objects.filter(
            content_type=charge_type_ct,
            object_id__in=calc_ids
        ).delete()

        # اگر همه رکوردها حذف شدند → اعلان غیرفعال شود
        if not ChargeByPersonAreaCalc.objects.filter(person_area_charge=charge).exists():
            charge.send_notification = False
            charge.save()

        return JsonResponse({'success': f'{deleted_count} اطلاعیه حذف شد.'})

    except Exception:
        return JsonResponse({'error': 'خطایی هنگام حذف اطلاعیه‌ها رخ داد.'}, status=500)


# ==========================Fix Person Area Charge ================================
@method_decorator(middle_admin_required, name='dispatch')
class MiddlePersonAreaFixChargeCreateView(CreateView):
    model = ChargeByFixPersonArea
    template_name = 'middleCharge/person_area_fix_charge_template.html'
    form_class = PersonAreaFixChargeForm
    success_url = reverse_lazy('middle_add_person_area_fix_charge')

    def form_valid(self, form):
        units = Unit.objects.filter(is_active=True, user__manager=self.request.user)

        if not units.exists():
            messages.error(self.request,
                           'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدهای ساختمان را ثبت کنید و مجددا تلاش نمایید.')
            return redirect('middle_manage_unit')
        fix_person_area_charge = form.save(commit=False)

        charge_name = form.cleaned_data.get('name') or 0
        fix_person_area_charge.name = charge_name
        fix_person_area_charge.user = self.request.user

        fix_person_area_charge.civil = fix_person_area_charge.civil or 0
        fix_person_area_charge.payment_penalty_amount = fix_person_area_charge.payment_penalty_amount or 0
        fix_person_area_charge.other_cost_amount = fix_person_area_charge.other_cost_amount or 0

        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        form.instance.unit_count = unit_count

        fix_person_area_charge.total_area = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('area'))['total'] or 0

        fix_person_area_charge.total_people = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('people_count'))['total'] or 0

        try:
            fix_person_area_charge.save()
            self.object = fix_person_area_charge
            messages.success(self.request, 'محاسبه شارژ با موفقیت ثبت گردید')
            return super().form_valid(form)
        except:
            messages.error(self.request, 'خطا در ثبت!')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unit_count'] = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        context['total_area'] = Unit.objects.filter(is_active=True, user__manager=self.request.user
                                                    ).aggregate(total=Sum('area'))['total'] or 0
        context['total_people'] = Unit.objects.filter(is_active=True, user__manager=self.request.user
                                                      ).aggregate(total=Sum('people_count'))['total'] or 0

        charges = ChargeByFixPersonArea.objects.annotate(
            notified_count=Count(
                'fix_person_area',
                filter=Q(fix_person_area__send_notification=True)
            ),
            total_units=Count('fix_person_area')
        ).order_by('-created_at')
        context['charges'] = charges
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_person_area_fix_charge_edit(request, pk):
    charge = get_object_or_404(ChargeByFixPersonArea, pk=pk)

    any_paid = ChargeByFixPersonAreaCalc.objects.filter(fix_person_area=charge, is_paid=True).exists()
    any_notify = ChargeByFixPersonAreaCalc.objects.filter(fix_person_area=charge, send_notification=True).exists()
    if any_paid:
        return redirect(f"{reverse('middle_add_person_area_fix_charge')}?error=paid")

    if any_notify:
        return redirect(f"{reverse('middle_add_person_area_fix_charge')}?error=notify")

    if request.method == 'POST':
        form = PersonAreaFixChargeForm(request.POST, request.FILES, instance=charge)
        if form.is_valid():
            charge = form.save(commit=False)
            charge.save()
            messages.success(request, f'  {charge.name} با موفقیت ویرایش شد.')
            return redirect('middle_add_person_area_fix_charge')
        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
            return render(request, 'middleCharge/person_area_fix_charge_template.html',
                          {'form': form, 'charge': charge})
    else:
        form = FixAreaChargeForm(instance=charge)
        return render(request, 'middleCharge/person_area_fix_charge_template.html',
                      {'form': form, 'charge': charge})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_person_area_fix_delete(request, pk):
    charge = get_object_or_404(ChargeByFixPersonArea, id=pk)

    # بررسی اینکه هیچ رکورد FixedChargeCalc با is_paid=True وجود نداشته باشد
    paid_calc_exists = charge.fix_person_area.filter(is_paid=True).exists()
    if paid_calc_exists:
        messages.error(request, "امکان حذف شارژ وجود ندارد چون پرداخت شارژ توسط واحد ثبت شده است.")
        return redirect(reverse('middle_add_person_area_fix_charge'))

    # چک کردن وجود رکوردهایی که send_notification == True هستند
    notification_exists = charge.fix_person_area.filter(send_notification=True).exists()
    if notification_exists:
        messages.error(request, "برای این شارژ اطلاعیه صادر شده است.ابتدا اطلاعیه شارژ را حذف و مجددا تلاش نمایید!")
        return redirect(reverse('middle_add_person_area_fix_charge'))
    try:
        charge.delete()
        messages.success(request, f'{charge.name} با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, "امکان حذف این شارژ به دلیل وابستگی وجود ندارد!")
    return redirect(reverse('middle_add_person_area_fix_charge'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_calculate_total_charge_fix_person_area(unit, charge):
    try:
        area = float(unit.area or 0)
        people = float(unit.people_count or 0)
        area_amount = float(charge.area_amount or 0)
        fix_charge = float(charge.fix_charge_amount or 0)
        person_amount = float(charge.person_amount or 0)
        civil = float(charge.civil or 0)
        other_cost = float(charge.other_cost_amount)
    except (TypeError, ValueError):
        area = people = area_amount = person_amount = other_cost = fix_charge = civil = 0.0

    final_person_amount = (area_amount * area) + (person_amount * people) + fix_charge
    total_charge = final_person_amount + civil + other_cost
    return total_charge


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_show_fix_person_area_charge_notification_form(request, pk):
    charge = get_object_or_404(ChargeByFixPersonArea, id=pk)
    units = Unit.objects.filter(is_active=True, user__manager=request.user).order_by('unit')

    notified_ids = ChargeByFixPersonAreaCalc.objects.filter(
        fix_person_area=charge,
        send_notification=True
    ).values_list('unit_id', flat=True)

    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    # گرفتن رکوردهای موجود
    existing_calcs = ChargeByFixPersonAreaCalc.objects.filter(fix_person_area=charge, unit__in=units)
    calc_map = {calc.unit_id: calc for calc in existing_calcs}

    units_with_details = []

    for unit in units:
        active_renter = unit.renters.filter(renter_is_active=True).first()
        total_charge = middle_calculate_total_charge_fix_person_area(unit, charge)
        calc = calc_map.get(unit.id)

        if calc:
            # آپدیت رکورد موجود
            calc.unit_count = charge.unit_count
            calc.details = charge.details
            calc.other_cost = charge.other_cost_amount
            calc.civil_charge = charge.civil
            calc.charge_name = charge.name
            calc.area_charge = int(charge.area_amount or 0)
            calc.person_charge = int(charge.person_amount or 0)
            calc.fix_charge = int(charge.fix_charge_amount or 0)
            calc.total_area = int(charge.total_area)
            calc.total_people = int(charge.total_people)
            calc.payment_penalty = charge.payment_penalty_amount
            calc.payment_deadline_date = charge.payment_deadline
            calc.base_charge = int(total_charge)

            calc.save()  # save محاسبات total_charge_month و سایر مقادیر را انجام می‌دهد
            is_paid = calc.is_paid
        else:
            # ایجاد رکورد جدید
            calc = ChargeByFixPersonAreaCalc(
                user=unit.user,
                unit=unit,
                fix_person_area=charge,
                unit_count=charge.unit_count,
                details=charge.details,
                other_cost=charge.other_cost_amount,
                civil_charge=charge.civil,
                charge_name=charge.name,
                area_charge=int(charge.area_amount or 0),
                person_charge=int(charge.person_amount or 0),
                fix_charge=int(charge.fix_charge_amount or 0),
                total_area=int(charge.total_area),
                total_people=int(charge.total_people),
                payment_penalty=charge.payment_penalty_amount,
                payment_deadline_date=charge.payment_deadline,
                base_charge=int(total_charge),
            )
            calc.save()
            is_paid = False

        units_with_details.append((unit, active_renter, is_paid, total_charge))

    # Pagination
    try:
        per_page = int(request.GET.get('per_page', 30))
    except ValueError:
        per_page = 30

    paginator = Paginator(units_with_details, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'charge': charge,
        'pk': pk,
        'notified_ids': list(notified_ids),
    }
    return render(request, 'middleCharge/notify_fix_person_area_charge_template.html', context)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
@require_POST
def middle_send_notification_fix_person_area_charge_to_user(request, pk):
    fix_person_area = get_object_or_404(ChargeByFixPersonArea, id=pk)
    selected_units = [int(uid) for uid in request.POST.getlist('units') if uid.isdigit()]
    charge_type = 'fix_person_area'
    calc_ct = ContentType.objects.get_for_model(ChargeByFixPersonAreaCalc)
    default_bank = Bank.objects.filter(user=request.user, is_default=True, is_active=True).first()

    if not selected_units:
        messages.warning(request, 'هیچ واحدی انتخاب نشده است.')
        return redirect('middle_show_notification_fix_person_area_charge_form', pk=pk)

    units_qs = Unit.objects.filter(is_active=True)
    units_to_notify = units_qs if 'all' in request.POST.getlist('units') else units_qs.filter(id__in=selected_units)

    if not units_to_notify.exists():
        messages.warning(request, 'هیچ واحد معتبری برای ارسال اطلاعیه پیدا نشد.')
        return redirect('middle_show_notification_fix_person_area_charge_form', pk=pk)

    notified_units = []

    with transaction.atomic():
        for unit in units_to_notify:
            calc_obj, created = ChargeByFixPersonAreaCalc.objects.update_or_create(
                unit=unit,
                fix_person_area=fix_person_area,
                defaults={
                    'user': unit.user,
                    'fix_charge': fix_person_area.fix_charge_amount,
                    'area_charge': fix_person_area.area_amount,
                    'person_charge': fix_person_area.person_amount,
                    'civil_charge': fix_person_area.civil,
                    'charge_name': fix_person_area.name,
                    'details': fix_person_area.details,
                    'payment_deadline_date': fix_person_area.payment_deadline,
                    'send_notification': True,
                    'send_notification_date': timezone.now().date(),
                    'bank': default_bank
                }
            )

            # ثبت یا به‌روزرسانی UnifiedCharge
            if not created and not calc_obj.send_notification:
                calc_obj.send_notification = True
                calc_obj.send_notification_date = timezone.now().date()
                calc_obj.bank = default_bank
                calc_obj.save()

            UnifiedCharge.objects.update_or_create(
                content_type=calc_ct,
                object_id=calc_obj.id,
                defaults={
                    'user': calc_obj.user,
                    'unit': calc_obj.unit,
                    'charge_type': charge_type,
                    'amount': calc_obj.base_charge or 0,
                    'penalty_amount': calc_obj.payment_penalty_price or 0,
                    'total_charge_month': calc_obj.total_charge_month or 0,
                    'title': calc_obj.charge_name,
                    'details': calc_obj.details,
                    'civil': calc_obj.civil_charge,
                    'other_cost_amount': calc_obj.other_cost,
                    'send_notification_date': calc_obj.send_notification_date,
                    'payment_deadline_date': calc_obj.payment_deadline_date,
                    'send_notification': True,
                    'bank': default_bank
                }
            )

            notified_units.append(str(unit))

        fix_person_area.send_notification = True
        fix_person_area.send_notification_date = timezone.now().date()
        fix_person_area.send_sms = True
        fix_person_area.save()

    if notified_units:
        messages.success(request, 'اطلاعیه برای واحدهای انتخابی ارسال شد!')
    else:
        messages.info(request, 'اطلاعیه‌ای ارسال نشد؛ ممکن است قبلاً برای واحد انتخابی ثبت شده باشد.')

    return redirect('middle_show_notification_fix_person_area_charge_form', pk=pk)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_remove_send_notification_fix_person_area(request, pk):
    if request.method != 'POST' or request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'error': 'درخواست نامعتبر است.'}, status=400)

    unit_ids = request.POST.getlist('units[]')
    if not unit_ids:
        return JsonResponse({'error': 'هیچ واحدی انتخاب نشده است.'})

    charge = get_object_or_404(ChargeByFixPersonArea, id=pk)
    charge_type = 'fix_person_area'
    charge_type_ct = ContentType.objects.get_for_model(ChargeByFixPersonAreaCalc)

    try:
        # ================================
        # حذف همه
        # ================================
        if 'all' in unit_ids:
            qs = ChargeByFixPersonAreaCalc.objects.filter(fix_person_area=charge, is_paid=False)
            calc_ids = list(qs.values_list('id', flat=True))
            deleted_count = qs.count()
            qs.delete()

            # حذف UnifiedCharge مرتبط
            UnifiedCharge.objects.filter(
                content_type=charge_type_ct,
                object_id__in=calc_ids
            ).delete()

            charge.send_notification = False
            charge.save()
            return JsonResponse({'success': f'{deleted_count} اطلاعیه با موفقیت حذف شد.'})

        # ================================
        # حذف انتخابی
        # ================================
        selected_ids = [int(uid) for uid in unit_ids if uid.isdigit()]
        if not selected_ids:
            return JsonResponse({'error': 'هیچ واحد معتبری انتخاب نشده است.'})

        # اطلاعیه صادر نشده
        not_send = ChargeByFixPersonAreaCalc.objects.filter(
            fix_person_area=charge,
            unit_id__in=selected_ids,
            send_notification=False
        )
        if not_send.exists():
            return JsonResponse({'error': 'اطلاعیه برای برخی واحدها صادر نشده است.'})

        # پرداخت شده → قابل حذف نیست
        paid_qs = ChargeByFixPersonAreaCalc.objects.filter(
            fix_person_area=charge,
            unit_id__in=selected_ids,
            is_paid=True
        )
        if paid_qs.exists():
            return JsonResponse({'error': 'برخی واحدها پرداخت انجام داده‌اند؛ حذف ممکن نیست.'})

        # حذف رکوردهای انتخابی
        qs = ChargeByFixPersonAreaCalc.objects.filter(
            fix_person_area=charge,
            unit_id__in=selected_ids,
            is_paid=False
        )
        calc_ids = list(qs.values_list('id', flat=True))
        deleted_count = qs.count()
        qs.delete()

        # حذف UnifiedCharge مربوط
        UnifiedCharge.objects.filter(
            content_type=charge_type_ct,
            object_id__in=calc_ids
        ).delete()

        # اگر همه رکوردها حذف شدند → اعلان غیرفعال شود
        if not ChargeByFixPersonAreaCalc.objects.filter(fix_person_area=charge).exists():
            charge.send_notification = False
            charge.save()

        return JsonResponse({'success': f'{deleted_count} اطلاعیه حذف شد.'})

    except Exception:
        return JsonResponse({'error': 'خطایی هنگام حذف اطلاعیه‌ها رخ داد.'}, status=500)


# =========================ّFix Variable Charge =================================
@method_decorator(middle_admin_required, name='dispatch')
class MiddleVariableFixChargeCreateView(CreateView):
    model = ChargeFixVariable
    template_name = 'middleCharge/variable_fix_charge_template.html'
    form_class = VariableFixChargeForm
    success_url = reverse_lazy('middle_add_variable_fix_charge')

    def form_valid(self, form):
        units = Unit.objects.filter(is_active=True, user__manager=self.request.user)

        if not units.exists():
            messages.error(self.request,
                           'هیچ واحد فعالی یافت نشد. لطفا ابتدا واحدهای ساختمان را ثبت کنید و مجددا تلاش نمایید.')
            return redirect('middle_manage_unit')
        fix_variable_charge = form.save(commit=False)
        charge_name = form.cleaned_data.get('name') or 0
        fix_variable_charge.name = charge_name
        fix_variable_charge.user = self.request.user

        fix_variable_charge.civil = fix_variable_charge.civil or 0
        fix_variable_charge.payment_penalty_amount = fix_variable_charge.payment_penalty_amount or 0
        fix_variable_charge.other_cost_amount = fix_variable_charge.other_cost_amount or 0
        fix_variable_charge.other_cost_amount = fix_variable_charge.other_cost_amount or 0
        fix_variable_charge.extra_parking_amount = fix_variable_charge.extra_parking_amount or 0

        unit_count = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        form.instance.unit_count = unit_count

        fix_variable_charge.total_area = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('area'))['total'] or 0

        fix_variable_charge.total_people = Unit.objects.filter(
            is_active=True,
            user__manager=self.request.user
        ).aggregate(total=Sum('people_count'))['total'] or 0

        try:
            fix_variable_charge.save()
            self.object = fix_variable_charge
            messages.success(self.request, 'محاسبه شارژ با موفقیت ثبت گردید')
            return super().form_valid(form)
        except:
            messages.error(self.request, 'خطا در ثبت!')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unit_count'] = Unit.objects.filter(is_active=True, user__manager=self.request.user).count()
        context['total_area'] = Unit.objects.filter(is_active=True, user__manager=self.request.user
                                                    ).aggregate(total=Sum('area'))['total'] or 0
        context['total_people'] = Unit.objects.filter(is_active=True, user__manager=self.request.user
                                                      ).aggregate(total=Sum('people_count'))['total'] or 0

        charges = ChargeFixVariable.objects.annotate(
            notified_count=Count(
                'fix_variable_charge',
                filter=Q(fix_variable_charge__send_notification=True)
            ),
            total_units=Count('fix_variable_charge')
        ).order_by('-created_at')
        context['charges'] = charges
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_variable_fix_charge_edit(request, pk):
    charge = get_object_or_404(ChargeFixVariable, pk=pk)

    any_paid = ChargeFixVariableCalc.objects.filter(fix_variable_charge=charge, is_paid=True).exists()
    any_notify = ChargeFixVariableCalc.objects.filter(fix_variable_charge=charge, send_notification=True).exists()
    if any_paid:
        return redirect(f"{reverse('middle_add_variable_fix_charge')}?error=paid")

    if any_notify:
        return redirect(f"{reverse('middle_add_variable_fix_charge')}?error=notify")

    if request.method == 'POST':
        form = VariableFixChargeForm(request.POST, request.FILES, instance=charge)
        if form.is_valid():
            charge = form.save(commit=False)
            charge.save()
            messages.success(request, f'  {charge.name} با موفقیت ویرایش شد.')
            return redirect('middle_add_variable_fix_charge')
        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
            return render(request, 'middleCharge/variable_fix_charge_template.html',
                          {'form': form, 'charge': charge})
    else:
        form = VariableFixChargeForm(instance=charge)
        return render(request, 'middleCharge/variable_fix_charge_template.html',
                      {'form': form, 'charge': charge})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_variable_fix_charge_delete(request, pk):
    charge = get_object_or_404(ChargeFixVariable, id=pk)

    # بررسی اینکه هیچ رکورد FixedChargeCalc با is_paid=True وجود نداشته باشد
    paid_calc_exists = charge.fix_variable_charge.filter(is_paid=True).exists()
    if paid_calc_exists:
        messages.error(request, "امکان حذف شارژ وجود ندارد چون پرداخت شارژ توسط واحد ثبت شده است.")
        return redirect(reverse('middle_add_variable_fix_charge'))

    # چک کردن وجود رکوردهایی که send_notification == True هستند
    notification_exists = charge.fix_variable_charge.filter(send_notification=True).exists()
    if notification_exists:
        messages.error(request, "برای این شارژ اطلاعیه صادر شده است.ابتدا اطلاعیه شارژ را حذف و مجددا تلاش نمایید!")
        return redirect(reverse('middle_add_variable_fix_charge'))
    try:
        charge.delete()
        messages.success(request, f'{charge.name} با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, "امکان حذف این شارژ به دلیل وابستگی وجود ندارد!")
    return redirect(reverse('middle_add_variable_fix_charge'))


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_calculate_total_charge_fix_variable(unit, charge):
    area = float(unit.area or 0)
    people = float(unit.people_count or 0)
    parking_counts = float(unit.parking_counts or 0)

    unit_fix_amount = float(charge.unit_fix_amount or 0)
    unit_variable_person_amount = float(charge.unit_variable_person_amount or 0)
    unit_variable_area_amount = float(charge.unit_variable_area_amount or 0)
    extra_parking_amount = float(charge.extra_parking_amount or 0)
    other_cost_amount = float(charge.other_cost_amount or 0)
    civil_charge = float(charge.civil or 0)

    # Calculate variable middleCharge
    variable_charge = (unit_variable_area_amount * area) + (unit_variable_person_amount * people)
    print(f'variable_charge: {variable_charge}')

    # Calculate extra parking middleCharge (e.g., 2 parking spots × 100,000 per spot)
    parking_charge = parking_counts * extra_parking_amount if parking_counts > 0 else 0
    print(f'parking_charge: {parking_charge}')

    total_charge = variable_charge + unit_fix_amount + other_cost_amount + parking_charge + civil_charge
    print(f'total_charge: {total_charge}')

    return total_charge


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_show_fix_variable_notification_form(request, pk):
    charge = get_object_or_404(ChargeFixVariable, id=pk)
    units = Unit.objects.filter(is_active=True, user__manager=request.user).order_by('unit')

    notified_ids = ChargeFixVariableCalc.objects.filter(
        fix_variable_charge=charge,
        send_notification=True
    ).values_list('unit_id', flat=True)

    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()

    # گرفتن رکوردهای موجود
    existing_calcs = ChargeFixVariableCalc.objects.filter(fix_variable_charge=charge, unit__in=units)
    calc_map = {calc.unit_id: calc for calc in existing_calcs}

    units_with_details = []

    for unit in units:
        active_renter = unit.renters.filter(renter_is_active=True).first()
        total_charge = middle_calculate_total_charge_fix_variable(unit, charge)
        extra_parking_charge = (unit.parking_counts or 0) * (charge.extra_parking_amount or 0)

        calc = calc_map.get(unit.id)

        if calc:
            # آپدیت رکورد موجود
            calc.unit_count = charge.unit_count
            calc.details = charge.details
            calc.civil_charge = charge.civil
            calc.charge_name = charge.name
            calc.unit_variable_person_charge = int(charge.unit_variable_person_amount or 0)
            calc.unit_variable_area_charge = int(charge.unit_variable_area_amount or 0)
            calc.unit_fix_charge_per_unit = int(charge.unit_fix_amount or 0)
            calc.total_area = int(charge.total_area)
            calc.total_people = int(charge.total_people)
            calc.payment_penalty = charge.payment_penalty_amount
            calc.payment_deadline_date = charge.payment_deadline
            calc.extra_parking_charges = extra_parking_charge
            calc.other_cost = charge.other_cost_amount
            calc.base_charge = int(total_charge)
            calc.final_person_amount = (
                    int((charge.unit_variable_person_amount or 0) * (unit.people_count or 0)) +
                    int((charge.unit_variable_area_amount or 0) * (unit.area or 0)) +
                    int(charge.unit_fix_amount or 0)
            )

            calc.save()  # save محاسبات را انجام می‌دهد
            is_paid = calc.is_paid
        else:
            # ایجاد رکورد جدید
            calc = ChargeFixVariableCalc(
                user=unit.user,
                unit=unit,
                fix_variable_charge=charge,
                unit_count=charge.unit_count,
                details=charge.details,
                civil_charge=charge.civil,
                charge_name=charge.name,
                unit_variable_person_charge=int(charge.unit_variable_person_amount or 0),
                unit_variable_area_charge=int(charge.unit_variable_area_amount or 0),
                unit_fix_charge_per_unit=int(charge.unit_fix_amount or 0),
                total_area=int(charge.total_area),
                total_people=int(charge.total_people),
                payment_penalty=charge.payment_penalty_amount,
                payment_deadline_date=charge.payment_deadline,
                extra_parking_charges=extra_parking_charge,
                other_cost=charge.other_cost_amount,
                base_charge=int(total_charge),
                final_person_amount=(
                        int((charge.unit_variable_person_amount or 0) * (unit.people_count or 0)) +
                        int((charge.unit_variable_area_amount or 0) * (unit.area or 0)) +
                        int(charge.unit_fix_amount or 0)
                )
            )
            calc.save()
            is_paid = False

        units_with_details.append((unit, active_renter, is_paid, total_charge))

    # Pagination
    try:
        per_page = int(request.GET.get('per_page', 30))
    except ValueError:
        per_page = 30

    paginator = Paginator(units_with_details, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'charge': charge,
        'pk': pk,
        'notified_ids': list(notified_ids),
    }
    return render(request, 'middleCharge/notify_fix_variable_charge_template.html', context)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
@require_POST
def middle_send_notification_fix_variable_to_user(request, pk):
    fix_variable = get_object_or_404(ChargeFixVariable, id=pk)
    selected_units = [int(uid) for uid in request.POST.getlist('units') if uid.isdigit()]
    charge_type = 'fix_variable'
    calc_ct = ContentType.objects.get_for_model(ChargeFixVariableCalc)
    default_bank = Bank.objects.filter(user=request.user, is_default=True, is_active=True).first()

    if not selected_units:
        messages.warning(request, 'هیچ واحدی انتخاب نشده است.')
        return redirect('middle_show_notification_fix_variable_charge_form', pk=pk)

    units_qs = Unit.objects.filter(is_active=True)
    units_to_notify = units_qs if 'all' in request.POST.getlist('units') else units_qs.filter(id__in=selected_units)

    if not units_to_notify.exists():
        messages.warning(request, 'هیچ واحد معتبری برای ارسال اطلاعیه پیدا نشد.')
        return redirect('middle_show_notification_fix_variable_charge_form', pk=pk)

    notified_units = []

    with transaction.atomic():
        for unit in units_to_notify:
            calc_obj, created = ChargeFixVariableCalc.objects.update_or_create(
                unit=unit,
                fix_variable_charge=fix_variable,
                defaults={
                    'user': unit.user,
                    'unit_variable_area_charge': fix_variable.unit_variable_area_amount,
                    'unit_variable_person_charge': fix_variable.unit_variable_person_amount,
                    'unit_fix_charge_per_unit': fix_variable.unit_fix_amount,
                    'civil_charge': fix_variable.civil,
                    'charge_name': fix_variable.name,
                    'details': fix_variable.details,
                    'payment_deadline_date': fix_variable.payment_deadline,
                    'send_notification': True,
                    'send_notification_date': timezone.now().date(),
                    'bank': default_bank
                }
            )

            # ایجاد یا به‌روزرسانی UnifiedCharge
            if not created and not calc_obj.send_notification:
                calc_obj.send_notification = True
                calc_obj.send_notification_date = timezone.now().date()
                calc_obj.bank = default_bank
                calc_obj.save()

            UnifiedCharge.objects.update_or_create(
                content_type=calc_ct,
                object_id=calc_obj.id,
                defaults={
                    'user': calc_obj.user,
                    'unit': calc_obj.unit,
                    'charge_type': charge_type,
                    'amount': calc_obj.base_charge or 0,
                    'penalty_amount': calc_obj.payment_penalty_price or 0,
                    'total_charge_month': calc_obj.total_charge_month or 0,
                    'title': calc_obj.charge_name,
                    'details': calc_obj.details,
                    'civil': calc_obj.civil_charge,
                    'other_cost_amount': calc_obj.other_cost,
                    'send_notification_date': calc_obj.send_notification_date,
                    'payment_deadline_date': calc_obj.payment_deadline_date,
                    'send_notification': True,
                    'bank': default_bank
                }
            )

            notified_units.append(str(unit))

        fix_variable.send_notification = True
        fix_variable.send_notification_date = timezone.now().date()
        fix_variable.send_sms = True
        fix_variable.save()

    if notified_units:
        messages.success(request, 'اطلاعیه برای واحدهای انتخابی ارسال شد!')
    else:
        messages.info(request, 'اطلاعیه‌ای ارسال نشد؛ ممکن است قبلاً برای واحد انتخابی ثبت شده باشد.')

    return redirect('middle_show_notification_fix_variable_charge_form', pk=pk)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def middle_remove_send_notification_fix_variable(request, pk):
    if request.method != 'POST' or request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({'error': 'درخواست نامعتبر است.'}, status=400)

    unit_ids = request.POST.getlist('units[]')
    if not unit_ids:
        return JsonResponse({'error': 'هیچ واحدی انتخاب نشده است.'})

    charge = get_object_or_404(ChargeFixVariable, id=pk)
    charge_type = 'fix_variable'
    charge_type_ct = ContentType.objects.get_for_model(ChargeFixVariableCalc)

    try:
        # ================================
        # حذف همه
        # ================================
        if 'all' in unit_ids:
            qs = ChargeFixVariableCalc.objects.filter(fix_variable_charge=charge, is_paid=False)
            calc_ids = list(qs.values_list('id', flat=True))
            deleted_count = qs.count()
            qs.delete()

            # حذف UnifiedCharge مرتبط
            UnifiedCharge.objects.filter(
                content_type=charge_type_ct,
                object_id__in=calc_ids
            ).delete()

            charge.send_notification = False
            charge.save()
            return JsonResponse({'success': f'{deleted_count} اطلاعیه با موفقیت حذف شد.'})

        # ================================
        # حذف انتخابی
        # ================================
        selected_ids = [int(uid) for uid in unit_ids if uid.isdigit()]
        if not selected_ids:
            return JsonResponse({'error': 'هیچ واحد معتبری انتخاب نشده است.'})

        # اطلاعیه صادر نشده
        not_send = ChargeFixVariableCalc.objects.filter(
            fix_variable_charge=charge,
            unit_id__in=selected_ids,
            send_notification=False
        )
        if not_send.exists():
            return JsonResponse({'error': 'اطلاعیه برای برخی واحدها صادر نشده است.'})

        # پرداخت شده → قابل حذف نیست
        paid_qs = ChargeFixVariableCalc.objects.filter(
            fix_variable_charge=charge,
            unit_id__in=selected_ids,
            is_paid=True
        )
        if paid_qs.exists():
            return JsonResponse({'error': 'برخی واحدها پرداخت انجام داده‌اند؛ حذف ممکن نیست.'})

        # حذف رکوردهای انتخابی
        qs = ChargeFixVariableCalc.objects.filter(
            fix_variable_charge=charge,
            unit_id__in=selected_ids,
            is_paid=False
        )
        calc_ids = list(qs.values_list('id', flat=True))
        deleted_count = qs.count()
        qs.delete()

        # حذف UnifiedCharge مربوط
        UnifiedCharge.objects.filter(
            content_type=charge_type_ct,
            object_id__in=calc_ids
        ).delete()

        # اگر همه رکوردها حذف شدند → اعلان غیرفعال شود
        if not ChargeFixVariableCalc.objects.filter(fix_variable_charge=charge).exists():
            charge.send_notification = False
            charge.save()

        return JsonResponse({'success': f'{deleted_count} اطلاعیه حذف شد.'})

    except Exception:
        return JsonResponse({'error': 'خطایی هنگام حذف اطلاعیه‌ها رخ داد.'}, status=500)


# ==============================================================================================
# def get_user_charges(model, user):
#     return model.objects.filter(
#         user__manager=user,
#         send_notification=True
#     ).select_related('unit').order_by('-created_at')
#
#
# def fetch_middle_charges(request):
#     unit = Unit.objects.filter(user=request.user, is_active=True).first()
#
#     charges = get_user_charges(FixedChargeCalc, request.user)
#     area_charges = get_user_charges(AreaChargeCalc, request.user)
#     person_charges = get_user_charges(PersonChargeCalc, request.user)
#     fix_person_charges = get_user_charges(FixPersonChargeCalc, request.user)
#     fix_area_charges = get_user_charges(FixAreaChargeCalc, request.user)
#     person_area_charges = get_user_charges(ChargeByPersonAreaCalc, request.user)
#     fix_person_area_charges = get_user_charges(ChargeByFixPersonAreaCalc, request.user)
#     fix_variable_charges = get_user_charges(ChargeFixVariableCalc, request.user)
#
#     context = {
#         'unit': unit,
#         'charges': charges,
#         'area_charges': area_charges,
#         'person_charges': person_charges,
#         'fix_person_charges': fix_person_charges,
#         'fix_area_charges': fix_area_charges,
#         'person_area_charges': person_area_charges,
#         'fix_person_area_charges': fix_person_area_charges,
#         'fix_variable_charges': fix_variable_charges,
#     }
#
#     return render(request, 'middleCharge/manage_charges.html', context)


# --------------------------------------------------------

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
