from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render, get_object_or_404

from user_app.forms import LoginForm
from user_app.models import Unit, MyHouse


def index(request):
    form = LoginForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        mobile = form.cleaned_data['mobile']
        password = form.cleaned_data['password']

        user = authenticate(request, username=mobile, password=password)

        if user:
            if user.is_superuser:
                messages.error(request, 'شما مجوز ورود از این صفحه را ندارید.')

            elif not user.is_active:
                messages.error(request, 'حساب کاربری شما غیرفعال است.')

            # ⛔ مالک با مستاجر فعال
            elif Unit.objects.filter(
                    user=user,
                    renters__renter_is_active=True
            ).exists():
                messages.error(
                    request,
                    'برای واحد شما مستاجر فعال ثبت شده است و امکان ورود مالک وجود ندارد.'
                )

            else:
                login(request, user)

                if user.is_middle_admin:
                    has_house = MyHouse.objects.filter(user=user).exists()
                    if has_house:
                        return redirect('middle_admin_dashboard')
                    else:
                        return redirect('middle_manage_house')

                return redirect('user_panel')


        else:
            messages.error(request, 'ورود ناموفق: شماره موبایل یا کلمه عبور نادرست است.')

    return render(request, 'index.html', {'form': form})


def home_page(request):
    buildings = MyHouse.objects.filter(is_active=True)

    return render(request, "home.html", {
        "buildings": buildings
    })


def building_page(request):
    host = request.get_host()  # مثال: "lale.myvh.ir"
    subdomain = host.split('.')[0]  # "lale"

    building = get_object_or_404(MyHouse, subdomain=subdomain, is_active=True)

    return render(request, "building_page.html", {"building": building})