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


@register.filter(name='show_jalali_date')
def show_jalali_date(value):
    if value is None:
        return ''
    try:
        # Convert to timezone-aware datetime in the desired timezone
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone=pytz.timezone('Asia/Tehran'))
        else:
            value = value.astimezone(pytz.timezone('Asia/Tehran'))

        # Convert the Gregorian datetime to Jalali datetime
        jalali_datetime = jdatetime.datetime.fromgregorian(datetime=value)

        # Adjust weekday to match Persian week (Saturday as 0)
        weekday = WEEKDAYS[jalali_datetime.weekday()]
        month = MONTHS[jalali_datetime.month - 1]  # Index starts from 0 for MONTHS list

        # Format the date and time manually using Persian names
        formatted_date = f'{weekday} {jalali_datetime.day} {month} {jalali_datetime.year} ساعت {jalali_datetime.strftime("%H:%M:%S")}'
        return formatted_date
    except (ValueError, TypeError):
        return ''  # Return empty string if there's an error in conversion


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
    if value is None:
        return ''
    try:
        # Ensure the input is a datetime object
        if isinstance(value, jdatetime.date):  # If it's already a Jalali date, no need to convert
            jalali_datetime = value
        else:
            # Convert to datetime if it's not already a datetime object
            if isinstance(value,
                          datetime.date):  # If it's a datetime.date (without time), turn it into a datetime object
                value = datetime.datetime.combine(value, datetime.datetime.min.time())

            # Make sure the datetime object is timezone-aware
            if timezone.is_naive(value):
                value = timezone.make_aware(value, timezone=pytz.timezone('Asia/Tehran'))
            else:
                value = value.astimezone(pytz.timezone('Asia/Tehran'))

            # Convert the Gregorian datetime to Jalali datetime
            jalali_datetime = jdatetime.date.fromgregorian(datetime=value)

        # Format the Jalali date as YYYY/MM/DD
        formatted_date = jalali_datetime.strftime('%Y/%m/%d')
        return formatted_date
    except (ValueError, TypeError):
        return ''  # Return empty string if there's an error in conversion


@register.filter(name='three_digit_currency')
def three_digit_currency(value: int):
    if value is None:
        return '0'  # You can customize this to return whatever you'd like for None values
    return '{:,}'.format(value)


@register.filter(name='to_jalali')
def to_jalali(value):
    if value:
        return jdatetime.date.fromgregorian(date=value).strftime('%Y/%m/%d')
    return value
