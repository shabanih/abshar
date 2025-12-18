from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import render

from admin_panel.models import Fund


def fund_turnover(request):
    manager = request.user
    query = request.GET.get('q', '').strip()
    paginate = int(request.GET.get('paginate', 20) or 20)
    paginate = paginate if paginate > 0 else 20

    funds = (
        Fund.objects
        .select_related('bank', 'content_type')
        .filter(Q(user=manager) | Q(user__manager=manager))
        .order_by('-id')
    )

    if query:
        funds = funds.filter(
            Q(payment_description__icontains=query) |
            Q(transaction_no__icontains=query)
        )

    totals = funds.aggregate(
        total_income=Sum('creditor_amount'),
        total_expense=Sum('debtor_amount'),
    )

    balance = (totals['total_income'] or 0) - (totals['total_expense'] or 0)

    paginator = Paginator(funds, paginate)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'fund_turnover.html', {
        'funds': page_obj,
        'query': query,
        'paginate': paginate,
        'page_obj': page_obj,
        'totals': totals,
        'balance': balance,
    })


def unit_reports(request):
    return render(request, 'unit_reports.html')


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
                Q(transaction_no__icontains=query) |
                Q(payment_gateway__icontains=query)
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
