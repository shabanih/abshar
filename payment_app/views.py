import json
import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest, HttpResponse, JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from admin_panel.forms import UnifiedChargePaymentForm
from admin_panel.models import FixedChargeCalc, AreaChargeCalc, PersonChargeCalc, FixPersonChargeCalc, \
    FixAreaChargeCalc, ChargeByPersonAreaCalc, ChargeByFixPersonAreaCalc, ChargeFixVariableCalc, Fund, UnifiedCharge
from user_app.models import Bank

MERCHANT = "3d6d6a26-c139-49ac-9d8d-b03a8cdf0fdd"

# ZP_API_REQUEST = "https://api.zarinpal.com/pg/v4/payment/request.json"
# ZP_API_VERIFY = "https://api.zarinpal.com/pg/v4/payment/verify.json"
# ZP_API_STARTPAY = "https://www.zarinpal.com/pg/StartPay/{authority}"#


ZP_API_REQUEST = "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
ZP_API_VERIFY = "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
ZP_API_STARTPAY = "https://sandbox.zarinpal.com/pg/StartPay/{authority}"

# amount = 1000  # Rial / Required
description = "Raya"  # Required
# phone = 'YOUR_PHONE_NUMBER'  # Optional
# Important: need to edit for realy server.
CallbackURLFix = 'http://127.0.0.1:8001/payment/verify-pay/'


# CallbackURLArea = 'http://127.0.0.1:8001/payment/verify-pay-area/'
# CallbackURLPerson = 'http://127.0.0.1:8001/payment/verify-pay-person/'
# CallbackURLFixPerson = 'http://127.0.0.1:8001/payment/verify-pay-fix-person/'
# CallbackURLFixArea = 'http://127.0.0.1:8001/payment/verify-pay-fix-area/'
# CallbackURLPersonArea = 'http://127.0.0.1:8001/payment/verify-pay-person-area/'
# CallbackURLFixPersonArea = 'http://127.0.0.1:8001/payment/verify-pay-fix-person-area/'
# CallbackURLFixVariable = 'http://127.0.0.1:8001/payment/verify-pay-fix-variable/'

@login_required()
def request_pay(request: HttpRequest, charge_id):
    if not request.user.is_authenticated:
        return redirect('login')  # Ensure the user is logged in

    try:
        charge = get_object_or_404(UnifiedCharge, id=charge_id, user=request.user, is_paid=False,
                                   send_notification=True)

        if not charge.total_charge_month or charge.total_charge_month <= 0:
            return HttpResponse("مبلغ شارژ نامعتبر است.", status=400)

        charge.update_penalty(save=True)
        total_fix_charge = charge.total_charge_month
        # charge.save()
        callback_url = f"{CallbackURLFix}?charge_id={charge.id}"  # اضافه کردن charge_id

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

    except FixedChargeCalc.DoesNotExist:
        return HttpResponse("middleCharge not found.", status=404)
    except requests.RequestException as e:
        return HttpResponse(f"Payment request failed: {str(e)}", status=500)


@login_required()
def verify_pay(request: HttpRequest):
    charge_id = request.GET.get('charge_id')
    if not charge_id:
        return render(request, 'payment_gateway.html', {
            'error': 'شناسه شارژ ارسال نشده است.'
        })

    payment_charge = get_object_or_404(UnifiedCharge, id=charge_id, user=request.user, is_paid=False)

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

            if not req_data.get('errors'):
                t_status = req_data['data']['code']
                if t_status == 100:
                    ref_str = req_data['data']['ref_id']
                    # payment_charge.bank = default_bank  # ⭐⭐⭐
                    payment_charge.transaction_reference = req_data['data']['ref_id']
                    payment_charge.is_paid = True
                    payment_charge.payment_date = timezone.now()
                    payment_charge.payment_gateway = 'پرداخت اینترنتی'
                    payment_charge.save()

                    content_type = ContentType.objects.get_for_model(payment_charge)
                    Fund.objects.create(
                        content_type=content_type,
                        object_id=payment_charge.id,
                        bank=payment_charge.bank,
                        unit=payment_charge.unit,
                        payer_name=payment_charge.unit,
                        debtor_amount=payment_charge.total_charge_month,
                        amount=payment_charge.total_charge_month,
                        creditor_amount=0,
                        user=request.user,
                        payment_date=payment_charge.payment_date,
                        payment_description=payment_charge.title,
                        transaction_no=payment_charge.transaction_reference,
                        payment_gateway='پرداخت اینترنتی'
                    )

                    return render(request, 'internet_payment_done.html', {
                        'success': f'تراکنش شما با کد پیگیری {ref_str} با موفقیت انجام و پرداخت شارژ شما ثبت گردید. ',
                        'charge': payment_charge,  # ← این خط حیاتی است
                    })
                elif t_status == 101:
                    return render(request, 'internet_payment_done.html', {
                        'info': 'این تراکنش قبلا ثبت شده است',
                        'charge': payment_charge,  # ← این خط حیاتی است
                    })
                else:
                    return render(request, 'internet_payment_done.html', {
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


@login_required
def paymentView(request, pk):
    # گرفتن شارژ
    charge = get_object_or_404(UnifiedCharge, pk=pk, user=request.user)

    if request.method == "POST":
        form = UnifiedChargePaymentForm(request.POST, instance=charge)
        if form.is_valid():
            charge = form.save(commit=False)
            charge.is_paid = True
            charge.payment_gateway = 'کارت به کارت'

            # به‌روزرسانی جریمه قبل از ذخیره
            charge.update_penalty()

            # ذخیره اطلاعات شارژ
            charge.save(update_fields=[
                'is_paid', 'payment_gateway', 'payment_date', 'transaction_reference', 'penalty_amount'
            ])

            # بروزرسانی مدل محاسبه اصلی در صورت وجود
            calc_model = CHARGE_CALC_MAP.get(charge.charge_type)
            if calc_model:
                calc_charge = calc_model.objects.filter(pk=charge.object_id).first()
                if calc_charge:
                    calc_charge.payment_date = charge.payment_date
                    calc_charge.transaction_reference = charge.transaction_reference
                    if hasattr(calc_charge, 'is_paid'):
                        calc_charge.is_paid = True
                        calc_charge.save(update_fields=['payment_date', 'transaction_reference', 'is_paid'])
                    else:
                        calc_charge.save(update_fields=['payment_date', 'transaction_reference'])

            # ثبت در صندوق
            Fund.objects.create(
                content_type=ContentType.objects.get_for_model(charge),
                object_id=charge.id,
                bank=charge.bank,
                unit=charge.unit,
                payer_name=getattr(charge.unit, 'unit_number', str(charge.unit)),
                debtor_amount=charge.total_charge_month,
                amount=charge.total_charge_month,
                creditor_amount=0,
                user=request.user,
                payment_date=charge.payment_date,
                payment_description=charge.title,
                transaction_no=charge.transaction_reference,
                payment_gateway='پرداخت الکترونیک'
            )

            messages.success(request, 'پرداخت شما با موفقیت ثبت شد.')
            return redirect('payment_done', pk=charge.id)

        else:
            # نمایش فرم با خطاها بدون ریدایرکت
            messages.error(request, 'خطا در ثبت اطلاعات پرداخت. لطفاً فرم را بررسی کنید.')
            return render(request, 'payment_gateway.html', {
                'form': form,
                'charge': charge
            })

    else:
        # نمایش فرم برای پرداخت
        form = UnifiedChargePaymentForm(instance=charge)
        return render(request, 'payment_gateway.html', {
            'form': form,
            'charge': charge
        })

def payment_done_view(request, pk):
    charge = get_object_or_404(UnifiedCharge, pk=pk)
    return render(request, 'payment_done.html', {'charge': charge})


CHARGE_CALC_MAP = {
    'fix': FixedChargeCalc,
    'area': AreaChargeCalc,
    'person': PersonChargeCalc,
    'fix_person': FixPersonChargeCalc,
    'fix_area': FixAreaChargeCalc,
    'person_area': ChargeByPersonAreaCalc,
    'fix_person_area': ChargeByFixPersonAreaCalc,
    'fix_variable': ChargeFixVariableCalc,
}

CHARGE_FK_FIELD = {
    'fix': 'fix_charge_id',
    'area': 'area_charge_id',
    'person': 'person_charge_id',
    'fix_person': 'fix_person_charge_id',
    'fix_area': 'fix_area_charge_id',
    'person_area': 'person_area_charge_id',
    'fix_person_area': 'fix_person_area_id',
    'fix_variable': 'fix_variable_charge_id',
}


@login_required
def unit_charge_payment_view(request, charge_type, charge_id):
    # 1️⃣ انتخاب مدل محاسبه
    model = CHARGE_CALC_MAP.get(charge_type)
    if not model:
        raise Http404('نوع شارژ نامعتبر است')

    # 2️⃣ گرفتن نمونه شارژ محاسبه شده (مثل FixChargeCalc)
    calc_charge = get_object_or_404(model, pk=charge_id, is_active=True)

    # 3️⃣ گرفتن یا ساخت UnifiedCharge متناظر
    unified_charge, created = UnifiedCharge.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(calc_charge),
        object_id=calc_charge.id,
        defaults={
            'user': calc_charge.user,
            'unit': getattr(calc_charge, 'unit', None),
            'bank': getattr(calc_charge, 'bank', None),
            'amount': getattr(calc_charge, 'amount', 0),
            'charge_type': charge_type,
            'total_charge_month': getattr(calc_charge, 'amount', 0),
            'title': getattr(calc_charge, 'name', ''),
        }
    )

    # 4️⃣ پردازش فرم
    if request.method == "POST":
        form = UnifiedChargePaymentForm(request.POST, instance=unified_charge)
        if form.is_valid():
            unified_charge = form.save(commit=False)
            unified_charge.is_paid = True
            unified_charge.payment_gateway = 'کارت به کارت'
            # بدون پارامتر save
            unified_charge.update_penalty()
            # ذخیره با همه فیلدهای تغییر یافته
            unified_charge.save(update_fields=['is_paid', 'payment_gateway', 'payment_date', 'transaction_reference'])

            # بروزرسانی مدل محاسبه اصلی
            calc_charge.payment_date = unified_charge.payment_date
            calc_charge.transaction_reference = unified_charge.transaction_reference
            fields_to_update = ['payment_date', 'transaction_reference']
            if hasattr(calc_charge, 'is_paid'):
                calc_charge.is_paid = True
                fields_to_update.append('is_paid')
            calc_charge.save(update_fields=fields_to_update)

            # ثبت در صندوق
            Fund.objects.create(
                content_type=ContentType.objects.get_for_model(calc_charge),
                object_id=unified_charge.id,
                bank=unified_charge.bank,
                unit=unified_charge.unit,
                payer_name=unified_charge.unit,
                debtor_amount=unified_charge.total_charge_month,
                amount=unified_charge.total_charge_month,
                creditor_amount=0,
                user=request.user,
                payment_date=unified_charge.payment_date,
                payment_description=unified_charge.title,
                transaction_no=unified_charge.transaction_reference,
                payment_gateway='پرداخت الکترونیک'
            )

            messages.success(request, "پرداخت شارژ واحد با موفقیت ثبت شد.")
            return redirect(reverse('charge_payment_done', args=[unified_charge.id]))


        else:
            messages.error(request, "خطا در ثبت اطلاعات پرداخت. لطفاً فرم را بررسی کنید.")
            return render(request, 'charge_payment_gateway.html', {
                'charge': unified_charge,
                'form': form
            })

    else:
        # نمایش فرم برای پرداخت
        form = UnifiedChargePaymentForm(instance=unified_charge)
        return render(request, 'charge_payment_gateway.html', {
            'charge': unified_charge,
            'form': form
        })


@login_required
def charge_payment_done_view(request, pk):
    charge = get_object_or_404(UnifiedCharge, pk=pk)
    return render(request, 'charge_payment_done.html', {'charge': charge})

