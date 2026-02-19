from decimal import Decimal

from django.core.cache import cache
from django.db.models import Q, Sum
from django.utils import timezone

from admin_panel.models import UnifiedCharge, Announcement, MessageToUser, MessageReadStatus, SmsCredit, \
    MiddleMessageReadStatus, SmsManagement, Subscription
from user_app.models import MyHouse, Unit

# def current_middle_house(request):
#     if not request.user.is_authenticated:
#         return {}
#
#     middle_house = MyHouse.objects.filter(
#         residents=request.user,
#         is_active=True
#     ).order_by('-created_at').first()
#
#     return {'middle_house': middle_house}


def current_middle_house(request):
    """
    برمی‌گرداند:
    - خانه فعال کاربر
    - اشتراک معتبر
    - تعداد کل روزها
    - روزهای مانده
    - وضعیت اشتراک
    - هشدار تمدید اشتراک (3 روز قبل یا بعد)
    """

    if not request.user.is_authenticated:
        return {}

    # ===== خانه فعال =====
    middle_house = MyHouse.objects.filter(
        residents=request.user,
        is_active=True
    ).order_by('-created_at').first()

    # ===== مقادیر پیش‌فرض =====
    current_subscription = None
    total_days = 0
    remaining_days = 0
    sub_status = "inactive"
    plan = None
    subscription_warning = False
    redirect_to_buy = False

    # ===== آخرین اشتراک =====
    last_sub = Subscription.objects.filter(user=request.user).order_by('-created_at').first()
    now = timezone.now()

    if last_sub and last_sub.end_date:
        days_remaining = (last_sub.end_date.date() - last_sub.start_date.date()).days
        current_subscription = last_sub

        # ---- Trial فعال ----
        if last_sub.is_trial and days_remaining >= 0:
            total_days = 1
            remaining_days = days_remaining
            sub_status = "trial"

        # ---- Paid فعال ----
        elif last_sub.is_paid and days_remaining >= 0:
            total_days = (last_sub.end_date.date() - last_sub.start_date.date()).days
            remaining_days = days_remaining
            sub_status = "paid"
            plan = last_sub.plan

        # ---- منقضی شده ----
        else:
            total_days = 0
            remaining_days = 0
            sub_status = "inactive"

        # هشدار 3 روزه قبل از پایان یا بعد از پایان
        if -1 <= days_remaining <= 1:
            subscription_warning = True

        # هدایت مستقیم بعد از 3 روز از پایان اشتراک
        if days_remaining < -1:
            redirect_to_buy = True

    # اگر هیچ اشتراکی وجود ندارد
    else:
        total_days = 0
        remaining_days = 0
        sub_status = "inactive"
        # هشدار 3 روزه پس از عدم اشتراک
        subscription_warning = True
        redirect_to_buy = False  # هدایت فقط بعد از 3 روز از عدم اشتراک

    return {
        "middle_house": middle_house,
        "current_subscription": current_subscription,
        "total_days": total_days,
        "remaining_days": remaining_days,
        "sub_status": sub_status,
        "plan": plan,
        "subscription_warning": subscription_warning,
        "redirect_to_buy": redirect_to_buy,
    }




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
            'new_messages_count': 0,
            'middle_current_credit': Decimal('0'),
        }

    user = request.user

    # پیام‌های خوانده‌نشده
    middle_new_messages_count = MiddleMessageReadStatus.objects.filter(
        user=user,
        is_read=False
    ).values('message').distinct().count()

    # اعتبار پیامک مدیر ساختمان
    middle_current_credit = (
            SmsCredit.objects
            .filter(user=user, is_paid=True)
            .aggregate(total=Sum('amount'))['total']
            or Decimal('0')
    )

    return {
        'middle_new_messages_count': middle_new_messages_count,
        'middle_current_credit': middle_current_credit,
    }


def admin_header_notifications(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return {'admin_new_messages_count': 0}

    admin_new_messages_count = SmsManagement.objects.filter(
        is_approved=False,
        is_active=True
    ).count()

    return {'admin_new_messages_count': admin_new_messages_count}


def impersonation_banner(request):
    return {
        "is_impersonating": bool(request.session.get("impersonator_id")),
        "impersonator_id": request.session.get("impersonator_id"),
    }
