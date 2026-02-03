from decimal import Decimal

from django.db.models import Q, Sum

from admin_panel.models import UnifiedCharge, Announcement, MessageToUser, MessageReadStatus, SmsCredit
from user_app.models import MyHouse, Unit


def current_middle_house(request):
    if not request.user.is_authenticated:
        return {}

    middle_house = MyHouse.objects.filter(
        residents=request.user,
        is_active=True
    ).order_by('-created_at').first()

    return {'middle_house': middle_house}


def current_house(request):
    if not request.user.is_authenticated:
        return {}

    houses = MyHouse.objects.filter(
        Q(units__user=request.user) |
        Q(units__renters__user=request.user, units__renters__renter_is_active=True)
    ).distinct().order_by('-created_at')

    return {
        'house': houses.first(),
        'houses': houses,  # اگر بعداً لیست هم خواستی
    }


def user_header_notifications(request):
    if not request.user.is_authenticated:
        return {
            'new_charges_count': 0,
            'new_messages_count': 0,
        }
    # واحدهایی که کاربر مالک یا مستاجر فعال آن است
    # user_units = Unit.objects.filter(
    #     is_active=True
    # ).filter(
    #     Q(user=request.user) |  # مالک
    #     Q(renters__user=request.user, renters__renter_is_active=True)  # مستاجر فعال
    # ).distinct()
    # # شارژهای پرداخت‌نشده
    # # new_user_charges_count = UnifiedCharge.objects.filter(
    # #     unit__in=user_units,
    # #     is_paid=False
    # # ).select_related('unit').count()
    #
    user_unit_ids = Unit.objects.filter(
        is_active=True
    ).filter(
        Q(user=request.user) |
        Q(renters__user=request.user,
          renters__renter_is_active=True)
    ).values_list('id', flat=True)

    new_user_charges_count = UnifiedCharge.objects.filter(
        unit__in=user_unit_ids,
        is_paid=False,
        send_notification=True
    ).count()

    # پیام‌های خوانده‌نشده
    new_user_messages_count = MessageReadStatus.objects.filter(
        unit__in=user_unit_ids,
        is_read=False
    ).values('message').distinct().count()

    user = request.user
    if user.is_middle_admin:
        units = (
            Unit.objects
            .filter(user__manager=user, is_active=True)
            .prefetch_related('renters')
        )
        marquee_announcements = (
            Announcement.objects
            .filter(user=user, is_active=True)
            .order_by('-created_at')[:5]
        )
    else:
        units = (
            Unit.objects
            .filter(user=user, is_active=True)
            .prefetch_related('renters')
        )
        marquee_announcements = (
            Announcement.objects
            .filter(user=user.manager, is_active=True)
            .order_by('-created_at')[:5]
        )

    return {
        'new_user_charges_count': new_user_charges_count,
        'new_user_messages_count': new_user_messages_count,
        'marquee_announcements': marquee_announcements,
    }


def middle_header_notifications(request):
    if not request.user.is_authenticated:
        return {
            'new_charges_count': 0,
            'new_messages_count': 0,
        }
    # واحدهایی که کاربر مالک یا مستاجر فعال آن است
    user_units = Unit.objects.filter(
        Q(user=request.user) |
        Q(renters__user=request.user, renters__renter_is_active=True)
    ).distinct()
    # شارژهای پرداخت‌نشده
    new_charges_count = UnifiedCharge.objects.filter(
        unit__in=user_units,
        is_paid=False
    ).count()

    # پیام‌های خوانده‌نشده
    new_messages_count = MessageReadStatus.objects.filter(
        unit__in=user_units,
        is_read=False
    ).values('message').distinct().count()

    middle_current_credit = (
            SmsCredit.objects
            .filter(user=request.user, is_paid=True)
            .aggregate(total=Sum('amount'))['total']
            or Decimal('0')
    )

    # new_announce_count = Announcement.objects.filter(
    #     unit__in=user_units,
    # ).count()

    return {
        'new_charges_count': new_charges_count,
        'new_messages_count': new_messages_count,
        'middle_current_credit': middle_current_credit,
        # 'new_announce_count': new_announce_count,
    }
