from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.core.paginator import Paginator
from django.db.models import ProtectedError
from django.http import HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, UpdateView

from home.forms import FreeRequestForm, ContactUsForm, ArticleForm
from home.models import SliderText, FreeRequest, ContactUs, Articles
from user_app.forms import LoginForm
from user_app.models import Unit, MyHouse


def house_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.house:
            return redirect('main_site')  # صفحه اصلی سایت
        return view_func(request, *args, **kwargs)

    return wrapper


def index(request):
    articles = Articles.objects.filter(is_active=True).order_by('-created_at')[:3]
    form = FreeRequestForm()
    if request.method == 'POST':
        form = FreeRequestForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'ثبت با موفقیت انجام شد')
            return redirect('home')
        else:
            messages.error(request, 'oxg')
            return redirect('home')

    return render(request, 'home.html', {'form': form, 'articles': articles})


def house_home(request):
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

            # # ⛔ مالک با مستاجر فعال
            # elif Unit.objects.filter(
            #         user=user,
            #         renters__renter_is_active=True
            # ).exists():
            #     messages.error(
            #         request,
            #         'برای واحد شما مستاجر فعال ثبت شده است و امکان ورود مالک وجود ندارد.'
            #     )

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
    context = {
        'form': form,
        "house": request.house,

    }

    return render(request, 'building_page.html', context)


def site_header_component(request):
    sliders = SliderText.objects.all().order_by('-id')

    context = {
        'sliders': sliders
    }
    return render(request, 'renter_partials/site_header.html', context)


def site_footer_component(request):
    return render(request, 'renter_partials/site_footer.html')


def test_subdomain(request):
    return HttpResponse(
        f"Subdomain: {request.subdomain} | House: {request.house}"
    )


def middle_login(request):
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
            # elif Unit.objects.filter(
            #         user=user,
            #         renters__renter_is_active=True
            # ).exists():
            #     messages.error(
            #         request,
            #         'برای واحد شما مستاجر فعال ثبت شده است و امکان ورود مالک وجود ندارد.'
            #     )

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
    context = {
        'form': form,
        "house": request.house,

    }
    return render(request, "middle_login.html", context)


def contact_us_view(request):
    form = ContactUsForm(request.POST or None)
    if request.method == 'POST':
        # name = request.POST['name']
        # subject = request.POST['subject']
        # message = request.POST['message']
        # mobile = request.POST['mobile']

        if form.is_valid():
            # comment = ContactUs.objects.create(name=name, subject=subject, message=message, mobile=mobile)
            form.save()
            messages.success(request,
                             'پیام شما با موفقیت ارسال گردید. پس از بررسی در صورت ثبت شماره تماس و یا ایمیل با شما ارتباط  خواهیم گرفت.')
            return redirect(reverse('contact_us'))
        else:
            messages.error(request, 'لطفا موارد ذیل را بررسی کنید.')

    context = {
        'form': form
    }
    return render(request, 'contact.html', context)


def about_us_view(request):
    return render(request, 'about.html')


def introduction_view(request):
    return render(request, 'introduction.html')


def articles_view(request):
    articles = Articles.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'articles.html', {'articles': articles})


def article_details_view(request, article_id):
    article = Articles.objects.get(pk=article_id)
    similar_articles = Articles.objects.filter(is_active=True).exclude(pk=article.pk)
    return render(request, 'article_details.html', {'article': article, 'similar_articles': similar_articles})

