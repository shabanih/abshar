from kavenegar import KavenegarAPI, APIException, HTTPException

from absharProject.settings import Kavenegar_API
from user_app.models import User


def send_notify_user_by_sms(mobile, name, charge_title):
    mobile = [mobile]
    name = name or "کاربر گرامی"
    charge_title = charge_title or "شارژ"

    try:
        api = KavenegarAPI(Kavenegar_API)

        params = {
            'mobile': mobile,
            'token10': name,   # نام شخص
            'token': charge_title,       # نام شارژ
            'template': 'raya',
            'type': 'sms'
        }

        return api.verify_lookup(params)

    except APIException as e:
        print(f"APIException: {e}")
        return {"error": str(e)}

    except HTTPException as e:
        print(f"HTTPException: {e}")
        return {"error": str(e)}




# def send_notify_user_by_sms(unified_charges, message):
    # """
    # ارسال پیامک به مجموعه‌ای از UnifiedChargeها
    # """
    # mobiles = []
    # names = []
    #
    # for uc in unified_charges:
    #     mobile = uc.get_mobile()
    #     if mobile:
    #         mobiles.append(mobile)
    #         # می‌توانید نام را از مستاجر یا مالک بگیرید
    #         renter = uc.unit.get_active_renter()
    #         if renter and renter.renter_name:
    #             names.append(renter.renter_name)
    #         else:
    #             names.append(uc.unit.owner_name)
    #
    # if not mobiles:
    #     return {"error": "شماره موبایلی یافت نشد"}
    #
    # try:
    #     api = KavenegarAPI(Kavenegar_API)
    #     # ارسال همه شماره‌ها با یک قالب
    #     response = api.verify_lookup({
    #         'mobile': mobiles,
    #         'token10': names,  # مثلا نام گیرنده در قالب
    #         'template': 'raya',  # نام قالب
    #         'type': 'sms'
    #     })
    #     return {"success": True, "response": response}
    # except APIException as e:
    #     return {"success": False, "error": str(e)}
    # except HTTPException as e:
    #     return {"success": False, "error": str(e)}


def send_sms_to_user(mobile, message, full_name, otp=None):
    mobile = str(mobile)  # مطمئن شو عدد به رشته تبدیل شده
    full_name = str(full_name)
    message = str(message)
    text = '.'

    try:
        api = KavenegarAPI(Kavenegar_API)

        params = {
            'receptor': [mobile],  # List of strings for mobile numbers

            'token': full_name,
            'token10': message,
            # 'token20': message,
            'template': 'smsToUser',  # Template name (if using a template)
            'message': otp,  # Custom message
            'type': 'sms'
        }

        # Send the message
        response = api.verify_lookup(params)
        return response
    except User.DoesNotExist:
        print("User not found.")
        return {"error": "User not found"}
    except APIException as e:
        print(f"APIException: {e}")
        return {"error": "APIException", "message": str(e)}
    except HTTPException as e:
        print(f"HTTPException: {e}")
        return {"error": "HTTPException", "message": str(e)}
