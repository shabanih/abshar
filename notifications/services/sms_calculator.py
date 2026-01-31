import math

SMS_CHUNK_SIZE = 70  # فارسی

def calculate_sms_count(message: str) -> int:
    if not message:
        return 0
    length = len(message)
    return math.ceil(length / SMS_CHUNK_SIZE)
