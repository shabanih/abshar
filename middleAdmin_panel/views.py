import io
from datetime import timezone
from django.utils import timezone
import jdatetime
import openpyxl
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction, IntegrityError
from django.db.models import ProtectedError
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, UpdateView, DetailView, ListView
from openpyxl.styles import PatternFill, Alignment, Font
from pypdf import PdfWriter
from sweetify import sweetify
from weasyprint import CSS, HTML

from admin_panel.forms import announcementForm, BankForm, UnitForm
from admin_panel.models import Announcement
from user_app.models import Bank, Unit, User, Renter


def middle_admin_required(view_func):
    return user_passes_test(lambda u: u.is_middle_admin, login_url=settings.LOGIN_URL_MIDDLE_ADMIN)(view_func)


def middle_admin_login_view(request):
    if request.method == 'POST':
        mobile = request.POST.get('mobile')
        password = request.POST.get('password1')

        user = authenticate(request, mobile=mobile, password=password)
        if user is not None:
            if user.is_middle_admin:
                login(request, user)
                sweetify.success(request, f"{user.full_name} عزیز، با موفقیت وارد بخش مدیر ساختمان شدید!")
                return redirect(reverse('middle_admin_dashboard'))
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
    return redirect('login_middle_admin')


def site_header_component(request):
    context = {
        'user': request.user,
        # اگر اعلان داری می‌توانی اعلان‌ها را هم اضافه کنی مثلا:
        # 'notifications': Notification.objects.filter(user=request.user, is_read=False),
    }
    return render(request, 'middleShared/notification_template.html', context)


def middle_admin_dashboard(request):
    announcements = Announcement.objects.filter(is_active=True)
    context = {

        'announcements': announcements
    }
    return render(request, 'middleShared/home_template.html', context)


# ============================= Announcement ====================
@method_decorator(middle_admin_required, name='dispatch')
class MiddleAnnouncementView(CreateView):
    model = Announcement
    template_name = 'middle_admin/middle_announcement.html'
    form_class = announcementForm
    success_url = reverse_lazy('middle_announcement')

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        # announce_instance = form.instance
        messages.success(self.request, 'اطلاعیه با موفقیت ثبت گردید!')
        return super(MiddleAnnouncementView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['announcements'] = Announcement.objects.all().order_by('-created_at')
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
        context['announcements'] = Announcement.objects.filter(is_active=True)
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


# ========================== My House Views ========================
@method_decorator(middle_admin_required, name='dispatch')
class MiddleAddMyBankView(CreateView):
    model = Bank
    template_name = 'middle_admin/middle_add_my_house.html'
    form_class = BankForm
    success_url = reverse_lazy('middle_manage_house')

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        messages.success(self.request, 'اطلاعات ساختمان با موفقیت ثبت گردید!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['banks'] = Bank.objects.filter(is_active=True, user=self.request.user)
        return context


class MiddleMyBankUpdateView(UpdateView):
    model = Bank
    template_name = 'middle_admin/middle_add_my_house.html'
    form_class = BankForm
    success_url = reverse_lazy('middle_manage_house')

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        messages.success(self.request, 'اطلاعات ساختمان با موفقیت ویرایش گردید!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['banks'] = Bank.objects.filter(is_active=True, user=self.request.user)
        return context


@login_required()
def middle_bank_delete(request, pk):
    bank = get_object_or_404(Bank, id=pk)
    try:
        bank.delete()
        messages.success(request, 'حساب بانکی با موفقیت حذف گردید!')
        return redirect(reverse('middle_manage_house'))
    except Bank.DoesNotExist:
        messages.info(request, 'خطا در ثبت حساب بانکی')
        return redirect(reverse('middle_manage_house'))


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
                is_owner = form.cleaned_data.get('is_owner')  # Boolean

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
                user.name = form.cleaned_data.get('renter_name') if is_owner else form.cleaned_data.get('owner_name')
                user.save()

                # ساخت واحد و اتصال به کاربر جدید
                unit = form.save(commit=False)
                unit.user = user  # کاربر ایجاد شده، مالک واحد است
                unit.save()

                # اگر مستاجر وجود دارد
                if is_owner:
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
                is_owner = form.cleaned_data.get('is_owner')

                if new_mobile and new_mobile != unit_owner.mobile:
                    if User.objects.filter(mobile=new_mobile).exclude(pk=unit_owner.pk).exists():
                        form.add_error('mobile', 'این شماره موبایل قبلاً ثبت شده است.')
                        return self.form_invalid(form)

                    unit_owner.mobile = new_mobile
                    unit_owner.username = new_mobile

                unit_owner.name = form.cleaned_data.get('renter_name') if is_owner else form.cleaned_data.get(
                    'owner_name')
                if new_password:
                    unit_owner.set_password(new_password)

                unit_owner.save()
                self.object.save()  # Save the unit after confirming no issues

                # Renter logic...
                if is_owner:
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
                if is_owner and renter_fields_changed:
                    messages.info(self.request, 'اطلاعات مستأجر جدید ثبت شد.')

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
                initial['is_owner'] = 'False'
        except Renter.DoesNotExist:
            initial['is_owner'] = 'False'
        return initial


@method_decorator(middle_admin_required, name='dispatch')
class MiddleUnitInfoView(DetailView):
    model = Unit
    template_name = 'middle_unit_templates/unit_info.html'
    context_object_name = 'unit'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        unit = self.object
        context['renters'] = unit.renters.order_by('-renter_is_active', '-start_date')
        return context


def middle_unit_delete(request, pk):
    unit = get_object_or_404(Unit, id=pk)
    try:
        unit.delete()
        messages.success(request, 'واحد با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('middle_manage_unit'))


@method_decorator(middle_admin_required, name='dispatch')
class MiddleUnitListView(ListView):
    model = Unit
    template_name = 'middle_unit_templates/unit_management.html'
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
