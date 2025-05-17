import io
import os
from datetime import timezone

import sweetify
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
import arabic_reshaper
import jdatetime
import openpyxl
from bidi.algorithm import get_display
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import get_template, render_to_string
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, UpdateView, DetailView, ListView
from django_filters.views import FilterView

from openpyxl.styles import PatternFill, Font, Alignment
from pypdf import PdfMerger, PdfWriter
from weasyprint import HTML, CSS

from xhtml2pdf import pisa

from admin_panel.filters import ExpenseFilter
from admin_panel.forms import announcementForm, UnitForm, ExpenseForm, ExpenseCategoryForm, SearchExpenseForm, \
    IncomeForm, IncomeCategoryForm, MyHouseForm, BankForm, ReceiveMoneyForm, PayerMoneyForm, PropertyForm, \
    MaintenanceForm, FixChargeForm, PersonAreaChargeForm, AreaChargeForm, PersonChargeForm, FixAreaChargeForm, \
    FixPersonChargeForm, PersonAreaFixChargeForm, VariableFixChargeForm
from admin_panel.models import Announcement, Expense, ExpenseCategory, ExpenseDocument, Income, IncomeDocument, \
    IncomeCategory, ReceiveMoney, ReceiveDocument, PayMoney, PayDocument, Property, PropertyDocument, Maintenance, \
    MaintenanceDocument, FixedChargeCalc, ChargeByPersonArea, AreaChargeCalc, PersonChargeCalc, FixAreaChargeCalc, \
    FixPersonChargeCalc, ChargeByFixPersonArea, ChargeCalcFixVariable
from user_app.models import Unit, MyHouse, Bank, Renter, User


def admin_dashboard(request):
    announcements = Announcement.objects.filter(is_active=True)

    context = {
        'announcements': announcements
    }
    return render(request, 'shared/home_template.html', context)


# def admin_login_view(request):
#     if request.method == 'POST':
#         mobile = request.POST.get('mobile')
#         password = request.POST.get('password1')
#
#         user = authenticate(request, mobile=mobile, password=password)
#         if user is not None:
#             if user.is_superuser:
#                 login(request, user)
#                 sweetify.success(request, f"{user.username} عزیز، با موفقیت وارد بخش ادمین شدید!")
#                 return redirect(reverse('admin_dashboard'))
#             else:
#                 logout(request)  # Log out any non-superuser who authenticated successfully
#                 messages.error(request, 'شما مجوز دسترسی به بخش ادمین را ندارید!')
#                 return redirect(reverse('login_admin'))
#         else:
#             messages.error(request, 'نام کاربری و یا رمز عبور اشتباه است!')
#             return redirect(reverse('login_admin'))
#
#     return render(request, 'partials/login.html')


def logout_admin(request):
    logout(request)
    return redirect('index')


#
#
def site_header_component(request):
    context = {
        'user': request.user,
        # اگر اعلان داری می‌توانی اعلان‌ها را هم اضافه کنی مثلا:
        # 'notifications': Notification.objects.filter(user=request.user, is_read=False),
    }
    return render(request, 'shared/notification_template.html', context)


class AnnouncementView(CreateView):
    model = Announcement
    template_name = 'admin_panel/announcement.html'
    form_class = announcementForm
    success_url = reverse_lazy('announcement')

    def form_valid(self, form):
        self.object = form.save(commit=False)
        # announce_instance = form.instance
        messages.success(self.request, 'اطلاعیه با موفقیت ثبت گردید!')
        return super(AnnouncementView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['announcements'] = Announcement.objects.all().order_by('-created_at')
        return context


class AnnouncementUpdateView(UpdateView):
    model = Announcement
    template_name = 'admin_panel/announcement.html'
    form_class = announcementForm
    success_url = reverse_lazy('announcement')

    def form_valid(self, form):
        edit_instance = form.instance
        self.object = form.save(commit=False)
        messages.success(self.request, 'اطلاعیه با موفقیت ویرایش گردید!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['announcements'] = Announcement.objects.filter(is_active=True)
        return context


def announcement_delete(request, pk):
    announce = get_object_or_404(Announcement, id=pk)
    print(announce.id)

    try:
        announce.delete()
        messages.success(request, 'اظلاعیه با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('announcement'))


# ========================== My House Views ========================

class AddMyHouseView(LoginRequiredMixin, View):
    template_name = 'admin_panel/add_my_house.html'

    def get(self, request, *args, **kwargs):
        context = {
            'bank_form': BankForm(),
            'house_form': MyHouseForm(),
            'banks': Bank.objects.all(),
            'houses': MyHouse.objects.all()
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        bank_form = BankForm()  # پیش‌فرض خالی
        house_form = MyHouseForm()  # پیش‌فرض خالی

        if 'submit_bank' in request.POST:
            bank_form = BankForm(request.POST)
            if bank_form.is_valid():
                bank = bank_form.save(commit=False)
                bank.user = request.user
                bank.save()
                messages.success(request, 'حساب بانکی با موفقیت ثبت شد.')
                return redirect('manage_house')
            else:
                messages.error(request, 'خطا در ثبت اطلاعات بانکی.')

        elif 'submit_house' in request.POST:
            house_form = MyHouseForm(request.POST)
            if house_form.is_valid():
                house = house_form.save(commit=False)
                house.user = request.user
                bank_id = request.POST.get('account_no')
                if bank_id:
                    try:
                        bank = Bank.objects.get(id=bank_id)
                        house.account_no = bank  # اختصاص Bank object به فیلد ForeignKey
                    except Bank.DoesNotExist:
                        messages.error(request, 'حساب بانکی انتخاب‌شده یافت نشد.')
                        return render(request, self.template_name, {
                            'bank_form': bank_form,
                            'house_form': house_form,
                            'banks': Bank.objects.all(),
                            'houses': MyHouse.objects.all()
                        })
                house.save()
                messages.success(request, 'اطلاعات ساختمان با موفقیت ثبت شد.')
                return redirect('manage_house')
            else:
                messages.error(request, 'خطا در ثبت اطلاعات خانه.')
        return render(request, self.template_name, {
            'bank_form': bank_form,
            'house_form': house_form,
            'banks': Bank.objects.all(),
            'houses': MyHouse.objects.all()
        })


def edit_bank(request, pk):
    bank = get_object_or_404(Bank, pk=pk)
    if request.method == 'POST':
        form = BankForm(request.POST, instance=bank)
        if form.is_valid():
            form.save()
            messages.success(request, 'حساب بانکی با موفقیت ویرایش شد.')
            return redirect('manage_house')  # Adjust redirect as necessary
        else:
            messages.error(request, 'خطا در ویرایش فرم! لطفا دوباره تلاش کنید.')
            return redirect('manage_house')
    else:
        # If the request is not POST, redirect to the appropriate page
        return redirect('manage_house')


def edit_house(request, pk):
    house = get_object_or_404(MyHouse, pk=pk)

    if request.method == 'POST':
        house_form = MyHouseForm(request.POST, instance=house)
        if house_form.is_valid():
            house_form.save()
            messages.success(request, 'اطلاعات ساختمان با موفقیت ویرایش شد.')
            return redirect('manage_house')
        else:
            messages.error(request, 'خطا در ویرایش فرم! لطفا دوباره تلاش کنید.')
    else:
        house_form = MyHouseForm(instance=house)

    return render(request, 'admin_panel/add_my_house.html', {
        'house_form': house_form,
        'banks': Bank.objects.all(),
        'houses': MyHouse.objects.all(),
        'house': house
    })


def bank_delete(request, pk):
    bank = get_object_or_404(Bank, id=pk)
    try:
        bank.delete()
        messages.success(request, 'حساب بانکی با موفقیت حذف گردید!')
        return redirect(reverse('manage_house'))
    except Bank.DoesNotExist:
        messages.info(request, 'خطا در ثبت حساب بانکی')
        return redirect(reverse('manage_house'))


def house_delete(request, pk):
    house = get_object_or_404(MyHouse, id=pk)
    try:
        house.delete()
        messages.success(request, 'ساختمان با موفقیت حذف گردید!')
        return redirect(reverse('manage_house'))
    except Bank.DoesNotExist:
        messages.info(request, 'خطا در ثبت حساب بانکی')
        return redirect(reverse('manage_house'))


# =========================== unit Views ================================
class UnitRegisterView(LoginRequiredMixin, CreateView):
    model = Unit
    form_class = UnitForm
    success_url = reverse_lazy('manage_unit')
    template_name = 'unit_templates/unit_register.html'

    def form_valid(self, form):
        form.instance.user = self.request.user
        try:
            unit = form.save(commit=False)
            mobile = form.cleaned_data['mobile']
            password = form.cleaned_data['password']

            # ایجاد یا گرفتن کاربر
            user, created = User.objects.get_or_create(mobile=mobile)

            user.username = mobile
            user.set_password(password)
            user.otp_create_time = timezone.now()

            # 👇 تعیین نام کاربر بسته به مالک یا مستاجر بودن
            is_owner = form.cleaned_data.get('is_owner') == 'True'
            if is_owner:
                user.name = form.cleaned_data.get('renter_name')
            else:
                user.name = form.cleaned_data.get('owner_name')

            user.save()

            unit.user = user
            self.object = unit
            self.object.save()

            # اگر مستاجر وجود دارد
            if is_owner:
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
                    renter_details=form.cleaned_data.get('renter_details')
                )

            messages.success(self.request, 'واحد و کاربر با موفقیت ثبت گردید!')
            return super().form_valid(form)

        except IntegrityError:
            form.add_error(None, "خطا در ذخیره اطلاعات. لطفاً مجدد تلاش کنید.")
            return self.form_invalid(form)


class UnitUpdateView(LoginRequiredMixin, UpdateView):
    model = Unit
    form_class = UnitForm
    template_name = 'unit_templates/edit_unit.html'
    success_url = reverse_lazy('manage_unit')  # Redirect where you want after update

    def form_valid(self, form):
        form.instance.user = self.request.user

        try:
            with transaction.atomic():
                self.object = form.save()
                old_user = self.object.user

                new_mobile = form.cleaned_data.get('mobile')
                new_password = form.cleaned_data.get('password')
                is_owner = form.cleaned_data.get('is_owner') == 'True'

                if new_mobile and new_mobile != old_user.mobile:
                    existing_user = User.objects.filter(mobile=new_mobile).exclude(pk=old_user.pk).first()
                    if existing_user:
                        form.add_error('mobile', 'این شماره موبایل قبلاً ثبت شده است.')
                        return self.form_invalid(form)

                    # Create new user
                    new_user = User.objects.create(
                        mobile=new_mobile,
                        username=new_mobile,
                    )

                    new_user.name = form.cleaned_data.get('renter_name') if is_owner else form.cleaned_data.get(
                        'owner_name')

                    if new_password:
                        new_user.set_password(new_password)

                    new_user.save()

                    # Update unit to new user
                    self.object.user = new_user
                    self.object.save()

                else:
                    # No mobile change: just update existing user
                    if new_password:
                        old_user.set_password(new_password)

                    old_user.name = form.cleaned_data.get('renter_name') if is_owner else form.cleaned_data.get(
                        'owner_name')
                    old_user.save()

                if is_owner:
                    current_renter = Renter.objects.filter(unit=self.object, renter_is_active=True).first()

                    def normalize(val):
                        """Convert None to '', strip strings, cast ints to str for safe comparison."""
                        if val is None:
                            return ''
                        if isinstance(val, str):
                            return val.strip()
                        return str(val)

                    # Only check if current_renter exists
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

                messages.success(self.request, 'واحد با موفقیت به‌روزرسانی شد.')
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
        except Renter.DoesNotExist:
            initial['is_owner'] = 'False'
        return initial


class UnitInfoView(DetailView):
    model = Unit
    template_name = 'unit_templates/unit_info.html'
    context_object_name = 'unit'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        unit = self.object
        context['renters'] = unit.renters.order_by('-renter_is_active', '-start_date')
        return context


def unit_delete(request, pk):
    unit = get_object_or_404(Unit, id=pk)
    try:
        unit.delete()
        messages.success(request, 'واحد با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('manage_unit'))


class UnitListView(ListView):
    model = Unit
    template_name = 'unit_templates/unit_management.html'
    paginate_by = 50

    def get_queryset(self):
        # Start with all units
        queryset = Unit.objects.all().order_by('unit')

        # Retrieve filter parameters correctly
        unit = self.request.GET.get('unit')
        print(unit)
        owner_name = self.request.GET.get('owner_name')
        owner_mobile = self.request.GET.get('owner_mobile')
        area = self.request.GET.get('area')
        bedrooms_count = self.request.GET.get('bedrooms_count')
        renter_name = self.request.GET.get('renter_name')
        renter_mobile = self.request.GET.get('renter_mobile')
        people_count = self.request.GET.get('people_count')
        status_residence = self.request.GET.get('status_residence')

        if unit and unit.isdigit():
            queryset = queryset.filter(unit=int(unit))

        if owner_name:
            queryset = queryset.filter(owner_name__icontains=owner_name)

        if owner_mobile:
            queryset = queryset.filter(owner_mobile__icontains=owner_mobile)

        if area:
            queryset = queryset.filter(area__icontains=area)

        if bedrooms_count and bedrooms_count.isdigit():
            queryset = queryset.filter(bedrooms_count=int(bedrooms_count))

        if renter_name:
            queryset = queryset.filter(renters__renter_name__icontains=renter_name)

        if renter_mobile:
            queryset = queryset.filter(renters__renter_mobile__icontains=renter_mobile)

        if people_count and people_count.isdigit():
            queryset = queryset.filter(owner_people_count=people_count)

        if status_residence:
            queryset = queryset.filter(status_residence__icontains=status_residence)

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_units'] = Unit.objects.count()
        context['units'] = Unit.objects.all().order_by('unit')
        return context


def to_jalali(date_obj):
    if not date_obj:
        return ''
    jalali_date = jdatetime.date.fromgregorian(date=date_obj)
    return jalali_date.strftime('%Y/%m/%d')


def export_units_excel(request):
    units = Unit.objects.all().order_by('unit')

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


def export_units_pdf(request):
    units = Unit.objects.all().order_by('unit')

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
class ExpenseCategoryView(CreateView):
    model = ExpenseCategory
    template_name = 'expense_templates/add_category_expense.html'
    form_class = ExpenseCategoryForm
    success_url = reverse_lazy('add_category_expense')

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
        context['categories'] = ExpenseCategory.objects.all()
        return context


class ExpenseCategoryUpdate(UpdateView):
    model = ExpenseCategory
    template_name = 'expense_templates/add_category_expense.html'
    form_class = ExpenseCategoryForm
    success_url = reverse_lazy('add_category_expense')

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
        context['categories'] = ExpenseCategory.objects.all()
        return context


def expense_category_delete(request, pk):
    category = get_object_or_404(ExpenseCategory, id=pk)
    try:
        category.delete()
        messages.success(request, 'موضوع هزینه با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('add_category_expense'))


class ExpenseView(CreateView):
    model = Expense
    template_name = 'expense_templates/expense_register.html'
    form_class = ExpenseForm
    success_url = reverse_lazy('add_expense')

    def form_valid(self, form):
        form.instance.user = self.request.user
        try:
            self.object = form.save()
            files = self.request.FILES.getlist('document')

            # ذخیره فایل‌ها در مدل ExpenseDocument
            for f in files:
                ExpenseDocument.objects.create(expense=self.object, document=f)
            messages.success(self.request, 'هزینه با موفقیت ثبت گردید')
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, 'خطا در ثبت هزینه!')
            return self.form_invalid(form)

    def get_queryset(self):
        queryset = Expense.objects.all()

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        expenses = self.get_queryset()  # از get_queryset برای دریافت داده‌های فیلتر شده استفاده می‌کنیم
        paginator = Paginator(expenses, 10)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context['page_obj'] = page_obj
        context['total_expense'] = Expense.objects.count()
        context['categories'] = ExpenseCategory.objects.all()

        return context


def expense_edit(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, instance=expense)
        if form.is_valid():
            expense = form.save()  # Save the form (updates or creates expense)
            # Handle multiple file uploads
            files = request.FILES.getlist('document')
            if files:
                for f in files:
                    ExpenseDocument.objects.create(expense=expense, document=f)
            messages.success(request, 'هزینه با موفقیت ویرایش شد.')
            return redirect('add_expense')  # Adjust redirect as necessary
        else:
            messages.error(request, 'خطا در ویرایش فرم هزینه. لطفا دوباره تلاش کنید.')
            return redirect('add_expense')
    else:
        # If the request is not POST, redirect to the appropriate page
        return redirect('add_expense')


def expense_delete(request, pk):
    expense = get_object_or_404(Expense, id=pk)
    try:
        expense.delete()
        messages.success(request, ' هزینه با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('add_expense'))


@csrf_exempt
def delete_expense_document(request):
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
class IncomeCategoryView(CreateView):
    model = IncomeCategory
    template_name = 'income_templates/add_category_income.html'
    form_class = IncomeCategoryForm
    success_url = reverse_lazy('add_category_income')

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
        context['income_categories'] = IncomeCategory.objects.all()
        return context


class IncomeCategoryUpdate(UpdateView):
    model = IncomeCategory
    template_name = 'income_templates/add_category_income.html'
    form_class = IncomeCategoryForm
    success_url = reverse_lazy('add_category_income')

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
        context['income_categories'] = IncomeCategory.objects.all()
        return context


def income_category_delete(request, pk):
    income_category = get_object_or_404(IncomeCategory, id=pk)
    try:
        income_category.delete()
        messages.success(request, 'موضوع درآمد با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('add_category_income'))


class IncomeView(CreateView):
    model = Income
    template_name = 'income_templates/income_register.html'
    form_class = IncomeForm
    success_url = reverse_lazy('add_income')

    def form_valid(self, form):
        form.instance.user = self.request.user
        try:
            self.object = form.save()
            files = self.request.FILES.getlist('document')

            # ذخیره فایل‌ها در مدل ExpenseDocument
            for f in files:
                IncomeDocument.objects.create(income=self.object, document=f)
            messages.success(self.request, 'درآمد با موفقیت ثبت گردید')
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, 'خطا در ثبت درآمد!')
            return self.form_invalid(form)

    def get_queryset(self):
        queryset = Income.objects.all()

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
        paginator = Paginator(incomes, 10)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context['page_obj'] = page_obj
        context['total_incomes'] = Income.objects.count()
        context['categories'] = IncomeCategory.objects.all()

        return context


def income_edit(request, pk):
    income = get_object_or_404(Income, pk=pk)

    if request.method == 'POST':
        form = IncomeForm(request.POST, request.FILES, instance=income)

        if form.is_valid():
            income = form.save()  # Save the form (updates or creates expense)

            # Handle multiple file uploads
            files = request.FILES.getlist('document')
            if files:
                for f in files:
                    IncomeDocument.objects.create(income=income, document=f)

            messages.success(request, 'درآمد با موفقیت ویرایش شد.')
            return redirect('add_income')  # Adjust redirect as necessary

        else:
            messages.error(request, 'خطا در ویرایش فرم درآمد. لطفا دوباره تلاش کنید.')
            return redirect('add_income')
    else:
        # If the request is not POST, redirect to the appropriate page
        return redirect('add_income')


def income_delete(request, pk):
    income = get_object_or_404(Income, id=pk)
    try:
        income.delete()
        messages.success(request, ' درآمد با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('add_income'))


@csrf_exempt
def delete_income_document(request):
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


class ReceiveMoneyView(View):
    pass


# ============================ ReceiveMoneyView ==========================

class ReceiveMoneyCreateView(CreateView):
    model = ReceiveMoney
    form_class = ReceiveMoneyForm
    template_name = 'receiveMoney/add_receive_money.html'
    success_url = reverse_lazy('add_receive')

    def form_valid(self, form):
        form.instance.user = self.request.user
        try:
            self.object = form.save()
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
        queryset = ReceiveMoney.objects.all()

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        receives = self.get_queryset()
        paginator = Paginator(receives, 50)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context['page_obj'] = page_obj
        context['total_receives'] = ReceiveMoney.objects.count()
        context['receives'] = ReceiveMoney.objects.all()
        context['banks'] = MyHouse.objects.all()
        return context


def receive_edit(request, pk):
    receive = get_object_or_404(ReceiveMoney, pk=pk)

    if request.method == 'POST':
        form = ReceiveMoneyForm(request.POST, request.FILES, instance=receive)

        if form.is_valid():
            receive = form.save()  # Save the form (updates or creates expense)

            # Handle multiple file uploads
            files = request.FILES.getlist('document')
            if files:
                for f in files:
                    ReceiveDocument.objects.create(receive=receive, document=f)

            messages.success(request, 'سند با موفقیت ویرایش شد.')
            return redirect('add_receive')  # Adjust redirect as necessary

        else:
            messages.error(request, 'خطا در ویرایش فرم درآمد. لطفا دوباره تلاش کنید.')
            return redirect('add_receive')
    else:
        # If the request is not POST, redirect to the appropriate page
        return redirect('add_receive')


def receive_delete(request, pk):
    receive = get_object_or_404(ReceiveMoney, id=pk)
    try:
        receive.delete()
        messages.success(request, ' سند با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('add_receive'))


@csrf_exempt
def delete_receive_document(request):
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


def export_receive_pdf(request):
    receives = ReceiveMoney.objects.all()

    filter_fields = {
        'bank': 'bank__id',
        'payer_name': 'payer_name',
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
    template = get_template("receiveMoney/receive_pdf.html")
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

    response['Content-Disposition'] = f'attachment; filename="receives.pdf"'

    pdf_merger.write(response)
    return response


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
        if receive.bank and receive.bank.account_number:
            bank_account = str(receive.bank.account_number)

        ws.cell(row=row_num, column=2, value=bank_account)
        ws.cell(row=row_num, column=3, value=receive.payer_name)
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

class PaymentMoneyCreateView(CreateView):
    model = PayMoney
    form_class = PayerMoneyForm
    template_name = 'payMoney/add_pay_money.html'
    success_url = reverse_lazy('add_receive')

    def form_valid(self, form):
        form.instance.user = self.request.user
        try:
            self.object = form.save()
            files = self.request.FILES.getlist('document')

            # ذخیره فایل‌ها در مدل ExpenseDocument
            for f in files:
                PayDocument.objects.create(payment=self.object, document=f)
            messages.success(self.request, 'سند پرداخت با موفقیت ثبت گردید!')
            return super().form_valid(form)
        except:
            messages.error(self.request, 'خطا در ثبت!')
            return self.form_invalid(form)

    def get_queryset(self):
        queryset = PayMoney.objects.all()

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        receives = self.get_queryset()
        paginator = Paginator(receives, 50)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context['page_obj'] = page_obj
        context['total_payments'] = PayMoney.objects.count()
        context['payments'] = PayMoney.objects.all()
        context['banks'] = MyHouse.objects.all()
        return context


def pay_edit(request, pk):
    payment = get_object_or_404(PayMoney, pk=pk)

    if request.method == 'POST':
        form = PayerMoneyForm(request.POST, request.FILES, instance=payment)

        if form.is_valid():
            payment = form.save()  # Save the form (updates or creates expense)

            # Handle multiple file uploads
            files = request.FILES.getlist('document')
            if files:
                for f in files:
                    PayDocument.objects.create(payment=payment, document=f)

            messages.success(request, 'سند با موفقیت ویرایش شد.')
            return redirect('add_pay')  # Adjust redirect as necessary

        else:
            messages.error(request, 'خطا در ویرایش فرم درآمد. لطفا دوباره تلاش کنید.')
            return redirect('add_pay')
    else:
        # If the request is not POST, redirect to the appropriate page
        return redirect('add_pay')


def pay_delete(request, pk):
    payment = get_object_or_404(PayMoney, id=pk)
    try:
        payment.delete()
        messages.success(request, ' سند با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('add_pay'))


@csrf_exempt
def delete_pay_document(request):
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
    template = get_template("payMoney/pay_pdf.html")
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
        if payment.bank and payment.bank.account_number:
            bank_account = str(payment.bank.account_number)

        ws.cell(row=row_num, column=2, value=bank_account)
        ws.cell(row=row_num, column=3, value=payment.receiver_name)
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

class PropertyCreateView(CreateView):
    model = Property
    template_name = 'property/manage_property.html'
    form_class = PropertyForm
    success_url = reverse_lazy('add_property')

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
        queryset = Property.objects.all()

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
        context['total_properties'] = Property.objects.count()
        context['properties'] = Property.objects.all()
        return context


def property_edit(request, pk):
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
            return redirect('add_property')  # Adjust redirect as necessary

        else:
            messages.error(request, 'خطا در ویرایش فرم درآمد. لطفا دوباره تلاش کنید.')
            return redirect('add_property')
    else:
        # If the request is not POST, redirect to the appropriate page
        return redirect('add_property')


def property_delete(request, pk):
    property_d = get_object_or_404(Property, id=pk)
    try:
        property_d.delete()
        messages.success(request, ' اموال با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('add_property'))


@csrf_exempt
def delete_property_document(request):
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

class MaintenanceCreateView(CreateView):
    model = Maintenance
    template_name = 'maintenance/add_maintenance.html'
    form_class = MaintenanceForm
    success_url = reverse_lazy('add_maintenance')

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
        queryset = Maintenance.objects.all()

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
        context['total_maintenances'] = maintenances.count()
        context['maintenances'] = page_obj.object_list
        return context


def maintenance_edit(request, pk):
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
            return redirect('add_maintenance')  # Adjust redirect as necessary

        else:
            messages.error(request, 'خطا در ویرایش فرم درآمد. لطفا دوباره تلاش کنید.')
            return redirect('add_maintenance')
    else:
        # If the request is not POST, redirect to the appropriate page
        return redirect('add_maintenance')


def maintenance_delete(request, pk):
    maintenance = get_object_or_404(Maintenance, id=pk)
    try:
        maintenance.delete()
        messages.success(request, ' سند با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('add_maintenance'))


@csrf_exempt
def delete_maintenance_document(request):
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

def charge_view(request):
    return render(request, 'charge/add_charge.html')


class FixChargeCreateView(CreateView):
    model = FixedChargeCalc
    template_name = 'charge/fix_charge_template.html'
    form_class = FixChargeForm
    success_url = reverse_lazy('add_fixed_charge')

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.unit = Unit.objects.filter(is_active=True, user=self.request.user).first()
        amount = form.cleaned_data.get('amount') or 0
        civil_charge = form.cleaned_data.get('civil_charge') or 0
        unit_count = Unit.objects.filter(is_active=True, user=self.request.user).count()

        form.instance.unit_count = unit_count

        # Calculate and save
        form.instance.total_charge_month = str((amount + civil_charge) * unit_count)
        try:
            self.object = form.save()
            messages.success(self.request, 'محاسبه شارژ با موفقیت ثبت گردید')
            return super().form_valid(form)
        except:
            messages.error(self.request, 'خطا در ثبت!')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['charges'] = FixedChargeCalc.objects.all()
        # unit_count = Unit.objects.filter(is_active=True, user=self.request.user).count()
        # context['unit_count'] = unit_count
        total_charge_year = FixedChargeCalc.objects.aggregate(
            total_year=Sum('total_charge_month')
        )['total_year'] or 0
        context['total_charge_year'] = total_charge_year
        return context


def fix_charge_edit(request, pk):
    charge = get_object_or_404(FixedChargeCalc, pk=pk)

    if request.method == 'POST':
        form = FixChargeForm(request.POST, request.FILES, instance=charge)

        if form.is_valid():
            form.instance.user = request.user
            form.instance.unit = Unit.objects.filter(is_active=True, user=request.user).first()
            amount = form.cleaned_data.get('amount') or 0
            civil_charge = form.cleaned_data.get('civil_charge') or 0
            unit_count = Unit.objects.filter(is_active=True, user=request.user).count()

            form.instance.unit_count = unit_count

            # Calculate and save
            form.instance.total_charge_month = str((amount + civil_charge) * unit_count)
            form.save()  # Save the form (updates or creates expense)

            messages.success(request, 'شارژ با موفقیت ویرایش شد.')
            return redirect('add_fixed_charge')  # Adjust redirect as necessary

        else:
            messages.error(request, 'خطا در ویرایش فرم . لطفا دوباره تلاش کنید.')
            return redirect('add_fixed_charge')
    else:
        return redirect('add_fixed_charge')


def fix_charge_delete(request, pk):
    charge = get_object_or_404(FixedChargeCalc, id=pk)
    try:
        charge.delete()
        messages.success(request, ' شارژ با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('add_fixed_charge'))


def show_fix_charge_notification_form(request, pk):
    charge = get_object_or_404(FixedChargeCalc, id=pk)
    units = Unit.objects.filter(user=charge.user, is_active=True).order_by('unit')

    search_query = request.GET.get('search', '').strip()
    if search_query:
        units = units.filter(
            Q(unit__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(renters__renter_name__icontains=search_query)
        ).distinct()  # adjust field accordingly

    # Pair units with their active renter for template context:
    units_with_active_renter = []
    for unit in units:
        active_renter = unit.renters.filter(renter_is_active=True).first()
        units_with_active_renter.append((unit, active_renter))

    # Pagination
    per_page = request.GET.get('per_page', 20)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 20

    paginator = Paginator(units_with_active_renter, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'charge': charge,
        'page_obj': page_obj,
    }

    return render(request, 'charge/notify_fix_charge_template.html', context)


@require_POST
def notification_fix_charge_to_user(request, pk):
    charge = get_object_or_404(FixedChargeCalc, id=pk)
    selected_units = request.POST.getlist('units')

    if not selected_units:
        messages.warning(request, 'هیچ واحدی انتخاب نشده است.')
        return redirect('notification_fix_charge_form', pk=pk)

    all_units = Unit.objects.filter(is_active=True, user=charge.user)

    if 'all' in selected_units:
        units_to_notify = all_units
    else:
        units_to_notify = all_units.filter(id__in=selected_units)

    if not units_to_notify.exists():
        messages.warning(request, 'هیچ واحد معتبری برای ارسال اطلاعیه پیدا نشد.')
        return redirect('notification_fix_charge_form', pk=pk)

    with transaction.atomic():
        count = 0
        for unit in units_to_notify:
            if not FixedChargeCalc.objects.filter(user=charge.user, unit=unit, send_notification=True).exists():
                FixedChargeCalc.objects.create(
                    user=charge.user,
                    unit=unit,
                    amount=charge.amount,  # مقداردهی به فیلد اجباری
                    send_notification=True
                )
                count += 1

        charge.send_notification = True
        charge.save()

    messages.success(request, f'اطلاعیه برای {count} واحد ارسال شد.')
    return redirect('add_fixed_charge')


# ===============================================
class AreaChargeCreateView(CreateView):
    model = AreaChargeCalc
    template_name = 'charge/area_charge_template.html'
    form_class = AreaChargeForm
    success_url = reverse_lazy('add_area_charge')

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        form.instance.unit = Unit.objects.filter(is_active=True, user=user).first()

        units_qs = Unit.objects.filter(is_active=True, user=user)
        area_amount = form.cleaned_data.get('area_amount') or 0
        civil_charge = form.cleaned_data.get('civil_charge') or 0
        total_area = units_qs.aggregate(total=Sum('area'))['total'] or 0

        unit_count = units_qs.count()

        form.instance.total_area = total_area
        form.instance.unit_count = unit_count
        form.instance.final_area_amount = area_amount / total_area if total_area else 0

        try:
            self.object = form.save()
            messages.success(self.request, 'محاسبه شارژ با موفقیت ثبت گردید')
            return super().form_valid(form)
        except:
            messages.error(self.request, 'خطا در ثبت!')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['charges'] = AreaChargeCalc.objects.all()
        unit_count = Unit.objects.filter(is_active=True, user=self.request.user).count()
        context['unit_count'] = unit_count
        total_area = Unit.objects.filter(is_active=True, user=self.request.user).aggregate(total=Sum('area'))[
                         'total'] or 0
        context['total_area'] = total_area
        total_people = Unit.objects.filter(is_active=True, user=self.request.user).aggregate(
            total=Sum('people_count'))['total'] or 0
        context['total_people'] = total_people
        total_charge_year = AreaChargeCalc.objects.aggregate(
            total_year=Sum('total_charge_month')
        )['total_year'] or 0
        context['total_charge_year'] = total_charge_year
        return context


def area_charge_edit(request, pk):
    charge = get_object_or_404(AreaChargeCalc, pk=pk)

    if request.method == 'POST':
        form = AreaChargeForm(request.POST, request.FILES, instance=charge)

        if form.is_valid():
            form.instance.unit = Unit.objects.filter(user=request.user).first()
            area_amount = form.cleaned_data.get('area_amount') or 0
            civil_charge = form.cleaned_data.get('civil_charge') or 0

            total_area = Unit.objects.filter(is_active=True, user=request.user).aggregate(total=Sum('area'))[
                             'total'] or 0
            form.instance.total_area = total_area
            unit_count = Unit.objects.filter(is_active=True, user=request.user).count()
            form.instance.unit_count = unit_count

            if unit_count == 0:
                messages.error(request, 'هیچ واحدی برای کاربر ثبت نشده است.')
                return redirect('add_area_charge')

            final_area_amount = round((total_area * area_amount) / unit_count, -3)
            total_charge_month = final_area_amount + (civil_charge * unit_count)

            form.instance.final_area_amount = final_area_amount
            form.instance.total_charge_month = total_charge_month

            form.save()

            messages.success(request, 'شارژ با موفقیت ویرایش شد.')
            return redirect('add_area_charge')

        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
            return redirect('add_area_charge')

    return redirect('add_area_charge')


def area_charge_delete(request, pk):
    charge = get_object_or_404(AreaChargeCalc, id=pk)
    try:
        charge.delete()
        messages.success(request, ' شارژ با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('add_area_charge'))


# ===============================================
class PersonChargeCreateView(CreateView):
    model = PersonChargeCalc
    template_name = 'charge/person_charge_template.html'
    form_class = PersonChargeForm
    success_url = reverse_lazy('add_person_charge')

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.unit = Unit.objects.filter(is_active=True, user=self.request.user).first()
        person_amount = form.cleaned_data.get('person_amount') or 0
        civil_charge = form.cleaned_data.get('civil_charge') or 0

        total_people = Unit.objects.filter(is_active=True, user=self.request.user).aggregate(
            total=Sum('people_count')
        )['total'] or 0

        unit_count = Unit.objects.filter(is_active=True, user=self.request.user).count()

        form.instance.total_people = total_people
        form.instance.unit_count = unit_count

        final_person_amount = round((total_people * person_amount) / unit_count, -2)

        form.instance.final_person_amount = final_person_amount

        form.instance.total_charge_month = (final_person_amount + civil_charge) * unit_count

        try:
            self.object = form.save()
            messages.success(self.request, 'محاسبه شارژ با موفقیت ثبت گردید')
            return super().form_valid(form)
        except:
            messages.error(self.request, 'خطا در ثبت!')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['charges'] = PersonChargeCalc.objects.all()
        context['total_people'] = \
            Unit.objects.filter(is_active=True, user=self.request.user).aggregate(total=Sum('people_count'))[
                'total'] or 0
        total_charge_year = PersonChargeCalc.objects.aggregate(
            total_year=Sum('total_charge_month')
        )['total_year'] or 0
        context['total_charge_year'] = total_charge_year
        return context


def person_charge_edit(request, pk):
    charge = get_object_or_404(PersonChargeCalc, pk=pk)

    if request.method == 'POST':
        form = PersonChargeForm(request.POST, request.FILES, instance=charge)

        if form.is_valid():
            form.instance.unit = Unit.objects.filter(user=request.user).first()
            person_amount = form.cleaned_data.get('person_amount') or 0
            civil_charge = form.cleaned_data.get('civil_charge') or 0

            total_people = Unit.objects.filter(is_active=True, user=request.user).aggregate(
                total=Sum('people_count')
            )['total'] or 0

            unit_count = Unit.objects.filter(is_active=True, user=request.user).count()

            form.instance.total_people = total_people
            form.instance.unit_count = unit_count

            if unit_count == 0:
                messages.error(request, 'هیچ واحدی برای کاربر ثبت نشده است.')
                return redirect('add_person_charge')

            final_person_amount = round((total_people * person_amount) / unit_count, -2)
            total_charge_month = final_person_amount + (civil_charge * unit_count)

            form.instance.final_person_amount = final_person_amount
            form.instance.total_charge_month = total_charge_month

            form.save()

            messages.success(request, 'شارژ با موفقیت ویرایش شد.')
            return redirect('add_person_charge')

        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
            return redirect('add_person_charge')

    return redirect('add_person_charge')


def person_charge_delete(request, pk):
    charge = get_object_or_404(PersonChargeCalc, id=pk)
    try:
        charge.delete()
        messages.success(request, ' شارژ با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('add_person_charge'))


# =================================================
class FixAreaChargeCreateView(CreateView):
    model = FixAreaChargeCalc
    template_name = 'charge/fix_area_charge_template.html'
    form_class = FixAreaChargeForm
    success_url = reverse_lazy('add_fix_area_charge')

    def form_valid(self, form):
        form.instance.user = self.request.user
        user_units = Unit.objects.filter(is_active=True, user=self.request.user)
        form.instance.unit = user_units.first()

        area_amount = form.cleaned_data.get('area_amount') or 0
        fix_charge = form.cleaned_data.get('fix_charge') or 0
        civil_charge = form.cleaned_data.get('civil_charge') or 0
        total_area = Unit.objects.filter(is_active=True, user=self.request.user).aggregate(total=Sum('area'))[
                         'total'] or 0
        form.instance.total_area = total_area
        unit_count = Unit.objects.filter(is_active=True, user=self.request.user).count()
        form.instance.unit_count = unit_count

        total_area_based_charge = total_area * area_amount
        print(total_area_based_charge)
        total_fix_charge = fix_charge + total_area_based_charge
        print(total_fix_charge)
        fix_area_total = total_fix_charge / unit_count
        print(fix_area_total)
        form.instance.final_person_amount = round(fix_area_total, -2)
        print(form.instance.final_person_amount)
        # Total monthly charge includes civil charge per unit
        form.instance.total_charge_month = (fix_area_total + civil_charge) * unit_count

        try:
            self.object = form.save()
            messages.success(self.request, 'محاسبه شارژ با موفقیت ثبت گردید')
            return super().form_valid(form)
        except:
            messages.error(self.request, 'خطا در ثبت!')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['charges'] = FixAreaChargeCalc.objects.all()
        total_area = Unit.objects.filter(is_active=True, user=self.request.user).aggregate(total=Sum('area'))[
                         'total'] or 0
        context['total_area'] = total_area

        total_charge_year = FixAreaChargeCalc.objects.aggregate(
            total_year=Sum('total_charge_month')
        )['total_year'] or 0
        context['total_charge_year'] = total_charge_year
        return context


def fix_area_charge_edit(request, pk):
    charge = get_object_or_404(FixAreaChargeCalc, pk=pk)

    if request.method == 'POST':
        form = FixAreaChargeForm(request.POST, request.FILES, instance=charge)

        if form.is_valid():
            form.instance.unit = Unit.objects.filter(user=request.user).first()
            area_amount = form.cleaned_data.get('area_amount') or 0
            fix_charge = form.cleaned_data.get('fix_charge') or 0
            civil_charge = form.cleaned_data.get('civil_charge') or 0

            total_area = Unit.objects.filter(is_active=True, user=request.user).aggregate(total=Sum('area'))[
                             'total'] or 0
            form.instance.total_area = total_area
            unit_count = Unit.objects.filter(is_active=True, user=request.user).count()
            form.instance.unit_count = unit_count

            if unit_count == 0:
                messages.error(request, 'هیچ واحدی برای کاربر ثبت نشده است.')
                return redirect('add_area_charge')

            total_area_based_charge = total_area * area_amount
            total_fix_charge = fix_charge + total_area_based_charge
            fix_area_total = total_fix_charge / unit_count
            final_person_amount = round(fix_area_total, -2)
            form.instance.final_person_amount = final_person_amount

            form.instance.total_charge_month = (final_person_amount + civil_charge) * unit_count

            form.save()

            messages.success(request, 'شارژ با موفقیت ویرایش شد.')
            return redirect('add_fix_area_charge')

        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
            return redirect('add_fix_area_charge')

    return redirect('add_fix_area_charge')


def fix_area_charge_delete(request, pk):
    charge = get_object_or_404(FixAreaChargeCalc, id=pk)
    try:
        charge.delete()
        messages.success(request, ' شارژ با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('add_fix_area_charge'))


# =================================================
class FixPersonChargeCreateView(CreateView):
    model = FixPersonChargeCalc
    template_name = 'charge/fix_person_charge_template.html'
    form_class = FixPersonChargeForm
    success_url = reverse_lazy('add_fix_person_charge')

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.unit = Unit.objects.filter(is_active=True, user=self.request.user).first()
        person_amount = form.cleaned_data.get('person_amount') or 0
        fix_charge = form.cleaned_data.get('fix_charge') or 0
        civil_charge = form.cleaned_data.get('civil_charge') or 0
        total_people = Unit.objects.filter(is_active=True, user=self.request.user).aggregate(
            total=Sum('people_count')
        )['total'] or 0

        unit_count = Unit.objects.filter(is_active=True, user=self.request.user).count()

        form.instance.total_people = total_people
        form.instance.unit_count = unit_count

        total_person_based_charge = total_people * person_amount

        total_fix_charge = fix_charge + total_person_based_charge

        fix_person_total = total_fix_charge / unit_count

        form.instance.final_person_amount = round(fix_person_total, -2)

        # Total monthly charge includes civil charge per unit
        form.instance.total_charge_month = (fix_person_total + civil_charge) * unit_count

        try:
            self.object = form.save()
            messages.success(self.request, 'محاسبه شارژ با موفقیت ثبت گردید')
            return super().form_valid(form)
        except:
            messages.error(self.request, 'خطا در ثبت!')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['charges'] = FixPersonChargeCalc.objects.all()
        total_people = Unit.objects.filter(is_active=True, user=self.request.user).aggregate(
            total=Sum('people_count')
        )['total'] or 0
        context['total_people'] = total_people
        total_charge_year = FixPersonChargeCalc.objects.aggregate(
            total_year=Sum('total_charge_month')
        )['total_year'] or 0
        context['total_charge_year'] = total_charge_year
        return context


def fix_person_charge_edit(request, pk):
    charge = get_object_or_404(FixPersonChargeCalc, pk=pk)

    if request.method == 'POST':
        form = FixPersonChargeForm(request.POST, request.FILES, instance=charge)

        if form.is_valid():
            form.instance.user = request.user
            form.instance.unit = Unit.objects.filter(is_active=True, user=request.user).first()
            person_amount = form.cleaned_data.get('person_amount') or 0
            fix_charge = form.cleaned_data.get('fix_charge') or 0
            civil_charge = form.cleaned_data.get('civil_charge') or 0
            total_people = Unit.objects.filter(is_active=True, user=request.user).aggregate(
                total=Sum('people_count')
            )['total'] or 0

            unit_count = Unit.objects.filter(is_active=True, user=request.user).count()

            form.instance.total_people = total_people
            form.instance.unit_count = unit_count

            total_person_based_charge = total_people * person_amount

            total_fix_charge = fix_charge + total_person_based_charge

            fix_person_total = total_fix_charge / unit_count

            form.instance.final_person_amount = round(fix_person_total, -2)

            # Total monthly charge includes civil charge per unit
            form.instance.total_charge_month = (fix_person_total + civil_charge) * unit_count

            form.save()

            messages.success(request, 'شارژ با موفقیت ویرایش شد.')
            return redirect('add_fix_person_charge')

        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
            return redirect('add_fix_person_charge')

    return redirect('add_fix_person_charge')


def fix_person_charge_delete(request, pk):
    charge = get_object_or_404(FixPersonChargeCalc, id=pk)
    try:
        charge.delete()
        messages.success(request, ' شارژ با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('add_fix_person_charge'))


# ==========================================================

class PersonAreaChargeCreateView(CreateView):
    model = ChargeByPersonArea
    template_name = 'charge/person_area_charge_template.html'
    form_class = PersonAreaChargeForm
    success_url = reverse_lazy('add_person_area_charge')

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.unit = Unit.objects.filter(is_active=True, user=self.request.user).first()
        person_charge = form.cleaned_data.get('person_charge') or 0
        area_charge = form.cleaned_data.get('area_charge') or 0
        civil_charge = form.cleaned_data.get('civil_charge') or 0
        total_people = Unit.objects.filter(is_active=True, user=self.request.user).aggregate(
            total=Sum('people_count')
        )['total'] or 0
        form.instance.total_people = total_people
        total_area = Unit.objects.filter(is_active=True, user=self.request.user).aggregate(total=Sum('area'))[
                         'total'] or 0
        form.instance.total_area = total_area
        unit_count = Unit.objects.filter(is_active=True, user=self.request.user).count()
        form.instance.unit_count = unit_count

        total_person_based_charge = total_people * person_charge
        print(total_person_based_charge)
        total_area_based_charge = total_area * area_charge
        print(total_area_based_charge)
        total_persian_area_charge = (total_area_based_charge + total_person_based_charge) / unit_count
        print(total_persian_area_charge)

        form.instance.final_person_amount = round(total_persian_area_charge, -2)

        # Total monthly charge includes civil charge per unit
        form.instance.total_charge_month = (total_persian_area_charge + civil_charge) * unit_count

        try:
            self.object = form.save()
            messages.success(self.request, 'محاسبه شارژ با موفقیت ثبت گردید')
            return super().form_valid(form)
        except:
            messages.error(self.request, 'خطا در ثبت!')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['charges'] = ChargeByPersonArea.objects.all()
        total_people = Unit.objects.filter(is_active=True, user=self.request.user).aggregate(
            total=Sum('people_count')
        )['total'] or 0
        context['total_people'] = total_people
        total_area = Unit.objects.filter(is_active=True, user=self.request.user).aggregate(
            total=Sum('area')
        )['total'] or 0
        context['total_area'] = total_area
        total_charge_year = ChargeByPersonArea.objects.aggregate(
            total_year=Sum('total_charge_month')
        )['total_year'] or 0
        context['total_charge_year'] = total_charge_year
        return context


def person_area_charge_edit(request, pk):
    charge = get_object_or_404(ChargeByPersonArea, pk=pk)

    if request.method == 'POST':
        form = PersonAreaChargeForm(request.POST, request.FILES, instance=charge)

        if form.is_valid():
            form.instance.user = request.user
            form.instance.unit = Unit.objects.filter(is_active=True, user=request.user).first()
            person_charge = form.cleaned_data.get('person_charge') or 0
            area_charge = form.cleaned_data.get('area_charge') or 0
            civil_charge = form.cleaned_data.get('civil_charge') or 0
            total_people = Unit.objects.filter(is_active=True, user=request.user).aggregate(
                total=Sum('people_count')
            )['total'] or 0
            form.instance.total_people = total_people
            total_area = Unit.objects.filter(is_active=True, user=request.user).aggregate(total=Sum('area'))[
                             'total'] or 0
            form.instance.total_area = total_area
            unit_count = Unit.objects.filter(is_active=True, user=request.user).count()
            form.instance.unit_count = unit_count

            total_person_based_charge = total_people * person_charge
            print(total_person_based_charge)
            total_area_based_charge = total_area * area_charge
            print(total_area_based_charge)
            total_persian_area_charge = (total_area_based_charge + total_person_based_charge) / unit_count
            print(total_persian_area_charge)

            form.instance.final_person_amount = round(total_persian_area_charge, -2)

            # Total monthly charge includes civil charge per unit
            form.instance.total_charge_month = (total_persian_area_charge + civil_charge) * unit_count

            form.save()

            messages.success(request, 'شارژ با موفقیت ویرایش شد.')
            return redirect('add_person_area_charge')

        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
            return redirect('add_person_area_charge')

    return redirect('add_person_area_charge')


def person_area_charge_delete(request, pk):
    charge = get_object_or_404(ChargeByPersonArea, id=pk)
    try:
        charge.delete()
        messages.success(request, ' شارژ با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('add_person_area_charge'))


# ==========================================================

class PersonAreaFixChargeCreateView(CreateView):
    model = ChargeByFixPersonArea
    template_name = 'charge/person_area_fix_charge_template.html'
    form_class = PersonAreaFixChargeForm
    success_url = reverse_lazy('add_person_area_fix_charge')

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.unit = Unit.objects.filter(is_active=True, user=self.request.user).first()
        person_charge = form.cleaned_data.get('person_charge') or 0
        area_charge = form.cleaned_data.get('area_charge') or 0
        fix_charge = form.cleaned_data.get('fix_charge') or 0
        civil_charge = form.cleaned_data.get('civil_charge') or 0
        total_people = Unit.objects.filter(is_active=True, user=self.request.user).aggregate(
            total=Sum('people_count')
        )['total'] or 0
        form.instance.total_people = total_people
        total_area = Unit.objects.filter(is_active=True, user=self.request.user).aggregate(total=Sum('area'))[
                         'total'] or 0
        form.instance.total_area = total_area
        unit_count = Unit.objects.filter(is_active=True, user=self.request.user).count()
        form.instance.unit_count = unit_count

        total_person_based_charge = total_people * person_charge
        print(total_person_based_charge)
        total_area_based_charge = total_area * area_charge
        print(total_area_based_charge)
        total_persian_area_charge = (total_area_based_charge + total_person_based_charge + fix_charge) / unit_count
        print(total_persian_area_charge)

        form.instance.final_person_amount = total_persian_area_charge

        # Total monthly charge includes civil charge per unit
        form.instance.total_charge_month = (total_persian_area_charge + civil_charge) * unit_count

        try:
            self.object = form.save()
            messages.success(self.request, 'محاسبه شارژ با موفقیت ثبت گردید')
            return super().form_valid(form)
        except:
            messages.error(self.request, 'خطا در ثبت!')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['charges'] = ChargeByFixPersonArea.objects.all()
        total_people = Unit.objects.filter(is_active=True, user=self.request.user).aggregate(
            total=Sum('people_count')
        )['total'] or 0
        context['total_people'] = total_people
        total_area = Unit.objects.filter(is_active=True, user=self.request.user).aggregate(
            total=Sum('area')
        )['total'] or 0
        context['total_area'] = total_area
        total_charge_year = ChargeByFixPersonArea.objects.aggregate(
            total_year=Sum('total_charge_month')
        )['total_year'] or 0
        context['total_charge_year'] = total_charge_year
        return context


def person_area_fix_charge_edit(request, pk):
    charge = get_object_or_404(ChargeByFixPersonArea, pk=pk)

    if request.method == 'POST':
        form = PersonAreaFixChargeForm(request.POST, request.FILES, instance=charge)

        if form.is_valid():
            form.instance.user = request.user
            form.instance.unit = Unit.objects.filter(is_active=True, user=request.user).first()
            person_charge = form.cleaned_data.get('person_charge') or 0
            area_charge = form.cleaned_data.get('area_charge') or 0
            fix_charge = form.cleaned_data.get('fix_charge') or 0
            civil_charge = form.cleaned_data.get('civil_charge') or 0
            total_people = Unit.objects.filter(is_active=True, user=request.user).aggregate(
                total=Sum('people_count')
            )['total'] or 0
            form.instance.total_people = total_people
            total_area = Unit.objects.filter(is_active=True, user=request.user).aggregate(total=Sum('area'))[
                             'total'] or 0
            form.instance.total_area = total_area
            unit_count = Unit.objects.filter(is_active=True, user=request.user).count()
            form.instance.unit_count = unit_count

            total_person_based_charge = total_people * person_charge
            print(total_person_based_charge)
            total_area_based_charge = total_area * area_charge
            print(total_area_based_charge)
            total_persian_area_charge = (total_area_based_charge + total_person_based_charge + fix_charge) / unit_count
            print(total_persian_area_charge)

            form.instance.final_person_amount = total_persian_area_charge

            # Total monthly charge includes civil charge per unit
            form.instance.total_charge_month = (total_persian_area_charge + civil_charge) * unit_count

            form.save()

            messages.success(request, 'شارژ با موفقیت ویرایش شد.')
            return redirect('add_person_area_fix_charge')

        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
            return redirect('add_person_area_fix_charge')

    return redirect('add_person_area_fix_charge')


def person_area_fix_delete(request, pk):
    charge = get_object_or_404(ChargeByFixPersonArea, id=pk)
    try:
        charge.delete()
        messages.success(request, ' شارژ با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('add_person_area_fix_charge'))


# ==========================================================

class VariableFixChargeCreateView(CreateView):
    model = ChargeCalcFixVariable
    template_name = 'charge/variable_fix_charge_template.html'
    form_class = VariableFixChargeForm
    success_url = reverse_lazy('add_variable_fix_charge')

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.unit = Unit.objects.filter(is_active=True, user=self.request.user).first()

        salary = form.cleaned_data.get('salary') or 0
        elevator_cost = form.cleaned_data.get('elevator_cost') or 0
        public_electricity = form.cleaned_data.get('public_electricity') or 0
        common_expenses = form.cleaned_data.get('common_expenses') or 0
        facility_cost = form.cleaned_data.get('facility_cost') or 0
        extinguished_cost = form.cleaned_data.get('extinguished_cost') or 0
        camera_cost = form.cleaned_data.get('camera_cost') or 0
        insurance_cost = form.cleaned_data.get('insurance_cost') or 0
        office_cost = form.cleaned_data.get('office_cost') or 0
        green_space_cost = form.cleaned_data.get('green_space_cost') or 0
        public_water = form.cleaned_data.get('public_water') or 0
        public_gas = form.cleaned_data.get('public_gas') or 0
        civil_charge = form.cleaned_data.get('civil_charge') or 0

        total_people = Unit.objects.filter(is_active=True, user=self.request.user).aggregate(
            total=Sum('people_count')
        )['total'] or 0
        form.instance.total_people = total_people
        total_area = Unit.objects.filter(is_active=True, user=self.request.user).aggregate(total=Sum('area'))[
                         'total'] or 0
        form.instance.total_area = total_area
        unit_count = Unit.objects.filter(is_active=True, user=self.request.user).count()
        form.instance.unit_count = unit_count

        # Calculate Elevator Cost
        elevator_fix_charge = elevator_cost * 0.6
        print(f'elevator_fix_charge: {elevator_fix_charge}')
        form.instance.elevator_fix_cost = elevator_fix_charge

        # Calculator Fix Cost
        total_fix_cost = (salary + elevator_fix_charge + public_electricity + common_expenses + facility_cost
                          + extinguished_cost + camera_cost + insurance_cost + office_cost + green_space_cost)
        print(total_fix_cost)
        unit_fix_amount = total_fix_cost / 187
        print(f'unit_fix_amount: {unit_fix_amount}')
        final_fix_amount = unit_fix_amount / 12
        form.instance.unit_fix_amount = final_fix_amount

        # Calculator Variable Cost
        gas_cost_amount = public_gas / total_people
        print(f'gas_cost_amount: {gas_cost_amount}')

        elevator_variable_cost = elevator_cost * 0.4
        print(f'elevator_v:{elevator_variable_cost}')

        variable_cost_per_person = (elevator_variable_cost + public_water) / 21233
        print(f'total_variable_cost: {variable_cost_per_person}')

        form.instance.unit_variable_amount_person = variable_cost_per_person
        form.instance.unit_variable_amount_area = gas_cost_amount

        try:
            self.object = form.save()
            messages.success(self.request, 'محاسبه شارژ با موفقیت ثبت گردید')
            return super().form_valid(form)
        except:
            messages.error(self.request, 'خطا در ثبت!')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['charges'] = ChargeCalcFixVariable.objects.all()
        total_people = Unit.objects.filter(is_active=True, user=self.request.user).aggregate(
            total=Sum('people_count')
        )['total'] or 0
        context['total_people'] = total_people
        total_area = Unit.objects.filter(is_active=True, user=self.request.user).aggregate(
            total=Sum('area')
        )['total'] or 0
        context['total_area'] = total_area
        total_charge_year = ChargeCalcFixVariable.objects.aggregate(
            total_year=Sum('total_charge_month')
        )['total_year'] or 0
        context['total_charge_year'] = total_charge_year
        return context


def variable_fix_charge_edit(request, pk):
    charge = get_object_or_404(ChargeCalcFixVariable, pk=pk)

    if request.method == 'POST':
        form = VariableFixChargeForm(request.POST, request.FILES, instance=charge)

        if form.is_valid():
            form.instance.user = request.user
            form.instance.unit = Unit.objects.filter(is_active=True, user=request.user).first()

            salary = form.cleaned_data.get('salary') or 0
            elevator_cost = form.cleaned_data.get('elevator_cost') or 0
            public_electricity = form.cleaned_data.get('public_electricity') or 0
            common_expenses = form.cleaned_data.get('common_expenses') or 0
            facility_cost = form.cleaned_data.get('facility_cost') or 0
            extinguished_cost = form.cleaned_data.get('extinguished_cost') or 0
            camera_cost = form.cleaned_data.get('camera_cost') or 0
            insurance_cost = form.cleaned_data.get('insurance_cost') or 0
            office_cost = form.cleaned_data.get('office_cost') or 0
            green_space_cost = form.cleaned_data.get('green_space_cost') or 0
            public_water = form.cleaned_data.get('public_water') or 0
            public_gas = form.cleaned_data.get('public_gas') or 0
            civil_charge = form.cleaned_data.get('civil_charge') or 0

            total_people = Unit.objects.filter(is_active=True, user=request.user).aggregate(
                total=Sum('people_count')
            )['total'] or 0
            form.instance.total_people = total_people
            total_area = Unit.objects.filter(is_active=True, user=request.user).aggregate(total=Sum('area'))[
                             'total'] or 0
            form.instance.total_area = total_area
            unit_count = Unit.objects.filter(is_active=True, user=request.user).count()
            form.instance.unit_count = unit_count

            # Calculate Elevator Cost
            elevator_fix_charge = elevator_cost * 0.6
            print(f'elevator_fix_charge: {elevator_fix_charge}')
            form.instance.elevator_fix_cost = elevator_fix_charge

            # Calculator Fix Cost
            total_fix_cost = (salary + elevator_fix_charge + public_electricity + common_expenses + facility_cost
                              + extinguished_cost + camera_cost + insurance_cost + office_cost + green_space_cost)
            print(total_fix_cost)
            unit_fix_amount = total_fix_cost / 187
            print(f'unit_fix_amount: {unit_fix_amount}')
            final_fix_amount = unit_fix_amount / 12
            form.instance.unit_fix_amount = final_fix_amount

            # Calculator Variable Cost
            gas_cost_amount = public_gas / total_people
            print(f'gas_cost_amount: {gas_cost_amount}')

            elevator_variable_cost = elevator_cost * 0.4
            print(f'elevator_v:{elevator_variable_cost}')

            variable_cost_per_person = (elevator_variable_cost + public_water) / 21233
            print(f'total_variable_cost: {variable_cost_per_person}')

            form.instance.unit_variable_amount_person = variable_cost_per_person
            form.instance.unit_variable_amount_area = gas_cost_amount

            form.save()

            messages.success(request, 'شارژ با موفقیت ویرایش شد.')
            return redirect('add_variable_fix_charge')

        else:
            messages.error(request, 'خطا در ویرایش فرم. لطفا دوباره تلاش کنید.')
            return redirect('add_variable_fix_charge')

    return redirect('add_variable_fix_charge')


def variable_fix_charge_delete(request, pk):
    charge = get_object_or_404(ChargeCalcFixVariable, id=pk)
    try:
        charge.delete()
        messages.success(request, ' شارژ با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('add_variable_fix_charge'))
