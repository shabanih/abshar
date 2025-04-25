import io
import os

import arabic_reshaper
import jdatetime
import openpyxl
from bidi.algorithm import get_display
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.db.models import ProtectedError, Q
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import get_template, render_to_string
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import CreateView, UpdateView, DetailView, ListView

from openpyxl.styles import PatternFill, Font
from pypdf import PdfMerger, PdfWriter
from weasyprint import HTML, CSS

from xhtml2pdf import pisa

from admin_panel.forms import announcementForm, UnitForm, ExpenseForm, ExpenseCategoryForm
from admin_panel.models import Announcement, Expense, ExpenseCategory
from user_app.models import Unit


def admin_dashboard(request):
    announcements = Announcement.objects.filter(is_active=True)

    context = {
        'announcements': announcements
    }
    return render(request, 'shared/home_template.html', context)


#
#
def site_header_component(request):
    return render(request, 'shared/notification_template.html')


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


# =========================== unit Views ================================

class UnitListView(ListView):
    model = Unit
    template_name = 'admin_panel/unit_management.html'
    context_object_name = 'units'
    paginate_by = 50
    ordering = ['unit']

    def get_queryset(self):
        # Start with the base queryset (all products)
        queryset = super().get_queryset()

        # Get the search query and selected column from GET parameters
        search_query = self.request.GET.get('search', '')
        selected_column = self.request.GET.get('column', '')

        # Apply filtering based on the selected column and search query
        if search_query and selected_column:
            # Map the selected column to the corresponding field lookup
            column_lookup = {
                'owner_name': 'owner_name__icontains',
                'renter_name': 'renter_name__icontains',  # Assuming 'category' is a foreign key
                'status_residence': 'status_residence__icontains',
                'area': 'area__icontains',
                'unit': 'unit__icontains',
                'bedrooms_count': 'bedrooms_count__icontains',
            }

            # Check if the selected column is valid and filter based on it
            if selected_column in column_lookup:
                # Filter queryset using the selected column lookup and search query
                filter_criteria = {column_lookup[selected_column]: search_query}
                queryset = queryset.filter(**filter_criteria)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_units'] = Unit.objects.count()
        context['search_query'] = self.request.GET.get('q', '')
        return context


def to_jalali(date_obj):
    if not date_obj:
        return ''
    jalali_date = jdatetime.date.fromgregorian(date=date_obj)
    return jalali_date.strftime('%Y/%m/%d')


def export_units_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Units"
    ws.sheet_view.rightToLeft = True

    # ✅ Style setup
    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")  # Gold
    header_font = Font(bold=True, color="000000")  # Black bold text

    headers = [
        'واحد', 'طبقه', 'متراژ', 'تعداد خواب', 'شماره تلفن',
        'تعداد پارکینگ', 'شماره پارکینگ', 'موقعیت پارکینک', 'وضعیت سکونت',
        'نام مالک', 'تلفن مالک', 'کد ملی مالک', 'تاریخ خرید',
        'نام مستاجر', 'تلفن مستاجر', 'کد ملی مستاجر', 'تعداد نفرات',
        'تاریخ اجاره', 'تاریخ پایان', 'شماره قرارداد', 'اجاره دهنده', 'شارژ اولیه',
    ]

    # ✅ Write header with styles
    for col_num, column_title in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=column_title)
        cell.fill = header_fill
        cell.font = header_font

    # ✅ Write data rows
    for row_num, unit in enumerate(Unit.objects.all(), start=2):
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
        ws.cell(row=row_num, column=14, value=unit.renter_name)
        ws.cell(row=row_num, column=15, value=unit.renter_mobile)
        ws.cell(row=row_num, column=16, value=unit.renter_national_code)
        ws.cell(row=row_num, column=17, value=unit.people_count)
        ws.cell(row=row_num, column=18, value=to_jalali(unit.start_date))
        ws.cell(row=row_num, column=19, value=to_jalali(unit.end_date))
        ws.cell(row=row_num, column=20, value=unit.contract_number)
        ws.cell(row=row_num, column=21, value=unit.estate_name)
        ws.cell(row=row_num, column=22, value=unit.first_charge)

    # ✅ Return file
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=units_rtl.xlsx'
    wb.save(response)
    return response


def export_units_pdf(request):
    search_query = request.GET.get('search', '')
    selected_column = request.GET.get('column', '')

    units = Unit.objects.all()

    column_lookup = {
        'owner_name': 'owner_name__icontains',
        'renter_name': 'renter_name__icontains',
        'status_residence': 'status_residence__icontains',
        'area': 'area__icontains',
        'unit': 'unit__icontains',
        'bedrooms_count': 'bedrooms_count__icontains',
    }

    if search_query and selected_column in column_lookup:
        filter_criteria = {column_lookup[selected_column]: search_query}
        units = units.filter(**filter_criteria)

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
    template = get_template("admin_panel/unit_pdf.html")
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


class UnitRegisterView(LoginRequiredMixin, CreateView):
    model = Unit
    form_class = UnitForm
    success_url = reverse_lazy('add_unit')
    template_name = 'admin_panel/unit_register.html'

    def form_valid(self, form):
        form.instance.user = self.request.user
        try:
            self.object = form.save()
            messages.success(self.request, 'واحد با موفقیت ثبت گردید!')
            return super().form_valid(form)
        except IntegrityError:
            form.add_error(None, "این اطلاعات قبلاً ثبت شده است.")
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super(UnitRegisterView, self).get_context_data(**kwargs)
        context['units'] = Unit.objects.all()
        return context


class UnitUpdateView(UpdateView):
    model = Unit
    form_class = UnitForm
    success_url = reverse_lazy('manage_unit')
    template_name = 'admin_panel/edit_unit.html'

    def form_valid(self, form):
        edit_instance = form.instance
        self.object = form.save()
        messages.success(self.request, f'واحد {edit_instance}با موفقیت ثبت گردید!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['units'] = Unit.objects.all()
        return context


class UnitInfoView(DetailView):
    model = Unit
    template_name = 'admin_panel/unit_info.html'
    context_object_name = 'unit'


def unit_delete(request, pk):
    unit = get_object_or_404(Unit, id=pk)
    try:
        unit.delete()
        messages.success(request, 'واحد با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('manage_unit'))


# ================================= Expense Views ==============================
class ExpenseCategoryView(View):
    template_name = 'admin_panel/expense_register.html'

    def get(self, request):
        categories = ExpenseCategory.objects.all()
        return render(request, self.template_name, {'categories': categories})

    def post(self, request):
        title = request.POST.get('title')
        if title:
            ExpenseCategory.objects.create(title=title)
            messages.success(request, 'موضوع هزینه با موفقیت ثبت گردید')
        else:
            messages.error(request, 'لطفاً عنوان را وارد کنید!')
        return redirect(reverse('add_category'))


class ExpenseView(CreateView):
    model = Expense
    template_name = 'admin_panel/expense_register.html'
    form_class = ExpenseForm
    success_url = reverse_lazy('add_expense')

    def form_valid(self, form):
        form.instance.user = self.request.user
        try:
            self.object = form.save()
            messages.success(self.request, 'هزینه با موفقیت ثبت گردید')
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, 'خطا در ثبت هزینه!')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['expenses'] = Expense.objects.all()
        return context
