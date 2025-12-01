from django.shortcuts import render

from admin_panel.models import Fund


def fund_turnover(request):
    funds = Fund.objects.filter(user__manager=request.user)
    context = {
        'funds': funds
    }
    return render(request, 'fund_turnover.html', context)


def unit_reports(request):
    return render(request, 'unit_reports.html')


def fund_turnover_user(request):
    user = request.user

    if not user.manager:
        funds = []
    else:
        # فقط اطلاعیه‌های مدیر میانی کاربر
        funds = Fund.objects.filter(
            user=user,
        ).order_by('-created_at')
    context = {
        'funds': funds
    }
    return render(request, 'fund_turnover_user.html', context)
