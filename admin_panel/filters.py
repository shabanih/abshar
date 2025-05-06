import django_filters

from admin_panel.models import Expense


class ExpenseFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(lookup_expr='icontains', label='موضوع هزینه')
    amount = django_filters.NumberFilter(lookup_expr='icontains', label='مبلغ')
    date = django_filters.DateFilter(lookup_expr='icontains', label='تاریخ سند')
    description = django_filters.CharFilter(lookup_expr='icontains', label='شرح')
    details = django_filters.CharFilter(lookup_expr='icontains', label='توضیحات')
    doc_no = django_filters.NumberFilter(lookup_expr='icontains', label='شماره سند')

    class Meta:
        model = Expense
        fields = ['category', 'amount', 'date', 'description', 'details', 'doc_no']
