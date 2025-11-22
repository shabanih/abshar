from user_app.models import MyHouse


def current_house(request):
    if request.user.is_authenticated:
        # کاربر مدیر یا ساکن
        house = MyHouse.objects.filter(residents=request.user).first() \
                or MyHouse.objects.filter(user=request.user).first()

        return {
            'house': house
        }
    return {}