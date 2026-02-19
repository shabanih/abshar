import json
from datetime import timedelta
from decimal import Decimal

import requests
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from admin_panel.models import SmsCredit, AdminFund, SubscriptionPlan, Subscription
from payment_app.views import ZP_API_STARTPAY, ZP_API_REQUEST
from user_app.models import Bank, MyHouse

MERCHANT = "3d6d6a26-c139-49ac-9d8d-b03a8cdf0fdd"

# ZP_API_REQUEST = "https://api.zarinpal.com/pg/v4/payment/request.json"
# ZP_API_VERIFY = "https://api.zarinpal.com/pg/v4/payment/verify.json"
# ZP_API_STARTPAY = "https://www.zarinpal.com/pg/StartPay/{authority}"#


ZP_API_REQUEST = "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
ZP_API_VERIFY = "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
ZP_API_STARTPAY = "https://sandbox.zarinpal.com/pg/StartPay/{authority}"

description = "Raya"  # Required

CallbackURLSMS = 'http://127.0.0.1:8001/admin-payment/verify-sms-pay/'
CallbackURLSub = 'http://127.0.0.1:8001/admin-payment/verify-subscription-pay/'

@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def request_sms_pay(request):
    if request.method != 'POST':
        return redirect('add_sms_credit')  # صفحه فرم شارژ پیامک

    amount = request.POST.get('amount')
    try:
        # حذف کاما و تبدیل به عدد صحیح
        amount = int(amount.replace(',', ''))
        if amount <= 0:
            messages.error(request, "مبلغ وارد شده معتبر نیست")
            return redirect('add_sms_credit')
    except Exception:
        messages.error(request, "مبلغ وارد شده معتبر نیست")
        return redirect('add_sms_credit')

    # محاسبه مالیات ۱۰٪
    amount_with_tax = round(amount * 1.1)

    # ایجاد رکورد SmsCredit
    credit = SmsCredit.objects.create(
        user=request.user,
        amount=Decimal(amount),              # مبلغ اصلی
        amount_with_tax=Decimal(amount_with_tax),  # شامل مالیات
        is_paid=False
    )

    # آماده سازی داده برای درگاه (ریال و int)
    req_data = {
        "merchant_id": MERCHANT,
        "amount": int(amount_with_tax * 10),  # تومان → ریال و int
        "callback_url": f"{CallbackURLSMS}?credit_id={credit.id}",
        "description": "شارژ حساب پیامک",
    }

    req_header = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    try:
        req = requests.post(
            url=ZP_API_REQUEST,
            data=json.dumps(req_data),  # هیچ Decimal ای وجود ندارد
            headers=req_header
        )
        result = req.json()

        if req.status_code == 200 and 'authority' in result.get('data', {}):
            authority = result['data']['authority']
            return redirect(ZP_API_STARTPAY.format(authority=authority))

        # خطا در درخواست
        e_code = result.get('errors', {}).get('code', '')
        e_message = result.get('errors', {}).get('message', '')
        return HttpResponse(f"{e_code} - {e_message}")

    except requests.RequestException as e:
        return HttpResponse(f"خطا در ارتباط با درگاه: {e}", status=500)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def verify_sms_credit_pay(request):
    credit_id = request.GET.get('credit_id')
    authority = request.GET.get('Authority')
    status = request.GET.get('Status')
    house = MyHouse.objects.filter(user=request.user).first()

    if not credit_id:
        return render(request, 'admin_payment_done.html', {'error': 'شناسه پرداخت ارسال نشده است'})

    credit = get_object_or_404(SmsCredit, id=credit_id, is_paid=False)

    if status != 'OK':
        messages.error(request, 'پرداخت لغو شد')
        return redirect('add_sms_credit')

    # مبلغ شامل مالیات برای تأیید پرداخت
    req_data = {
        "merchant_id": MERCHANT,
        "amount": int(credit.amount_with_tax * 10),  # تومان → ریال و int
        "authority": authority
    }

    req_header = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    try:
        req = requests.post(ZP_API_VERIFY, data=json.dumps(req_data), headers=req_header)
        result = req.json()

        if result.get('errors'):
            return render(request, 'admin_payment_done.html', {
                'error': result['errors'].get('message'),
                'credit': credit
            })

        code = result['data'].get('code')
        if code == 100:
            ref_id = result['data'].get('ref_id')

            # ثبت اطلاعات پرداخت
            credit.is_paid = True
            credit.house = house
            credit.paid_at = timezone.now()
            credit.transaction_reference = ref_id
            credit.payment_gateway = 'پرداخت اینترنتی'
            credit.save()

            content_type = ContentType.objects.get_for_model(SmsCredit)
            AdminFund.objects.create(
                user=request.user,
                bank=None,  # اگر بانک مربوط به درگاه داری می‌تونی اینجا بفرستی
                content_type=content_type,
                object_id=credit.id,
                amount=credit.amount_with_tax,
                payment_gateway='پرداخت اینترنتی',
                payment_date=credit.paid_at,
                transaction_no=ref_id,
                payment_description=f"شارژ حساب پیامک ",
                is_paid=True
            )


            messages.success(request, f'پرداخت با موفقیت انجام شد. کد پیگیری: {ref_id}')
            return redirect('add_sms_credit')

        elif code == 101:
            messages.info(request, 'این پرداخت قبلاً ثبت شده است')
            return redirect('add_sms_credit')

        return render(request, 'admin_payment_done.html', {
            'error': result['data'].get('message'),
            'credit': credit
        })

    except Exception as e:
        return render(request, 'admin_payment_done.html', {
            'error': f"خطا: {e}",
            'credit': credit
        })



@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def request_subscription_pay(request):

    if request.method != 'POST':
        return redirect('buy_subscription')

    plan_id = request.POST.get('plan')
    units_count = request.POST.get('units_count')

    # ---------- اعتبارسنجی ----------
    if not plan_id or not units_count:
        messages.error(request, "اطلاعات ناقص است")
        return redirect('buy_subscription')

    try:
        units_count = int(units_count)
        if units_count <= 0:
            raise ValueError
    except:
        messages.error(request, "تعداد واحد نامعتبر است")
        return redirect('buy_subscription')

    # ---------- گرفتن پلن ----------
    try:
        plan = SubscriptionPlan.objects.get(id=plan_id)
    except SubscriptionPlan.DoesNotExist:
        messages.error(request, "پلن انتخابی معتبر نیست")
        return redirect('buy_subscription')

    # ---------- محاسبه مبلغ ----------
    amount = units_count * plan.price_per_unit

    # اگر مالیات می‌خوای:
    # amount = round(amount * 1.1)

    # ---------- ساخت Subscription ----------
    sub = Subscription.objects.create(
        user=request.user,
        units_count=units_count,
        plan=plan,
        total_amount=amount,
        is_paid=False
    )

    # ---------- آماده سازی درگاه ----------
    req_data = {
        "merchant_id": MERCHANT,
        "amount": int(amount * 10),  # تومان → ریال
        "callback_url": f"{CallbackURLSub}?sub_id={sub.id}",
        "description": "خرید اشتراک ساختمان",
    }

    req_header = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    # ---------- درخواست به درگاه ----------
    try:
        req = requests.post(
            ZP_API_REQUEST,
            data=json.dumps(req_data),
            headers=req_header
        )

        result = req.json()

        if req.status_code == 200 and 'authority' in result.get('data', {}):
            authority = result['data']['authority']
            return redirect(ZP_API_STARTPAY.format(authority=authority))

        # خطای درگاه
        e = result.get('errors', {})
        return HttpResponse(f"{e.get('code')} - {e.get('message')}")

    except requests.RequestException as e:
        return HttpResponse(f"خطا در ارتباط با درگاه: {e}", status=500)



@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def verify_subscription_pay(request):
    sub_id = request.GET.get('sub_id')
    authority = request.GET.get('Authority')
    status = request.GET.get('Status')

    if not sub_id:
        return render(request, 'admin_payment_done.html', {
            'error': 'شناسه اشتراک ارسال نشده'
        })

    # فقط اشتراک‌های خود کاربر
    subscription = get_object_or_404(
        Subscription,
        id=sub_id,
        user=request.user,
        is_paid=False
    )

    # اگر کاربر پرداخت را لغو کرد
    if status != 'OK':
        messages.error(request, "پرداخت لغو شد")
        return redirect('buy_subscription')

    # بررسی plan
    if not subscription.plan:
        return render(request, 'admin_payment_done.html', {
            'error': 'پلن اشتراک مشخص نیست'
        })

    # -------- Verify به زرین پال --------
    req_data = {
        "merchant_id": MERCHANT,
        "amount": int(subscription.total_amount * 10),  # تومان → ریال
        "authority": authority
    }

    req_header = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    try:
        req = requests.post(
            ZP_API_VERIFY,
            data=json.dumps(req_data),
            headers=req_header
        )

        result = req.json()
        data = result.get('data', {})

        # خطای زرین پال
        if result.get('errors'):
            return render(request, 'admin_payment_done.html', {
                'error': result['errors'].get('message', 'خطای نامشخص در درگاه پرداخت')
            })

        code = data.get('code')

        # ---------- پرداخت موفق ----------
        if code == 100:
            ref_id = data.get('ref_id')
            now = timezone.now()

            subscription.is_paid = True
            subscription.is_trial = False
            subscription.payment_date = now
            subscription.house = MyHouse.objects.filter(user=request.user).first()
            subscription.transaction_id = ref_id

            # ---------- تعیین مدت اشتراک ----------
            now = timezone.now()

            if subscription.end_date and subscription.end_date > now:
                # اگر هنوز اشتراک فعال است → از تاریخ پایان فعلی ادامه بده
                subscription.start_date = subscription.end_date
            else:
                subscription.start_date = now

            subscription.end_date = subscription.start_date + relativedelta(
                months=subscription.plan.duration
            )

            subscription.save()

            content_type = ContentType.objects.get_for_model(Subscription)
            AdminFund.objects.create(
                user=request.user,
                bank=None,  # اگر بانک مربوط به درگاه داری می‌تونی اینجا بفرستی
                content_type=content_type,
                object_id=subscription.id,
                amount=subscription.total_amount,
                payment_gateway='پرداخت اینترنتی',
                payment_date=subscription.payment_date,
                transaction_no=ref_id,
                payment_description=f"خرید اشتراک {subscription.plan} ",
                is_paid=True
            )

            messages.success(
                request,
                f"پرداخت موفق. کد پیگیری: {ref_id}"
            )

            return redirect('middle_admin_dashboard')

        # ---------- پرداخت تکراری ----------
        elif code == 101:
            messages.info(request, "این پرداخت قبلاً ثبت شده")
            return redirect('middle_admin_dashboard')

        # سایر خطاها
        return render(request, 'admin_payment_done.html', {
            'error': data.get('message', 'خطای نامشخص در پرداخت')
        })

    except Exception as e:
        return render(request, 'admin_payment_done.html', {
            'error': f"خطا در تأیید پرداخت: {e}"
        })


