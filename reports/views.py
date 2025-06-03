from django.shortcuts import render

from admin_panel.models import Fund


def fund_turnover(request):
    funds = Fund.objects.all()
    context = {
        'funds': funds
    }
    return render(request, 'fund_turnover.html', context)


def unit_reports(request):
    return render(request, 'unit_reports.html')
