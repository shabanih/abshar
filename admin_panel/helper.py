from kavenegar import KavenegarAPI, APIException, HTTPException
from absharProject.settings import Kavenegar_API
from user_app.models import User


def send_notify_user_by_sms(mobile, name, amount):
    mobile = [mobile]
    name = name or "کاربر گرامی"
    amount = amount or "شارژ"

    try:
        api = KavenegarAPI(Kavenegar_API)

        params = {
            'receptor': mobile,
            'token10': name,   # نام شخص
            'token': amount,       # نام شارژ
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

def send_sms_to_user(mobile, message, full_name, otp=None):
    mobile = [mobile]  # مطمئن شو عدد به رشته تبدیل شده
    full_name = full_name
    message = message


    try:
        api = KavenegarAPI(Kavenegar_API)

        params = {
            'receptor': mobile,  # List of strings for mobile numbers
            'token10': full_name,
            'token': message,
            'template': 'raya',
            'type': 'sms'
        }
        print(params)

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


def send_sms_to_middle(mobile, message, full_name, otp=None):
    mobile = [mobile]  # مطمئن شو عدد به رشته تبدیل شده
    full_name = full_name
    message = message


    try:
        api = KavenegarAPI(Kavenegar_API)

        params = {
            'receptor': mobile,  # List of strings for mobile numbers
            'token10': full_name,
            'token': message,
            'template': 'raya',
            'type': 'sms'
        }
        print(params)

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
