import json
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from admin_panel.forms import UnifiedChargePaymentForm
from admin_panel.models import Fund, UnifiedCharge
from user_app.forms import UserPayMoneyForm, UserPayGateForm
from user_app.models import Bank, UserPayMoney

MERCHANT = "3d6d6a26-c139-49ac-9d8d-b03a8cdf0fdd"

# ZP_API_REQUEST = "https://api.zarinpal.com/pg/v4/payment/request.json"
# ZP_API_VERIFY = "https://api.zarinpal.com/pg/v4/payment/verify.json"
# ZP_API_STARTPAY = "https://www.zarinpal.com/pg/StartPay/{authority}"#


ZP_API_REQUEST = "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
ZP_API_VERIFY = "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
ZP_API_STARTPAY = "https://sandbox.zarinpal.com/pg/StartPay/{authority}"

description = "Raya"  # Required

CallbackURLCharge = 'http://127.0.0.1:8001/payment/verify-pay/'
CallbackURLUserPay = 'http://127.0.0.1:8001/payment/user-pay-verify/'


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def request_pay(request: HttpRequest, charge_id):
    if not request.user.is_authenticated:
        return redirect('login')  # Ensure the user is logged in

    try:
        charge = get_object_or_404(UnifiedCharge, id=charge_id, is_paid=False,
                                   send_notification=True)

        if not charge.total_charge_month or charge.total_charge_month <= 0:
            return HttpResponse("مبلغ شارژ نامعتبر است.", status=400)

        charge.update_penalty(save=True)
        total_fix_charge = charge.total_charge_month
        # charge.save()
        callback_url = f"{CallbackURLCharge}?charge_id={charge.id}"  # اضافه کردن charge_id

        req_data = {
            "merchant_id": MERCHANT,  # Ensure MERCHANT is defined
            "amount": total_fix_charge * 10,
            "callback_url": callback_url,  # Ensure CallbackURL is defined
            "description": description,  # Ensure description is defined
            # "metadata": {"mobile": mobile, "email": email}  # Add if needed
        }
        print(req_data)

        req_header = {"accept": "application/json", "content-type": "application/json"}
        req = requests.post(url=ZP_API_REQUEST, data=json.dumps(req_data), headers=req_header)
        req_data = req.json()

        if req.status_code == 200 and 'data' in req_data and 'authority' in req_data['data']:
            authority = req_data['data']['authority']
            return redirect(ZP_API_STARTPAY.format(authority=authority))
        else:
            e_code = req_data.get('errors', {}).get('code', 'Unknown Code')
            e_message = req_data.get('errors', {}).get('message', 'Unknown Error')
            return HttpResponse(f"Error code: {e_code}, Error Message: {e_message}")

    except UnifiedCharge.DoesNotExist:
        return HttpResponse("middleCharge not found.", status=404)
    except requests.RequestException as e:
        return HttpResponse(f"Payment request failed: {str(e)}", status=500)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def verify_pay(request: HttpRequest):
    charge_id = request.GET.get('charge_id')
    if not charge_id:
        return render(request, 'payment_gateway.html', {
            'error': 'شناسه شارژ ارسال نشده است.'
        })

    payment_charge = get_object_or_404(UnifiedCharge, id=charge_id, is_paid=False)

    if not payment_charge:
        return JsonResponse({"error": "Charge not found"}, status=404)

    total_fix_charge = payment_charge.total_charge_month

    t_authority = request.GET.get('Authority')

    if request.GET.get('Status') == 'OK':
        req_header = {"accept": "application/json", "content-type": "application/json"}
        req_data = {
            "merchant_id": MERCHANT,
            "amount": total_fix_charge * 10,
            "authority": t_authority
        }

        try:
            req = requests.post(url=ZP_API_VERIFY, data=json.dumps(req_data), headers=req_header)
            req_data = req.json()

            default_bank = Bank.objects.filter(
                user=payment_charge.user,
                house=payment_charge.unit.myhouse,
                is_gateway=True,
                is_active=True
            ).first()

            if not default_bank:
                messages.error(request, 'حساب درگاه اینترنتی تعریف نشده است.')
                return redirect('user_charges')

            if not req_data.get('errors'):
                t_status = req_data['data']['code']
                if t_status == 100:
                    ref_str = req_data['data']['ref_id']

                    payment_charge.bank = default_bank
                    payment_charge.transaction_reference = ref_str
                    payment_charge.is_paid = True
                    payment_charge.payment_date = timezone.now()
                    payment_charge.payment_gateway = 'پرداخت اینترنتی'
                    payment_charge.save()

                    content_type = ContentType.objects.get_for_model(payment_charge)
                    Fund.objects.create(
                        content_type=content_type,
                        object_id=payment_charge.id,
                        unit=payment_charge.unit,
                        house=payment_charge.house,
                        bank=default_bank,
                        debtor_amount=payment_charge.total_charge_month,
                        amount=payment_charge.total_charge_month,
                        creditor_amount=0,
                        user=request.user,
                        payer_name=payment_charge.unit.get_label(),
                        payment_date=payment_charge.payment_date,
                        payment_description=f"{payment_charge.title}",
                        transaction_no=payment_charge.transaction_reference,
                        payment_gateway='پرداخت اینترنتی'
                    )

                    messages.success(
                        request,
                        f'پرداخت با موفقیت انجام شد. کد پیگیری: {ref_str}'
                    )
                    return redirect('user_charges')
                elif t_status == 101:
                    messages.info(request, 'این تراکنش قبلاً ثبت شده است.')
                    return redirect('user_charges')
                else:
                    return render(request, 'payment_done.html', {
                        'error': str(req_data['data']['message']),
                        'charge': payment_charge,  # ← این خط حیاتی است
                    })
            else:
                e_code = req_data['errors'].get('code')
                e_message = req_data['errors'].get('message')
                return render(request, 'payment_done.html', {
                    'error': f"Error code: {e_code}, Message: {e_message}",
                    'charge': payment_charge,  # ← این خط حیاتی است
                })
        except Exception as e:
            return render(request, 'payment_done.html', {
                'error': f"An error occurred: {str(e)}",
                'charge': payment_charge,  # ← این خط حیاتی است
            })

    else:
        payment_charge.is_paid = False
        payment_charge.save()
        return redirect('user_fixed_charges')


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def payment_charge_user_view(request, pk):
    charge = get_object_or_404(UnifiedCharge, pk=pk)

    # اجازه پرداخت برای مستاجر یا مالک
    unit = charge.unit
    renter = unit.get_active_renter()

    if request.user != unit.user and (not renter or renter.user != request.user):
        # نه مالک است نه مستاجر فعال → دسترسی ندارد
        raise PermissionDenied("شما اجازه دسترسی به این شارژ را ندارید.")

    if request.method == 'POST':
        form = UnifiedChargePaymentForm(request.POST, instance=charge, charge=charge)
        if form.is_valid():
            charge = form.save(commit=False)
            charge.is_paid = True
            charge.payment_gateway = 'کارت به کارت'
            charge.update_penalty(save=False)
            charge.save()

            # ثبت Fund

            content_type = ContentType.objects.get_for_model(charge)
            Fund.objects.create(
                content_type=content_type,
                object_id=charge.id,
                unit=charge.unit,
                house=charge.house,
                bank=charge.bank,
                debtor_amount=charge.total_charge_month,
                amount=charge.total_charge_month,
                creditor_amount=0,
                user=request.user,
                payer_name=charge.unit.get_label(),
                payment_date=charge.payment_date,
                payment_description=f"{charge.title}",
                transaction_no=charge.transaction_reference,
                payment_gateway='کارت به کارت'
            )
            messages.success(request, 'پرداخت شارژ با موفقیت ثبت گردید')
            return redirect('user_charges')
        else:
            messages.error(request, 'خطا در ثبت پرداخت ')
            return redirect('user_charges')
    else:
        form = UnifiedChargePaymentForm(instance=charge, charge=charge)
        return render(request, 'payment_gateway.html', {
            'charge': charge,
            'form': form
        })


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def user_pay_money_view(request, pk):
    pay = get_object_or_404(UserPayMoney, pk=pk)
    house = pay.unit.myhouse  # خانه مربوط به واحد را می‌گیریم

    if request.method == 'POST':
        form = UserPayGateForm(request.POST, instance=pay, house=house)
        if form.is_valid():
            pay = form.save(commit=False)
            pay.is_paid = True
            pay.payment_gateway = 'کارت به کارت'
            pay.save()

            # بانک انتخاب‌شده از فرم
            selected_bank = form.cleaned_data['bank']

            # ثبت Fund
            content_type = ContentType.objects.get_for_model(UserPayMoney)
            Fund.objects.create(
                content_type=content_type,
                object_id=pay.id,
                unit=pay.unit,
                house=pay.house,
                bank=selected_bank,
                debtor_amount=pay.amount,
                amount=pay.amount,
                creditor_amount=0,
                user=request.user,
                payer_name=pay.unit.get_label(),
                payment_date=pay.payment_date,
                payment_description=f" پرداخت به ساختمان: {(pay.description or '')[:50]}",
                transaction_no=pay.transaction_reference,
                payment_gateway='کارت به کارت'
            )

            messages.success(request, 'پرداخت شما با موفقیت ثبت گردید')
            return redirect('user_pay_money')
        else:
            messages.error(request, 'خطا در ثبت پرداخت')
            return render(request, 'user_pay_gateway.html', {'pay': pay, 'form': form})
    else:
        form = UserPayGateForm(instance=pay, house=house)
        return render(request, 'user_pay_gateway.html', {'pay': pay, 'form': form})


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def request_user_pay_money(request: HttpRequest, pay_id):
    pay = get_object_or_404(
        UserPayMoney,
        id=pay_id,
        is_paid=False
    )

    if not pay.amount or pay.amount <= 0:
        return HttpResponse("مبلغ پرداخت نامعتبر است.", status=400)

    callback_url = f"{CallbackURLUserPay}?pay_id={pay.id}"

    req_data = {
        "merchant_id": MERCHANT,
        "amount": pay.amount * 10,  # تومان → ریال
        "callback_url": callback_url,
        "description": pay.description or "پرداخت اینترنتی",
    }

    req_header = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    try:
        req = requests.post(
            url=ZP_API_REQUEST,
            data=json.dumps(req_data),
            headers=req_header
        )
        req_data = req.json()

        if req.status_code == 200 and 'authority' in req_data.get('data', {}):
            authority = req_data['data']['authority']
            return redirect(ZP_API_STARTPAY.format(authority=authority))

        e_code = req_data.get('errors', {}).get('code')
        e_message = req_data.get('errors', {}).get('message')
        return HttpResponse(f"{e_code} - {e_message}")

    except requests.RequestException as e:
        return HttpResponse(f"خطا در ارتباط با درگاه: {e}", status=500)


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def verify_user_pay_money(request: HttpRequest):
    pay_id = request.GET.get('pay_id')
    authority = request.GET.get('Authority')
    status = request.GET.get('Status')

    if not pay_id:
        return render(request, 'payment_done.html', {
            'error': 'شناسه پرداخت ارسال نشده است'
        })

    pay = get_object_or_404(UserPayMoney, id=pay_id, is_paid=False)

    if status != 'OK':
        messages.error(request, 'پرداخت لغو شد')
        return redirect('user_pay_money')

    req_data = {
        "merchant_id": MERCHANT,
        "amount": pay.amount * 10,
        "authority": authority
    }

    req_header = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    try:
        req = requests.post(
            url=ZP_API_VERIFY,
            data=json.dumps(req_data),
            headers=req_header
        )
        result = req.json()

        if result.get('errors'):
            return render(request, 'payment_done.html', {
                'error': result['errors'].get('message'),
                'pay': pay
            })

        code = result['data']['code']

        if code == 100:
            ref_id = result['data']['ref_id']

            # بانک پیش‌فرض درگاه
            bank = Bank.objects.filter(
                house=pay.unit.myhouse,
                is_gateway=True,
                is_active=True
            ).first()

            if not bank:
                messages.error(request, 'حساب درگاه اینترنتی تعریف نشده است')
                return redirect('user_pay_money')

            pay.bank = bank
            pay.transaction_reference = ref_id
            pay.is_paid = True
            pay.payment_gateway = 'پرداخت اینترنتی'
            pay.payment_date = timezone.now()
            pay.save()

            # ثبت Fund
            content_type = ContentType.objects.get_for_model(pay)
            Fund.objects.create(
                content_type=content_type,
                object_id=pay.id,
                unit=pay.unit,
                house=pay.house,
                bank=bank,
                debtor_amount=0,
                amount=pay.amount,
                creditor_amount=pay.amount,
                user=request.user,
                payer_name=pay.unit.get_label(),
                payment_date=pay.payment_date,
                payment_description=f" پرداخت به ساختمان: {(pay.description or '')[:50]}",
                transaction_no=ref_id,
                payment_gateway='پرداخت اینترنتی'
            )


            messages.success(request, f'پرداخت با موفقیت انجام شد. کد پیگیری: {ref_id}')
            return redirect('user_pay_money')

        elif code == 101:
            messages.info(request, 'این پرداخت قبلاً ثبت شده است')
            return redirect('user_pay_money')

        return render(request, 'payment_done.html', {
            'error': result['data'].get('message'),
            'pay': pay
        })

    except Exception as e:
        return render(request, 'payment_done.html', {
            'error': f"خطا: {e}",
            'pay': pay
        })


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def unit_charge_middle_payment_view(request, charge_id):

    charge = get_object_or_404(
        UnifiedCharge,
        id=charge_id,
        user=request.user,
        is_paid=False
    )

    # جلوگیری از پرداخت تکراری
    if charge.is_paid:
        messages.warning(request, "این شارژ قبلاً پرداخت شده است.")
        return redirect('charge_units_list')

    if request.method == "POST":
        form = UnifiedChargePaymentForm(
            request.POST,
            instance=charge
        )

        if form.is_valid():
            with transaction.atomic():

                unified_charge = form.save(commit=False)

                unified_charge.is_paid = True
                unified_charge.payment_gateway = 'پرداخت الکترونیک'
                unified_charge.update_penalty(save=False)

                unified_charge.save(update_fields=[
                    'payment_date',
                    'transaction_reference',
                    'bank',
                    'is_paid',
                    'payment_gateway'
                ])

                content_type = ContentType.objects.get_for_model(UnifiedCharge)

                Fund.objects.create(
                    content_type=content_type,
                    object_id=unified_charge.id,
                    bank=unified_charge.bank,
                    unit=unified_charge.unit,
                    house=unified_charge.house,
                    payer_name=unified_charge.unit.get_label(),
                    debtor_amount=unified_charge.total_charge_month,
                    amount=unified_charge.total_charge_month,
                    creditor_amount=0,
                    user=request.user,
                    payment_date=unified_charge.payment_date,
                    payment_description=unified_charge.title,
                    transaction_no=unified_charge.transaction_reference,
                    payment_gateway='پرداخت الکترونیک'
                )

            main_charge = unified_charge.main_charge
            charge_name = getattr(main_charge, 'name', 'شارژ')

            messages.success(
                request,
                f"پرداخت '{charge_name}' با موفقیت ثبت شد."
            )

            return redirect(
                reverse(
                    'charge_units_list',
                    args=[
                        main_charge._meta.app_label,
                        main_charge._meta.model_name,
                        main_charge.id
                    ]
                )
            )

        messages.error(request, "خطا در ثبت اطلاعات پرداخت.")

    else:
        form = UnifiedChargePaymentForm(instance=charge)

    return render(request, 'charge_payment_gateway.html', {
        'charge': charge,
        'form': form,
        'app_label': charge._meta.app_label,
        'model_name': charge._meta.model_name,
    })


