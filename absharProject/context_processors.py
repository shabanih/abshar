from admin_panel.models import UnifiedCharge, Announcement
from user_app.models import MyHouse


# def current_house(request):
#     if request.user.is_authenticated:
#         # کاربر مدیر یا ساکن
#         house = MyHouse.objects.filter(residents=request.user).first() \
#                 or MyHouse.objects.filter(user=request.user).first()
#
#         return {
#             'house': house
#         }
#     return {}

def current_house(request):
    if not request.user.is_authenticated:
        return {}

    # همه خانه‌هایی که کاربر در آنها ساکن یا مالک است
    houses = MyHouse.objects.filter(residents=request.user).order_by('-created_at')

    # اگر فقط می‌خواهید اولین خانه را نشان دهید
    house = houses.first()

    return {'house': house}


def header_notifications(request):
    if not request.user.is_authenticated:
        return {}

    new_charges_count = UnifiedCharge.objects.filter(
        user=request.user,
        is_paid=False
    ).count()

    return {
        'new_charges_count': new_charges_count,
    }


def announcement_notifications(request):
    if not request.user.is_authenticated:
        return {}

    new_announce_count = Announcement.objects.filter(
        user=request.user,
        is_paid=False
    ).count()

    return {
        'new_announce_count': new_announce_count,
    }