import datetime

import jdatetime
import pytz
from django import template
from django.utils import timezone

register = template.Library()


@register.filter(name='cut')
def cut(value, arg):
    return value.replace(arg, '')


# @register.filter(name='show_jalali_date')
# def show_jalali_date(value):
#     return jdate.fromgregorian(date=value).strftime('%Y/%m/%d')

WEEKDAYS = ['شنبه', 'یک‌شنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه']
MONTHS = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
          'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']


# @register.filter(name='show_jalali_date')
# def show_jalali_date(value):
#     if value is None:
#         return ''
#     try:
#         # Convert to timezone-aware datetime in the desired timezone
#         if timezone.is_naive(value):
#             value = timezone.make_aware(value, timezone=pytz.timezone('Asia/Tehran'))
#         else:
#             value = value.astimezone(pytz.timezone('Asia/Tehran'))
#
#         # Convert the Gregorian datetime to Jalali datetime
#         jalali_datetime = jdatetime.datetime.fromgregorian(datetime=value)
#
#         # Adjust weekday to match Persian week (Saturday as 0)
#         weekday = WEEKDAYS[jalali_datetime.weekday()]
#         month = MONTHS[jalali_datetime.month - 1]  # Index starts from 0 for MONTHS list
#
#         # Format the date and time manually using Persian names
#         formatted_date = f'{weekday} {jalali_datetime.day} {month} {jalali_datetime.year} ساعت {jalali_datetime.strftime("%H:%M:%S")}'
#         return formatted_date
#     except (ValueError, TypeError):
#         return ''  # Return empty string if there's an error in conversion


@register.filter(name='show_jalali_date_only')
def show_jalali_date(value):
    if value is None:
        return ''
    # Convert the Gregorian datetime to Jalali datetime
    jalali_datetime = jdatetime.datetime.fromgregorian(datetime=value)

    # Get the Persian weekday and month name
    weekday = WEEKDAYS[jalali_datetime.weekday()]
    month = MONTHS[jalali_datetime.month - 1]  # Index starts from 0 for MONTHS list

    # Format the date manually using Persian names without time
    formatted_date = f'{weekday} {jalali_datetime.day} {month} {jalali_datetime.year}'
    return formatted_date


@register.filter(name='show_jalali')
def show_jalali(value):
    if not value:
        return ''
    if isinstance(value, datetime.datetime):
        jalali = jdatetime.datetime.fromgregorian(datetime=value)
    elif isinstance(value, datetime.date):
        jalali = jdatetime.date.fromgregorian(date=value)
    else:
        return ''
    return f'{jalali.year}-{jalali.month:02d}-{jalali.day:02d}'


@register.filter(name='three_digit_currency')
def three_digit_currency(value):
    try:
        return '{:,}'.format(int(value))
    except (ValueError, TypeError):
        return '0'


@register.filter(name='four_digit_cart')
def four_digit_cart(value):
    try:
        # Convert the value to a string
        value_str = str(int(value))
    except (ValueError, TypeError):
        return value  # Return the original value if conversion fails

        # Group digits in chunks of 4
    grouped = ' '.join([value_str[i:i + 4] for i in range(0, len(value_str), 4)])

    # Prepend Left-to-Right Mark to ensure correct display in RTL contexts
    return '\u200E' + grouped



    # if value is None:
    #     return '0'
    # # value_str = str(value)
    # # Reverse the string for grouping
    # reversed_str = value[::-1]
    # # Group digits in chunks of 4
    # chunks = [reversed_str[i:i + 4] for i in range(0, len(reversed_str), 4)]
    # # Join chunks with spaces and reverse back
    # formatted_value = ' '.join(chunks)[::-1]
    # # Prepend LRM to ensure correct display in RTL
    # return '\u200E' + formatted_value