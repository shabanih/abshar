import io
from datetime import datetime

import jdatetime
import openpyxl
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.views.generic.edit import FormMixin

from admin_panel.models import Fund, Expense, Income
from polls.templatetags.poll_extras import show_jalali
from user_app.forms import UnitReportForm
from user_app.models import Unit, MyHouse, UnitResidenceHistory
from openpyxl.styles import PatternFill, Font, Alignment
from pypdf import PdfWriter
from weasyprint import HTML, CSS


def to_jalali(date_obj):
    if not date_obj:
        return ''
    jalali_date = jdatetime.date.fromgregorian(date=date_obj)
    return jalali_date.strftime('%Y/%m/%d')


def fund_middle_turnover(request):
    manager = request.user
    query = request.GET.get('q', '').strip()
    paginate = int(request.GET.get('paginate', 20) or 20)
    paginate = paginate if paginate > 0 else 20

    funds = (
        Fund.objects
        .select_related('bank', 'content_type')
        .filter(Q(user=manager) | Q(user__manager=manager))
        .order_by('-payment_date')
    )

    if query:
        funds = funds.filter(
            Q(payment_description__icontains=query) |
            Q(payer_name__icontains=query) |
            Q(receiver_name__icontains=query) |
            Q(transaction_no__icontains=query) |
            Q(creditor_amount__icontains=query) |
            Q(debtor_amount__icontains=query) |
            Q(bank__bank_name__icontains=query)
        )

    totals = funds.aggregate(
        total_income=Sum('debtor_amount'),
        total_expense=Sum('creditor_amount'),
    )

    balance = (totals['total_income'] or 0) - (totals['total_expense'] or 0)

    paginator = Paginator(funds, paginate)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'fund_middle_turnover.html', {
        'funds': page_obj,
        'query': query,
        'paginate': paginate,
        'page_obj': page_obj,
        'totals': totals,
        'balance': balance,
    })


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def export_middle_report_pdf(request):
    manager = request.user

    # Queryset اصلی
    funds = Fund.objects.filter(Q(user=manager) | Q(user__manager=manager))
    house = None
    if request.user.is_authenticated:
        house = MyHouse.objects.filter(residents=request.user).order_by('-created_at').first()

    # فیلترها
    query = request.GET.get('q', '').strip()
    if query:
        funds = funds.filter(
            Q(payment_description__icontains=query) |
            Q(unit__unit__icontains=query) |
            Q(payer_name__icontains=query) |
            Q(receiver_name__icontains=query) |
            Q(payment_gateway__icontains=query) |
            Q(debtor_amount__icontains=query) |
            Q(creditor_amount__icontains=query)
        )
    # for field, lookup in filter_fields.items():
    #     value = request.GET.get(field)
    #     if value:
    #         funds = funds.filter(**{lookup: value})

    # محاسبه totals و balance
    totals = funds.aggregate(
        total_income=Sum('debtor_amount'),
        total_expense=Sum('creditor_amount'),
    )
    balance = (totals['total_income'] or 0) - (totals['total_expense'] or 0)

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
        table {{
            border-collapse: collapse;
            width: 100%;
        }}
        th, td {{
            border: 1px solid #000;
            padding: 5px;
            text-align: center;
        }}
        th {{
            background-color: #FFD700;
        }}
    """)

    template = get_template("middle_report_pdf.html")
    context = {
        'funds': funds,
        'query': query,
        'totals': totals,
        'balance': balance,
        'font_path': font_url,
        'today': datetime.now(),
        'house': house,
    }
    html = template.render(context)
    pdf_file = io.BytesIO()
    HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(pdf_file, stylesheets=[css])
    pdf_file.seek(0)

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="middle_report.pdf"'
    return response


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def export_middle_report_excel(request):
    manager = request.user
    report = Fund.objects.filter(Q(user=manager) | Q(user__manager=manager)).order_by('-payment_date')

    # Create Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "units"
    ws.sheet_view.rightToLeft = True

    # Title
    title_cell = ws.cell(row=1, column=1, value=f"گردش مالی صندوق ")
    title_cell.font = Font(bold=True, size=18)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=5)

    # Headers
    headers = [' بانک', 'تاریخ پرداخت', 'شرح', 'پرداخت کننده/واریز کننده', 'روش پرداخت', 'بدهکار', 'بستانکار']

    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")
    header_font = Font(bold=True, color="000000")
    for col_num, column_title in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_num, value=column_title)
        cell.fill = header_fill
        cell.font = header_font

    # Write data
    for row_num, fund in enumerate(report, start=3):
        ws.cell(row=row_num, column=1, value=f"{fund.bank.bank_name} - {fund.bank.account_no}")
        ws.cell(row=row_num, column=2, value=show_jalali(fund.payment_date))
        ws.cell(row=row_num, column=3, value=fund.payment_description)
        ws.cell(row=row_num, column=4, value=f"{fund.payer_name} - {fund.receiver_name}")
        ws.cell(row=row_num, column=5, value=fund.payment_gateway)
        ws.cell(row=row_num, column=6, value=fund.debtor_amount)
        ws.cell(row=row_num, column=7, value=fund.creditor_amount)

    # Return response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=report.xlsx'
    wb.save(response)
    return response


# ========================================================================
class UnitReportsTurnOver(FormMixin, ListView):
    model = Fund
    form_class = UnitReportForm
    template_name = 'unit_reports.html'
    context_object_name = 'transactions'
    paginate_by = 50

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        return Fund.objects.none()

    def form_valid(self, form):
        unit = form.cleaned_data['unit']

        # همیشه مالک
        # unit_user = unit.user

        transactions = Fund.objects.filter(
            unit=unit
        ).order_by('-payment_date')

        # ⚡ حتما object_list ست شود
        self.object_list = transactions

        totals = Fund.objects.filter(unit=unit).aggregate(
            total_income=Sum('debtor_amount'),
            total_expense=Sum('creditor_amount'),
        )

        balance = (totals['total_income'] or 0) - (totals['total_expense'] or 0)

        context = self.get_context_data(
            form=form,
            transactions=transactions,
            selected_unit=unit,
            balance=balance,
            totals=totals,
        )
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def export_units_report_excel(request):
    unit_id = request.GET.get('unit')
    unit = get_object_or_404(Unit, pk=unit_id)
    unit_user = unit.user

    report = Fund.objects.filter(user=unit_user).order_by('doc_number')

    # Create Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "units"
    ws.sheet_view.rightToLeft = True

    # Title
    title_cell = ws.cell(row=1, column=1, value=f"گردش مالی واحد {unit.unit}")
    title_cell.font = Font(bold=True, size=18)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=6)

    # Headers
    headers = [' بانک', 'تاریخ پرداخت', 'شرح', 'روش پرداخت', 'بدهکار', 'بستانکار']
    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")
    header_font = Font(bold=True, color="000000")
    for col_num, column_title in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_num, value=column_title)
        cell.fill = header_fill
        cell.font = header_font

    # Write data
    for row_num, fund in enumerate(report, start=3):
        ws.cell(row=row_num, column=1, value=f"{fund.bank.bank_name} - {fund.bank.account_no}")
        ws.cell(row=row_num, column=2, value=show_jalali(fund.payment_date))
        ws.cell(row=row_num, column=3, value=fund.payment_description)
        ws.cell(row=row_num, column=4, value=fund.payment_gateway)
        ws.cell(row=row_num, column=5, value=fund.debtor_amount)
        ws.cell(row=row_num, column=6, value=fund.creditor_amount)

    # Return response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=unit_{unit.unit}_report.xlsx'
    wb.save(response)
    return response


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def export_units_report_pdf(request):
    unit_id = request.GET.get('unit')
    unit = get_object_or_404(Unit, pk=unit_id)

    house = None
    if request.user.is_authenticated:
        house = MyHouse.objects.filter(residents=request.user).order_by('-created_at').first()

    # Queryset اصلی بر اساس واحد (کاربر مالک)
    funds = Fund.objects.filter(unit=unit).order_by('payment_date')

    # فیلترها از GET
    filter_fields = {
        'payment_date': 'payment_date__icontains',
        'payment_description': 'payment_description__icontains',
        'payment_gateway': 'payment_gateway__icontains',
        'debtor_amount': 'debtor_amount__icontains',
        'creditor_amount': 'creditor_amount__icontains',
    }

    for field, lookup in filter_fields.items():
        value = request.GET.get(field)
        if value:
            funds = funds.filter(**{lookup: value})

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
        table {{
            border-collapse: collapse;
            width: 100%;
        }}
        th, td {{
            border: 1px solid #000;
            padding: 5px;
            text-align: center;
        }}
        th {{
            background-color: #FFD700;
        }}
    """)

    # Render template
    template = get_template("unit_report_pdf.html")
    context = {
        'funds': funds,
        'unit': unit,
        'font_path': font_url,
        'today': datetime.now(),
        'house': house,
    }

    html = template.render(context)
    pdf_file = io.BytesIO()
    HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(pdf_file, stylesheets=[css])
    pdf_file.seek(0)

    # Response
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="unit_{unit.unit}_report.pdf"'
    return response


# ======================================================================================
def fund_turnover_user(request):
    user = request.user
    query = request.GET.get('q', '').strip()
    paginate = request.GET.get('paginate', '20')  # پیش‌فرض 20

    total_amount = Fund.objects.filter(user=user).aggregate(sum=Sum('amount'))['sum']

    if not getattr(user, 'manager', False):
        funds = Fund.objects.none()
    else:
        funds = Fund.objects.filter(user=user)

        # جستجو روی payment_description، transaction_no و doc_number
        if query:
            funds = funds.filter(
                Q(payment_description__icontains=query) |
                Q(payment_gateway__icontains=query) |
                Q(transaction_no__icontains=query) |
                Q(payment_date__icontains=query) |
                Q(amount__icontains=query)
            )

        funds = funds.order_by('-created_at')

    # پیجینیشن
    try:
        paginate = int(paginate)
    except ValueError:
        paginate = 20

    if paginate <= 0:
        paginate = 20

    paginator = Paginator(funds, paginate)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'funds': page_obj,
        'query': query,
        'paginate': paginate,
        'page_obj': page_obj,
        'total_amount': total_amount
    }
    return render(request, 'fund_turnover_user.html', context)


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def export_user_report_excel(request):
    user = request.user

    report = Fund.objects.filter(user=user).order_by('doc_number')

    # Create Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "units"
    ws.sheet_view.rightToLeft = True

    # Title
    title_cell = ws.cell(row=1, column=1, value=f"لیست تراکنش های من ")
    title_cell.font = Font(bold=True, size=18)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=5)

    # Headers
    headers = ['تاریخ پرداخت', 'شرح', 'روش پرداخت', 'شماره تراکنش', 'مبلغ']
    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")
    header_font = Font(bold=True, color="000000")
    for col_num, column_title in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_num, value=column_title)
        cell.fill = header_fill
        cell.font = header_font

    # Write data
    for row_num, fund in enumerate(report, start=3):
        ws.cell(row=row_num, column=1, value=show_jalali(fund.payment_date))
        ws.cell(row=row_num, column=2, value=fund.payment_description)
        ws.cell(row=row_num, column=3, value=fund.payment_gateway)
        ws.cell(row=row_num, column=4, value=fund.transaction_no)
        ws.cell(row=row_num, column=5, value=fund.amount)

    # Return response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=report.xlsx'
    wb.save(response)
    return response


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def export_user_report_pdf(request):
    user = request.user

    funds = Fund.objects.filter(user=user).order_by('doc_number')

    house = None
    if request.user.is_authenticated:
        house = MyHouse.objects.filter(residents=request.user).order_by('-created_at').first()

    # # Queryset اصلی بر اساس واحد (کاربر مالک)
    # funds = Fund.objects.filter(unit=unit).order_by('payment_date')

    # فیلترها از GET
    query = request.GET.get('q', '').strip()
    if query:
        funds = funds.filter(
            Q(payment_description__icontains=query) |
            Q(payment_gateway__icontains=query) |
            Q(transaction_no__icontains=query) |
            Q(payment_date__icontains=query) |
            Q(amount__icontains=query)

        )

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
        table {{
            border-collapse: collapse;
            width: 100%;
        }}
        th, td {{
            border: 1px solid #000;
            padding: 5px;
            text-align: center;
        }}
        th {{
            background-color: #FFD700;
        }}
    """)

    # Render template
    template = get_template("user_report_pdf.html")
    context = {
        'funds': funds,
        'query': query,
        'font_path': font_url,
        'today': datetime.now(),
        'house': house,
    }

    html = template.render(context)
    pdf_file = io.BytesIO()
    HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(pdf_file, stylesheets=[css])
    pdf_file.seek(0)

    # Response
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="report.pdf"'
    return response


# ===========================================================

def debtor_creditor_report(request):
    query = request.GET.get('q', '').strip()
    paginate = int(request.GET.get('paginate', 20) or 20)

    units = Unit.objects.filter(user__manager=request.user, is_active=True)

    if query:
        units = units.filter(
            Q(unit__icontains=query) |
            Q(owner_name__icontains=query)
        )

    report_data = []

    for unit in units:
        totals = Fund.objects.filter(unit=unit).aggregate(
            total_debtor=Sum('debtor_amount'),
            total_creditor=Sum('creditor_amount'),
        )

        balance = (totals['total_debtor'] or 0) - (totals['total_creditor'] or 0)

        report_data.append({
            'unit': unit,
            'total_debtor': totals['total_debtor'] or 0,
            'total_creditor': totals['total_creditor'] or 0,
            'balance': balance,
        })

    paginator = Paginator(report_data, paginate)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'debtor_creditor_report.html', {
        'page_obj': page_obj,
        'query': query,
    })


# ===========================================================

class HistoryUnitReports(FormMixin, ListView):
    model = UnitResidenceHistory
    form_class = UnitReportForm
    template_name = 'unit_history_reports.html'
    context_object_name = 'unit_histories'
    paginate_by = 40

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        queryset = UnitResidenceHistory.objects.none()
        self.selected_unit = None  # ⚡ مهم: برای context

        if self.request.method == 'POST':
            form = self.get_form()
            if form.is_valid():
                unit = form.cleaned_data['unit']
                self.selected_unit = unit  # ⚡ ذخیره برای context و export
                queryset = UnitResidenceHistory.objects.filter(
                    unit=unit
                ).order_by('-from_date')  # جدیدترین‌ها بالای جدول
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.get_form()
        context['selected_unit'] = getattr(self, 'selected_unit', None)
        return context

    def post(self, request, *args, **kwargs):
        # ⚡ مهم برای paginate کردن
        self.object_list = self.get_queryset()
        return self.render_to_response(self.get_context_data())


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def export_unit_history_report_pdf(request):
    # دریافت واحد انتخاب شده از query string
    unit_id = request.GET.get('unit')
    if not unit_id:
        return HttpResponse("واحدی انتخاب نشده است.", status=400)

    try:
        unit = Unit.objects.get(pk=unit_id)
    except Unit.DoesNotExist:
        return HttpResponse("واحد انتخاب شده وجود ندارد.", status=404)

    house = None
    if request.user.is_authenticated:
        house = MyHouse.objects.filter(residents=request.user).order_by('-created_at').first()

    # Queryset سوابق سکونت آن واحد
    unit_histories = UnitResidenceHistory.objects.filter(unit=unit).order_by('-created_at')

    # اگر سابقه‌ای نیست، پیام بده یا خالی بفرست
    if not unit_histories.exists():
        return HttpResponse("هیچ سابقه سکونتی برای این واحد وجود ندارد.", status=404)

    query = request.GET.get('q', '').strip()
    if query:
        unit_histories = unit_histories.filter(
            Q(resident_type__icontains=query) |
            Q(name__icontains=query) |
            Q(mobile__icontains=query)

        )

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
        table {{
            border-collapse: collapse;
            width: 100%;
        }}
        th, td {{
            border: 1px solid #000;
            padding: 5px;
            text-align: center;
        }}
        th {{
            background-color: #FFD700;
        }}
    """)

    # Template PDF (باید جدولی مطابق unit_histories داشته باشد)
    template = get_template("unit_history_report_pdf.html")
    context = {
        'unit': unit,
        'unit_histories': unit_histories,
        'today': datetime.now(),
        'font_path': font_url,
        'house': house
    }
    html = template.render(context)

    pdf_file = io.BytesIO()
    HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(pdf_file, stylesheets=[css])
    pdf_file.seek(0)

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="unit_{unit.unit}_history.pdf"'
    return response


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def export_unit_history_report_excel(request):
    unit_id = request.GET.get('unit')
    if not unit_id:
        return HttpResponse("واحدی انتخاب نشده است.", status=400)

    try:
        unit = Unit.objects.get(pk=unit_id)
    except Unit.DoesNotExist:
        return HttpResponse("واحد انتخاب شده وجود ندارد.", status=404)

    # Queryset سوابق سکونت آن واحد
    histories = UnitResidenceHistory.objects.filter(unit=unit).order_by('-created_at')
    if not histories.exists():
        return HttpResponse("هیچ سابقه سکونتی برای این واحد وجود ندارد.", status=404)

    # Create Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"واحد {unit.unit}"
    ws.sheet_view.rightToLeft = True

    # Title
    title_cell = ws.cell(row=1, column=1, value=f"سوابق سکونت واحد {unit.unit}")
    title_cell.font = Font(bold=True, size=18)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)

    # Headers
    headers = ['ردیف', 'نوع سکونت', 'نام', 'موبایل', 'تعداد نفرات', 'از تاریخ', 'تا تاریخ']

    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")
    header_font = Font(bold=True, color="000000")
    for col_num, column_title in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_num, value=column_title)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    # Write data
    for row_num, h in enumerate(histories, start=3):
        ws.cell(row=row_num, column=1, value=row_num - 2)  # ردیف
        ws.cell(row=row_num, column=2, value='مالک' if h.resident_type == 'owner' else 'مستاجر')
        ws.cell(row=row_num, column=3, value=h.name)
        ws.cell(row=row_num, column=4, value=h.mobile)
        ws.cell(row=row_num, column=5, value=h.people_count)
        ws.cell(row=row_num, column=6, value=show_jalali(h.from_date))
        ws.cell(row=row_num, column=7, value=show_jalali(h.to_date) if h.to_date else 'اکنون')

    # Return response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=unit_{unit.unit}_history.xlsx'
    wb.save(response)
    return response


# ====================================================================

def expense_reports(request):
    user = request.user
    query = request.GET.get('q', '').strip()
    paginate = request.GET.get('paginate', '20')  # پیش‌فرض 20

    total_amount = Expense.objects.filter(user=user).aggregate(sum=Sum('amount'))['sum']

    if not getattr(user, 'manager', False):
        expenses = Expense.objects.none()
    else:
        expenses = Expense.objects.filter(user=user)

        # جستجو روی payment_description، transaction_no و doc_number
        if query:
            expenses = expenses.filter(
                Q(category__title__icontains=query) |
                Q(bank__bank_name__icontains=query) |
                Q(amount__icontains=query) |
                Q(doc_no__icontains=query) |
                Q(description__icontains=query) |
                Q(details__icontains=query)
            )

        expenses = expenses.order_by('-created_at')

    # پیجینیشن
    try:
        paginate = int(paginate)
    except ValueError:
        paginate = 20

    if paginate <= 0:
        paginate = 20

    paginator = Paginator(expenses, paginate)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'funds': page_obj,
        'query': query,
        'paginate': paginate,
        'page_obj': page_obj,
        'total_amount': total_amount
    }
    return render(request, 'expense_reports.html', context)


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def export_expense_report_excel(request):
    user = request.user

    report = Fund.objects.filter(user=user).order_by('doc_number')

    # Create Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "units"
    ws.sheet_view.rightToLeft = True

    # Title
    title_cell = ws.cell(row=1, column=1, value=f"لیست تراکنش های من ")
    title_cell.font = Font(bold=True, size=18)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=5)

    # Headers
    headers = ['تاریخ پرداخت', 'شرح', 'روش پرداخت', 'شماره تراکنش', 'مبلغ']
    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")
    header_font = Font(bold=True, color="000000")
    for col_num, column_title in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_num, value=column_title)
        cell.fill = header_fill
        cell.font = header_font

    # Write data
    for row_num, fund in enumerate(report, start=3):
        ws.cell(row=row_num, column=1, value=show_jalali(fund.payment_date))
        ws.cell(row=row_num, column=2, value=fund.payment_description)
        ws.cell(row=row_num, column=3, value=fund.payment_gateway)
        ws.cell(row=row_num, column=4, value=fund.transaction_no)
        ws.cell(row=row_num, column=5, value=fund.amount)

    # Return response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=report.xlsx'
    wb.save(response)
    return response


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def export_expense_report_pdf(request):
    user = request.user

    funds = Fund.objects.filter(user=user).order_by('doc_number')

    house = None
    if request.user.is_authenticated:
        house = MyHouse.objects.filter(residents=request.user).order_by('-created_at').first()

    # # Queryset اصلی بر اساس واحد (کاربر مالک)
    # funds = Fund.objects.filter(unit=unit).order_by('payment_date')

    # فیلترها از GET
    query = request.GET.get('q', '').strip()
    if query:
        funds = funds.filter(
            Q(payment_description__icontains=query) |
            Q(payment_gateway__icontains=query) |
            Q(transaction_no__icontains=query) |
            Q(payment_date__icontains=query) |
            Q(amount__icontains=query)

        )

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
        table {{
            border-collapse: collapse;
            width: 100%;
        }}
        th, td {{
            border: 1px solid #000;
            padding: 5px;
            text-align: center;
        }}
        th {{
            background-color: #FFD700;
        }}
    """)

    # Render template
    template = get_template("user_report_pdf.html")
    context = {
        'funds': funds,
        'query': query,
        'font_path': font_url,
        'today': datetime.now(),
        'house': house,
    }

    html = template.render(context)
    pdf_file = io.BytesIO()
    HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(pdf_file, stylesheets=[css])
    pdf_file.seek(0)

    # Response
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="report.pdf"'
    return response


# =======================================================

def income_reports(request):
    user = request.user
    query = request.GET.get('q', '').strip()
    paginate = request.GET.get('paginate', '20')  # پیش‌فرض 20

    total_amount = Income.objects.filter(user=user).aggregate(sum=Sum('amount'))['sum']

    if not getattr(user, 'manager', False):
        incomes = Income.objects.none()
    else:
        incomes = Income.objects.filter(user=user)

        # جستجو روی payment_description، transaction_no و doc_number
        if query:
            incomes = incomes.filter(
                Q(category__title__icontains=query) |
                Q(bank__bank_name__icontains=query) |
                Q(amount__icontains=query) |
                Q(doc_no__icontains=query) |
                Q(description__icontains=query) |
                Q(details__icontains=query)
            )

        incomes = incomes.order_by('-created_at')

    # پیجینیشن
    try:
        paginate = int(paginate)
    except ValueError:
        paginate = 20

    if paginate <= 0:
        paginate = 20

    paginator = Paginator(incomes, paginate)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'funds': page_obj,
        'query': query,
        'paginate': paginate,
        'page_obj': page_obj,
        'total_amount': total_amount
    }
    return render(request, 'income_reports.html', context)


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def export_income_report_excel(request):
    user = request.user

    report = Fund.objects.filter(user=user).order_by('doc_number')

    # Create Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "units"
    ws.sheet_view.rightToLeft = True

    # Title
    title_cell = ws.cell(row=1, column=1, value=f"لیست تراکنش های من ")
    title_cell.font = Font(bold=True, size=18)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=5)

    # Headers
    headers = ['تاریخ پرداخت', 'شرح', 'روش پرداخت', 'شماره تراکنش', 'مبلغ']
    header_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")
    header_font = Font(bold=True, color="000000")
    for col_num, column_title in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_num, value=column_title)
        cell.fill = header_fill
        cell.font = header_font

    # Write data
    for row_num, fund in enumerate(report, start=3):
        ws.cell(row=row_num, column=1, value=show_jalali(fund.payment_date))
        ws.cell(row=row_num, column=2, value=fund.payment_description)
        ws.cell(row=row_num, column=3, value=fund.payment_gateway)
        ws.cell(row=row_num, column=4, value=fund.transaction_no)
        ws.cell(row=row_num, column=5, value=fund.amount)

    # Return response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=report.xlsx'
    wb.save(response)
    return response


@login_required(login_url=settings.LOGIN_URL_ADMIN)
def export_income_report_pdf(request):
    user = request.user

    funds = Fund.objects.filter(user=user).order_by('doc_number')

    house = None
    if request.user.is_authenticated:
        house = MyHouse.objects.filter(residents=request.user).order_by('-created_at').first()

    # # Queryset اصلی بر اساس واحد (کاربر مالک)
    # funds = Fund.objects.filter(unit=unit).order_by('payment_date')

    # فیلترها از GET
    query = request.GET.get('q', '').strip()
    if query:
        funds = funds.filter(
            Q(payment_description__icontains=query) |
            Q(payment_gateway__icontains=query) |
            Q(transaction_no__icontains=query) |
            Q(payment_date__icontains=query) |
            Q(amount__icontains=query)

        )

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
        table {{
            border-collapse: collapse;
            width: 100%;
        }}
        th, td {{
            border: 1px solid #000;
            padding: 5px;
            text-align: center;
        }}
        th {{
            background-color: #FFD700;
        }}
    """)

    # Render template
    template = get_template("user_report_pdf.html")
    context = {
        'funds': funds,
        'query': query,
        'font_path': font_url,
        'today': datetime.now(),
        'house': house,
    }

    html = template.render(context)
    pdf_file = io.BytesIO()
    HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(pdf_file, stylesheets=[css])
    pdf_file.seek(0)

    # Response
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="report.pdf"'
    return response
