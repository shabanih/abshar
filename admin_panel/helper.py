from kavenegar import KavenegarAPI, APIException, HTTPException

from absharProject.settings import Kavenegar_API
from user_app.models import User


def send_notify_user_by_sms(mobile, fix_charge, name, otp=None):
    mobile = [mobile]
    fix_charge = [fix_charge]
    name = [name]
    try:
        api = KavenegarAPI(Kavenegar_API)

        params = {
            'receptor': [mobile],  # List of strings for mobile numbers
            'token': fix_charge,  # OTP token
            'token10': name,
            'template': 'raya',  # Template name (if using a template)
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
