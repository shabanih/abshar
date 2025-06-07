import json

import requests
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from admin_panel.models import FixedChargeCalc, AreaChargeCalc, PersonChargeCalc, FixPersonChargeCalc, \
    FixAreaChargeCalc, ChargeByPersonAreaCalc, ChargeByFixPersonAreaCalc, ChargeFixVariableCalc, Fund

MERCHANT = "3d6d6a26-c139-49ac-9d8d-b03a8cdf0fdd"

ZP_API_REQUEST = "https://api.zarinpal.com/pg/v4/payment/request.json"
ZP_API_VERIFY = "https://api.zarinpal.com/pg/v4/payment/verify.json"
ZP_API_STARTPAY = "https://www.zarinpal.com/pg/StartPay/{authority}"

amount = 1000  # Rial / Required
description = "Raya"  # Required
# phone = 'YOUR_PHONE_NUMBER'  # Optional
# Important: need to edit for realy server.
CallbackURLFix = 'http://127.0.0.1:8000/payment/verify-pay-fix/'
CallbackURLArea = 'http://127.0.0.1:8000/payment/verify-pay-area/'
CallbackURLPerson = 'http://127.0.0.1:8000/payment/verify-pay-person/'
CallbackURLFixPerson = 'http://127.0.0.1:8000/payment/verify-pay-fix-person/'
CallbackURLFixArea = 'http://127.0.0.1:8000/payment/verify-pay-fix-area/'
CallbackURLPersonArea = 'http://127.0.0.1:8000/payment/verify-pay-person-area/'
CallbackURLFixPersonArea = 'http://127.0.0.1:8000/payment/verify-pay-fix-person-area/'
CallbackURLFixVariable = 'http://127.0.0.1:8000/payment/verify-pay-fix-variable/'


@login_required()
def request_pay_fix(request: HttpRequest, charge_id):
    if not request.user.is_authenticated:
        return redirect('login')  # Ensure the user is logged in

    try:
        charge = get_object_or_404(FixedChargeCalc, id=charge_id, user=request.user, is_paid=False,
                                   send_notification=True)

        if not charge.total_charge_month or charge.total_charge_month <= 0:
            return HttpResponse("مبلغ شارژ نامعتبر است.", status=400)

        total_fix_charge = charge.total_charge_month
        charge.save()
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
def verify_pay_fix(request: HttpRequest):
    charge_id = request.GET.get('charge_id')
    if not charge_id:
        return render(request, 'payment_done.html', {
            'error': 'شناسه شارژ ارسال نشده است.'
        })

    payment_charge = get_object_or_404(FixedChargeCalc, id=charge_id, user=request.user, is_paid=False)

    if not payment_charge:
        return JsonResponse({"error": "FixedChargeCalc not found"}, status=404)

    total_fix_charge = payment_charge.total_charge_month
    payment_charge.is_paid = True
    payment_charge.payment_date = timezone.now()
    payment_charge.save()

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
                    payment_charge.transaction_reference = req_data['data']['ref_id']
                    payment_charge.save()

                    content_type = ContentType.objects.get_for_model(payment_charge)
                    Fund.objects.create(
                        content_type=content_type,
                        object_id=payment_charge.id,
                        debtor_amount=payment_charge.total_charge_month,
                        creditor_amount=0,
                        payment_date=payment_charge.payment_date,
                        payment_description=f"{payment_charge.charge_name} - {payment_charge.user.full_name}",
                    )

                    return render(request, 'payment_done.html', {
                        'success': f'تراکنش شما با کد پیگیری {ref_str} با موفقیت انجام و پرداخت شارژ شما ثبت گردید. سپاس از شما'
                    })
                elif t_status == 101:
                    return render(request, 'payment_done.html', {
                        'info': 'این تراکنش قبلا ثبت شده است'
                    })
                else:
                    return render(request, 'payment_done.html', {
                        'error': str(req_data['data']['message'])
                    })
            else:
                e_code = req_data['errors'].get('code')
                e_message = req_data['errors'].get('message')
                return render(request, 'payment_done.html', {
                    'error': f"Error code: {e_code}, Message: {e_message}"
                })
        except Exception as e:
            return render(request, 'payment_done.html', {
                'error': f"An error occurred: {str(e)}"
            })

    else:
        payment_charge.is_paid = False
        payment_charge.save()
        return redirect('user_fixed_charges')


# ============================================ Area Charge payment =================

@login_required()
def request_pay_area(request: HttpRequest, charge_id):
    if not request.user.is_authenticated:
        return redirect('login')  # Ensure the user is logged in

    try:
        charge = get_object_or_404(AreaChargeCalc, id=charge_id, user=request.user, is_paid=False,
                                   send_notification=True)

        if not charge.total_charge_month or charge.total_charge_month <= 0:
            return HttpResponse("مبلغ شارژ نامعتبر است.", status=400)

        total_area_charge = charge.total_charge_month
        charge.save()
        callback_url = f"{CallbackURLArea}?charge_id={charge.id}"  # اضافه کردن charge_id

        req_data = {
            "merchant_id": MERCHANT,  # Ensure MERCHANT is defined
            "amount": total_area_charge * 10,
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
        return HttpResponse("Charge not found.", status=404)
    except requests.RequestException as e:
        return HttpResponse(f"Payment request failed: {str(e)}", status=500)


@login_required()
def verify_pay_area(request: HttpRequest):
    charge_id = request.GET.get('charge_id')
    if not charge_id:
        return render(request, 'payment_done.html', {
            'error': 'شناسه شارژ ارسال نشده است.'
        })

    payment_charge = get_object_or_404(AreaChargeCalc, id=charge_id, user=request.user, is_paid=False)

    if not payment_charge:
        return JsonResponse({"error": "FixedChargeCalc not found"}, status=404)

    total_area_charge = payment_charge.total_charge_month
    payment_charge.is_paid = True
    payment_charge.payment_date = timezone.now()
    payment_charge.save()

    t_authority = request.GET.get('Authority')

    if request.GET.get('Status') == 'OK':
        req_header = {"accept": "application/json", "content-type": "application/json"}
        req_data = {
            "merchant_id": MERCHANT,
            "amount": total_area_charge * 10,
            "authority": t_authority
        }

        try:
            req = requests.post(url=ZP_API_VERIFY, data=json.dumps(req_data), headers=req_header)
            req_data = req.json()

            if not req_data.get('errors'):
                t_status = req_data['data']['code']
                if t_status == 100:
                    ref_str = req_data['data']['ref_id']
                    payment_charge.transaction_reference = req_data['data']['ref_id']
                    payment_charge.save()
                    content_type = ContentType.objects.get_for_model(payment_charge)
                    Fund.objects.create(
                        content_type=content_type,
                        object_id=payment_charge.id,
                        debtor_amount=payment_charge.total_charge_month,
                        creditor_amount=0,
                        payment_date=payment_charge.payment_date,
                        payment_description=f"{payment_charge.charge_name} - {payment_charge.user.full_name}",
                    )
                    return render(request, 'payment_done.html', {
                        'success': f'تراکنش شما با کد پیگیری {ref_str} با موفقیت انجام و پرداخت شارژ شما ثبت گردید. سپاس از شما'
                    })
                elif t_status == 101:
                    return render(request, 'payment_done.html', {
                        'info': 'این تراکنش قبلا ثبت شده است'
                    })
                else:
                    return render(request, 'payment_done.html', {
                        'error': str(req_data['data']['message'])
                    })
            else:
                e_code = req_data['errors'].get('code')
                e_message = req_data['errors'].get('message')
                return render(request, 'payment_done.html', {
                    'error': f"Error code: {e_code}, Message: {e_message}"
                })
        except Exception as e:
            return render(request, 'payment_done.html', {
                'error': f"An error occurred: {str(e)}"
            })

    else:
        payment_charge.is_paid = False
        payment_charge.save()
        return redirect('user_fixed_charges')


# ============================================ Person Charge payment =================

@login_required()
def request_pay_person(request: HttpRequest, charge_id):
    if not request.user.is_authenticated:
        return redirect('login')  # Ensure the user is logged in

    try:
        charge = get_object_or_404(PersonChargeCalc, id=charge_id, user=request.user, is_paid=False,
                                   send_notification=True)

        if not charge.total_charge_month or charge.total_charge_month <= 0:
            return HttpResponse("مبلغ شارژ نامعتبر است.", status=400)

        total_person_charge = charge.total_charge_month
        charge.save()
        callback_url = f"{CallbackURLPerson}?charge_id={charge.id}"  # اضافه کردن charge_id

        req_data = {
            "merchant_id": MERCHANT,  # Ensure MERCHANT is defined
            "amount": total_person_charge * 10,
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
        return HttpResponse("Charge not found.", status=404)
    except requests.RequestException as e:
        return HttpResponse(f"Payment request failed: {str(e)}", status=500)


@login_required()
def verify_pay_person(request: HttpRequest):
    charge_id = request.GET.get('charge_id')
    if not charge_id:
        return render(request, 'payment_done.html', {
            'error': 'شناسه شارژ ارسال نشده است.'
        })

    payment_charge = get_object_or_404(PersonChargeCalc, id=charge_id, user=request.user, is_paid=False)

    if not payment_charge:
        return JsonResponse({"error": "FixedChargeCalc not found"}, status=404)

    total_person_charge = payment_charge.total_charge_month
    payment_charge.is_paid = True
    payment_charge.payment_date = timezone.now()
    payment_charge.save()

    t_authority = request.GET.get('Authority')

    if request.GET.get('Status') == 'OK':
        req_header = {"accept": "application/json", "content-type": "application/json"}
        req_data = {
            "merchant_id": MERCHANT,
            "amount": total_person_charge * 10,
            "authority": t_authority
        }

        try:
            req = requests.post(url=ZP_API_VERIFY, data=json.dumps(req_data), headers=req_header)
            req_data = req.json()

            if not req_data.get('errors'):
                t_status = req_data['data']['code']

                if t_status == 100:
                    ref_str = req_data['data']['ref_id']
                    payment_charge.transaction_reference = req_data['data']['ref_id']
                    payment_charge.save()
                    content_type = ContentType.objects.get_for_model(payment_charge)
                    Fund.objects.create(
                        content_type=content_type,
                        object_id=payment_charge.id,
                        debtor_amount=payment_charge.total_charge_month,
                        creditor_amount=0,
                        payment_date=payment_charge.payment_date,
                        payment_description=f"{payment_charge.charge_name} - {payment_charge.user.full_name}",
                    )
                    return render(request, 'payment_done.html', {
                        'success': f'تراکنش شما با کد پیگیری {ref_str} با موفقیت انجام و پرداخت شارژ شما ثبت گردید. سپاس از شما'
                    })
                elif t_status == 101:
                    return render(request, 'payment_done.html', {
                        'info': 'این تراکنش قبلا ثبت شده است'
                    })
                else:
                    return render(request, 'payment_done.html', {
                        'error': str(req_data['data']['message'])
                    })
            else:
                e_code = req_data['errors'].get('code')
                e_message = req_data['errors'].get('message')
                return render(request, 'payment_done.html', {
                    'error': f"Error code: {e_code}, Message: {e_message}"
                })
        except Exception as e:
            return render(request, 'payment_done.html', {
                'error': f"An error occurred: {str(e)}"
            })

    else:
        payment_charge.is_paid = False
        payment_charge.save()
        return redirect('user_fixed_charges')


# ================================== Person Fix charges ============================
@login_required()
def request_pay_fix_person(request: HttpRequest, charge_id):
    if not request.user.is_authenticated:
        return redirect('login')  # Ensure the user is logged in

    try:
        charge = get_object_or_404(FixPersonChargeCalc, id=charge_id, user=request.user, is_paid=False,
                                   send_notification=True)

        if not charge.total_charge_month or charge.total_charge_month <= 0:
            return HttpResponse("مبلغ شارژ نامعتبر است.", status=400)

        total_person_charge = charge.total_charge_month
        charge.save()
        callback_url = f"{CallbackURLFixPerson}?charge_id={charge.id}"  # اضافه کردن charge_id
        print(total_person_charge)
        req_data = {
            "merchant_id": MERCHANT,  # Ensure MERCHANT is defined
            "amount": total_person_charge * 10,
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
        return HttpResponse("Charge not found.", status=404)
    except requests.RequestException as e:
        return HttpResponse(f"Payment request failed: {str(e)}", status=500)


@login_required()
def verify_pay_fix_person(request: HttpRequest):
    charge_id = request.GET.get('charge_id')
    if not charge_id:
        return render(request, 'payment_done.html', {
            'error': 'شناسه شارژ ارسال نشده است.'
        })

    payment_charge = get_object_or_404(FixPersonChargeCalc, id=charge_id, user=request.user, is_paid=False)

    if not payment_charge:
        return JsonResponse({"error": "FixedChargeCalc not found"}, status=404)

    total_person_charge = payment_charge.total_charge_month
    print(f'verify_total_person_charge: {total_person_charge}')
    payment_charge.is_paid = True
    payment_charge.payment_date = timezone.now()
    payment_charge.save()

    t_authority = request.GET.get('Authority')

    if request.GET.get('Status') == 'OK':
        req_header = {"accept": "application/json", "content-type": "application/json"}
        req_data = {
            "merchant_id": MERCHANT,
            "amount": total_person_charge * 10,
            "authority": t_authority
        }

        try:
            req = requests.post(url=ZP_API_VERIFY, data=json.dumps(req_data), headers=req_header)
            req_data = req.json()

            if not req_data.get('errors'):
                t_status = req_data['data']['code']
                if t_status == 100:
                    ref_str = req_data['data']['ref_id']
                    payment_charge.transaction_reference = req_data['data']['ref_id']
                    payment_charge.save()
                    content_type = ContentType.objects.get_for_model(payment_charge)
                    Fund.objects.create(
                        content_type=content_type,
                        object_id=payment_charge.id,
                        debtor_amount=payment_charge.total_charge_month,
                        creditor_amount=0,
                        payment_date=payment_charge.payment_date,
                        payment_description=f"{payment_charge.charge_name} - {payment_charge.user.full_name}",
                    )
                    return render(request, 'payment_done.html', {
                        'success': f'تراکنش شما با کد پیگیری {ref_str} با موفقیت انجام و پرداخت شارژ شما ثبت گردید. سپاس از شما'
                    })
                elif t_status == 101:
                    return render(request, 'payment_done.html', {
                        'info': 'این تراکنش قبلا ثبت شده است'
                    })
                else:
                    return render(request, 'payment_done.html', {
                        'error': str(req_data['data']['message'])
                    })
            else:
                e_code = req_data['errors'].get('code')
                e_message = req_data['errors'].get('message')
                return render(request, 'payment_done.html', {
                    'error': f"Error code: {e_code}, Message: {e_message}"
                })
        except Exception as e:
            return render(request, 'payment_done.html', {
                'error': f"An error occurred: {str(e)}"
            })

    else:
        payment_charge.is_paid = False
        payment_charge.save()
        return redirect('user_fixed_charges')


# ================================== Area Fix charges ============================
@login_required()
def request_pay_fix_area(request: HttpRequest, charge_id):
    if not request.user.is_authenticated:
        return redirect('login')  # Ensure the user is logged in

    try:
        charge = get_object_or_404(FixAreaChargeCalc, id=charge_id, user=request.user, is_paid=False,
                                   send_notification=True)

        if not charge.total_charge_month or charge.total_charge_month <= 0:
            return HttpResponse("مبلغ شارژ نامعتبر است.", status=400)

        total_person_charge = charge.total_charge_month
        print(total_person_charge)
        callback_url = f"{CallbackURLFixArea}?charge_id={charge.id}"  # اضافه کردن charge_id

        req_data = {
            "merchant_id": MERCHANT,  # Ensure MERCHANT is defined
            "amount": total_person_charge * 10,
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
        return HttpResponse("Charge not found.", status=404)
    except requests.RequestException as e:
        return HttpResponse(f"Payment request failed: {str(e)}", status=500)


@login_required()
def verify_pay_fix_area(request: HttpRequest):
    charge_id = request.GET.get('charge_id')
    if not charge_id:
        return render(request, 'payment_done.html', {
            'error': 'شناسه شارژ ارسال نشده است.'
        })

    payment_charge = get_object_or_404(FixAreaChargeCalc, id=charge_id, user=request.user, is_paid=False)

    if not payment_charge:
        return JsonResponse({"error": "FixedChargeCalc not found"}, status=404)

    total_person_charge = payment_charge.total_charge_month
    payment_charge.is_paid = True
    payment_charge.payment_date = timezone.now()
    payment_charge.save()

    t_authority = request.GET.get('Authority')

    if request.GET.get('Status') == 'OK':
        req_header = {"accept": "application/json", "content-type": "application/json"}
        req_data = {
            "merchant_id": MERCHANT,
            "amount": total_person_charge * 10,
            "authority": t_authority
        }

        try:
            req = requests.post(url=ZP_API_VERIFY, data=json.dumps(req_data), headers=req_header)
            req_data = req.json()

            if not req_data.get('errors'):
                t_status = req_data['data']['code']
                if t_status == 100:
                    ref_str = req_data['data']['ref_id']
                    payment_charge.transaction_reference = req_data['data']['ref_id']
                    payment_charge.save()
                    content_type = ContentType.objects.get_for_model(payment_charge)
                    Fund.objects.create(
                        content_type=content_type,
                        object_id=payment_charge.id,
                        debtor_amount=payment_charge.total_charge_month,
                        creditor_amount=0,
                        payment_date=payment_charge.payment_date,
                        payment_description=f"{payment_charge.charge_name} - {payment_charge.user.full_name}",
                    )
                    return render(request, 'payment_done.html', {
                        'success': f'تراکنش شما با کد پیگیری {ref_str} با موفقیت انجام و پرداخت شارژ شما ثبت گردید. سپاس از شما'
                    })
                elif t_status == 101:
                    return render(request, 'payment_done.html', {
                        'info': 'این تراکنش قبلا ثبت شده است'
                    })
                else:
                    return render(request, 'payment_done.html', {
                        'error': str(req_data['data']['message'])
                    })
            else:
                e_code = req_data['errors'].get('code')
                e_message = req_data['errors'].get('message')
                return render(request, 'payment_done.html', {
                    'error': f"Error code: {e_code}, Message: {e_message}"
                })
        except Exception as e:
            return render(request, 'payment_done.html', {
                'error': f"An error occurred: {str(e)}"
            })

    else:
        payment_charge.is_paid = False
        payment_charge.save()
        return redirect('user_fixed_charges')

# ================================== Person Area charges ============================
@login_required()
def request_pay_person_area(request: HttpRequest, charge_id):
    if not request.user.is_authenticated:
        return redirect('login')  # Ensure the user is logged in

    try:
        charge = get_object_or_404(ChargeByPersonAreaCalc, id=charge_id, user=request.user, is_paid=False,
                                   send_notification=True)

        if not charge.total_charge_month or charge.total_charge_month <= 0:
            return HttpResponse("مبلغ شارژ نامعتبر است.", status=400)

        total_person_charge = charge.total_charge_month
        print(total_person_charge)
        callback_url = f"{CallbackURLPersonArea}?charge_id={charge.id}"  # اضافه کردن charge_id

        req_data = {
            "merchant_id": MERCHANT,  # Ensure MERCHANT is defined
            "amount": total_person_charge * 10,
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
        return HttpResponse("Charge not found.", status=404)
    except requests.RequestException as e:
        return HttpResponse(f"Payment request failed: {str(e)}", status=500)


@login_required()
def verify_pay_person_area(request: HttpRequest):
    charge_id = request.GET.get('charge_id')
    if not charge_id:
        return render(request, 'payment_done.html', {
            'error': 'شناسه شارژ ارسال نشده است.'
        })

    payment_charge = get_object_or_404(ChargeByPersonAreaCalc, id=charge_id, user=request.user, is_paid=False)

    if not payment_charge:
        return JsonResponse({"error": "FixedChargeCalc not found"}, status=404)

    total_person_charge = payment_charge.total_charge_month
    payment_charge.is_paid = True
    payment_charge.payment_date = timezone.now()
    payment_charge.save()

    t_authority = request.GET.get('Authority')

    if request.GET.get('Status') == 'OK':
        req_header = {"accept": "application/json", "content-type": "application/json"}
        req_data = {
            "merchant_id": MERCHANT,
            "amount": total_person_charge * 10,
            "authority": t_authority
        }

        try:
            req = requests.post(url=ZP_API_VERIFY, data=json.dumps(req_data), headers=req_header)
            req_data = req.json()

            if not req_data.get('errors'):
                t_status = req_data['data']['code']
                if t_status == 100:
                    ref_str = req_data['data']['ref_id']
                    payment_charge.transaction_reference = req_data['data']['ref_id']
                    payment_charge.save()
                    content_type = ContentType.objects.get_for_model(payment_charge)
                    Fund.objects.create(
                        content_type=content_type,
                        object_id=payment_charge.id,
                        debtor_amount=payment_charge.total_charge_month,
                        creditor_amount=0,
                        payment_date=payment_charge.payment_date,
                        payment_description=f"{payment_charge.charge_name} - {payment_charge.user.full_name}",
                    )
                    return render(request, 'payment_done.html', {
                        'success': f'تراکنش شما با کد پیگیری {ref_str} با موفقیت انجام و پرداخت شارژ شما ثبت گردید. سپاس از شما'
                    })
                elif t_status == 101:
                    return render(request, 'payment_done.html', {
                        'info': 'این تراکنش قبلا ثبت شده است'
                    })
                else:
                    return render(request, 'payment_done.html', {
                        'error': str(req_data['data']['message'])
                    })
            else:
                e_code = req_data['errors'].get('code')
                e_message = req_data['errors'].get('message')
                return render(request, 'payment_done.html', {
                    'error': f"Error code: {e_code}, Message: {e_message}"
                })
        except Exception as e:
            return render(request, 'payment_done.html', {
                'error': f"An error occurred: {str(e)}"
            })

    else:
        payment_charge.is_paid = False
        payment_charge.save()
        return redirect('user_fixed_charges')


# ==================================  Fix Person Area charges ============================
@login_required()
def request_pay_fix_person_area(request: HttpRequest, charge_id):
    if not request.user.is_authenticated:
        return redirect('login')  # Ensure the user is logged in

    try:
        charge = get_object_or_404(ChargeByFixPersonAreaCalc, id=charge_id, user=request.user, is_paid=False,
                                   send_notification=True)

        if not charge.total_charge_month or charge.total_charge_month <= 0:
            return HttpResponse("مبلغ شارژ نامعتبر است.", status=400)

        total_person_charge = charge.total_charge_month
        print(total_person_charge)
        callback_url = f"{CallbackURLFixPersonArea}?charge_id={charge.id}"  # اضافه کردن charge_id

        req_data = {
            "merchant_id": MERCHANT,  # Ensure MERCHANT is defined
            "amount": total_person_charge * 10,
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
        return HttpResponse("Charge not found.", status=404)
    except requests.RequestException as e:
        return HttpResponse(f"Payment request failed: {str(e)}", status=500)


@login_required()
def verify_pay_fix_person_area(request: HttpRequest):
    charge_id = request.GET.get('charge_id')
    if not charge_id:
        return render(request, 'payment_done.html', {
            'error': 'شناسه شارژ ارسال نشده است.'
        })

    payment_charge = get_object_or_404(ChargeByFixPersonAreaCalc, id=charge_id, user=request.user, is_paid=False)

    if not payment_charge:
        return JsonResponse({"error": "FixedChargeCalc not found"}, status=404)

    total_person_charge = payment_charge.total_charge_month
    payment_charge.is_paid = True
    payment_charge.payment_date = timezone.now()
    payment_charge.save()

    t_authority = request.GET.get('Authority')

    if request.GET.get('Status') == 'OK':
        req_header = {"accept": "application/json", "content-type": "application/json"}
        req_data = {
            "merchant_id": MERCHANT,
            "amount": total_person_charge * 10,
            "authority": t_authority
        }

        try:
            req = requests.post(url=ZP_API_VERIFY, data=json.dumps(req_data), headers=req_header)
            req_data = req.json()

            if not req_data.get('errors'):
                t_status = req_data['data']['code']
                if t_status == 100:
                    ref_str = req_data['data']['ref_id']
                    payment_charge.transaction_reference = req_data['data']['ref_id']
                    payment_charge.save()
                    content_type = ContentType.objects.get_for_model(payment_charge)
                    Fund.objects.create(
                        content_type=content_type,
                        object_id=payment_charge.id,
                        debtor_amount=payment_charge.total_charge_month,
                        creditor_amount=0,
                        payment_date=payment_charge.payment_date,
                        payment_description=f"{payment_charge.charge_name} - {payment_charge.user.full_name}",
                    )
                    return render(request, 'payment_done.html', {
                        'success': f'تراکنش شما با کد پیگیری {ref_str} با موفقیت انجام و پرداخت شارژ شما ثبت گردید. سپاس از شما'
                    })
                elif t_status == 101:
                    return render(request, 'payment_done.html', {
                        'info': 'این تراکنش قبلا ثبت شده است'
                    })
                else:
                    return render(request, 'payment_done.html', {
                        'error': str(req_data['data']['message'])
                    })
            else:
                e_code = req_data['errors'].get('code')
                e_message = req_data['errors'].get('message')
                return render(request, 'payment_done.html', {
                    'error': f"Error code: {e_code}, Message: {e_message}"
                })
        except Exception as e:
            return render(request, 'payment_done.html', {
                'error': f"An error occurred: {str(e)}"
            })

    else:
        payment_charge.is_paid = False
        payment_charge.save()
        return redirect('user_fixed_charges')


# ==================================  Fix Person Area charges ============================
@login_required()
def request_pay_fix_variable(request: HttpRequest, charge_id):
    if not request.user.is_authenticated:
        return redirect('login')  # Ensure the user is logged in

    try:
        charge = get_object_or_404(ChargeFixVariableCalc, id=charge_id, user=request.user, is_paid=False,
                                   send_notification=True)

        if not charge.total_charge_month or charge.total_charge_month <= 0:
            return HttpResponse("مبلغ شارژ نامعتبر است.", status=400)

        total_person_charge = charge.total_charge_month
        print(total_person_charge)
        callback_url = f"{CallbackURLFixVariable}?charge_id={charge.id}"  # اضافه کردن charge_id

        req_data = {
            "merchant_id": MERCHANT,  # Ensure MERCHANT is defined
            "amount": total_person_charge * 10,
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
        return HttpResponse("Charge not found.", status=404)
    except requests.RequestException as e:
        return HttpResponse(f"Payment request failed: {str(e)}", status=500)


@login_required()
def verify_pay_fix_variable(request: HttpRequest):
    charge_id = request.GET.get('charge_id')
    if not charge_id:
        return render(request, 'payment_done.html', {
            'error': 'شناسه شارژ ارسال نشده است.'
        })

    payment_charge = get_object_or_404(ChargeFixVariableCalc, id=charge_id, user=request.user, is_paid=False)

    if not payment_charge:
        return JsonResponse({"error": "FixedChargeCalc not found"}, status=404)

    total_person_charge = payment_charge.total_charge_month
    payment_charge.is_paid = True
    payment_charge.payment_date = timezone.now()
    payment_charge.save()

    t_authority = request.GET.get('Authority')

    if request.GET.get('Status') == 'OK':
        req_header = {"accept": "application/json", "content-type": "application/json"}
        req_data = {
            "merchant_id": MERCHANT,
            "amount": total_person_charge * 10,
            "authority": t_authority
        }

        try:
            req = requests.post(url=ZP_API_VERIFY, data=json.dumps(req_data), headers=req_header)
            req_data = req.json()

            if not req_data.get('errors'):
                t_status = req_data['data']['code']
                if t_status == 100:
                    ref_str = req_data['data']['ref_id']
                    payment_charge.transaction_reference = req_data['data']['ref_id']
                    payment_charge.save()
                    content_type = ContentType.objects.get_for_model(payment_charge)
                    Fund.objects.create(
                        content_type=content_type,
                        object_id=payment_charge.id,
                        debtor_amount=payment_charge.total_charge_month,
                        creditor_amount=0,
                        payment_date=payment_charge.payment_date,
                        payment_description=f"{payment_charge.charge_name} - {payment_charge.user.full_name}",
                    )
                    return render(request, 'payment_done.html', {
                        'success': f'تراکنش شما با کد پیگیری {ref_str} با موفقیت انجام و پرداخت شارژ شما ثبت گردید. سپاس از شما'
                    })
                elif t_status == 101:
                    return render(request, 'payment_done.html', {
                        'info': 'این تراکنش قبلا ثبت شده است'
                    })
                else:
                    return render(request, 'payment_done.html', {
                        'error': str(req_data['data']['message'])
                    })
            else:
                e_code = req_data['errors'].get('code')
                e_message = req_data['errors'].get('message')
                return render(request, 'payment_done.html', {
                    'error': f"Error code: {e_code}, Message: {e_message}"
                })
        except Exception as e:
            return render(request, 'payment_done.html', {
                'error': f"An error occurred: {str(e)}"
            })

    else:
        payment_charge.is_paid = False
        payment_charge.save()
        return redirect('user_fixed_charges')