import io
import os
from datetime import timezone

import arabic_reshaper
import jdatetime
import openpyxl
from bidi.algorithm import get_display
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import ProtectedError, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import get_template, render_to_string
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, UpdateView, DetailView, ListView
from django_filters.views import FilterView

from openpyxl.styles import PatternFill, Font, Alignment
from pypdf import PdfMerger, PdfWriter
from weasyprint import HTML, CSS

from xhtml2pdf import pisa

from admin_panel.filters import ExpenseFilter
from admin_panel.forms import announcementForm, UnitForm, ExpenseForm, ExpenseCategoryForm, SearchExpenseForm, \
    IncomeForm, IncomeCategoryForm, MyHouseForm, BankForm
from admin_panel.models import Announcement, Expense, ExpenseCategory, ExpenseDocument, Income, IncomeDocument, \
    IncomeCategory
from user_app.models import Unit, MyHouse, Bank


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

# def edit_house(request, pk):
#     house = get_object_or_404(MyHouse, pk=pk)
#     if request.method == 'POST':
#         house_form = MyHouseForm(request.POST, instance=house)
#         if house_form.is_valid():
#             house_form.save()
#             messages.success(request, 'اطلاعات با موفقیت ویرایش شد.')
#             return redirect('manage_house')  # Adjust redirect as necessary
#         else:
#             messages.error(request, 'خطا در ویرایش فرم! لطفا دوباره تلاش کنید.')
#             return redirect('manage_house')
#     else:
#         # If the request is not POST, redirect to the appropriate page
#         return redirect('manage_house')


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

class UnitListView(ListView):
    model = Unit
    template_name = 'unit_templates/unit_management.html'
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


class UnitRegisterView(LoginRequiredMixin, CreateView):
    model = Unit
    form_class = UnitForm
    success_url = reverse_lazy('add_unit')
    template_name = 'unit_templates/unit_register.html'

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
    template_name = 'unit_templates/edit_unit.html'

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
    template_name = 'unit_templates/unit_info.html'
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
