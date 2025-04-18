from random import randint

from django.utils import timezone

from absharProject.settings import Kavenegar_API
from kavenegar import KavenegarAPI, APIException, HTTPException

from user_app.models import User


def get_random_otp():
    """Generate a random 4-digit OTP."""
    return randint(10000, 99999)


def send_otp(mobile, otp):
    mobile = [mobile]
    try:
        api = KavenegarAPI(Kavenegar_API)
        params = {
            'sender': '2000500666',  # Optional sender number
            'receptor': mobile,  # List of strings for mobile numbers
            'token': otp,  # Use the OTP generated outside this function
            'template': 'boshgardi',  # Template name
            'type': 'sms',
            'message': 'your Otp is: '.format(otp)
        }
        print("Sending OTP:", otp)  #
        response = api.verify_lookup(params)

        return response
    except APIException as e:
        print(f"APIException: {e}")
    except HTTPException as e:
        print(f"HTTPException: {e}")


def check_otp_expiration(mobile):
    try:
        user = User.objects.get(mobile=mobile)
        otp_time = user.otp_create_time

        # Check if otp_create_time exists
        if otp_time is None:
            return False

        now = timezone.now()
        diff_time = now - otp_time
        print(now)
        print(otp_time)
        print(diff_time)

        # Check if the difference is more than 120 seconds
        if diff_time.seconds > 120:
            return False
        return True
    except User.DoesNotExist:
        return False