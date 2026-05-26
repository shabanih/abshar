import datetime
import io
import re
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q, ProtectedError, Sum, Count
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.template.loader import get_template
from django.utils import timezone
from django.views.generic import ListView
from pypdf import PdfWriter
from weasyprint import CSS, HTML

from user_app.models import Unit, User
from .models import Poll, Question, Choice, MyHouse, Vote
from .forms import PollCreateForm


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def create_poll(request):
    house = MyHouse.objects.filter(user=request.user).first()

    if request.method == "POST":

        form = PollCreateForm(request.POST)

        if form.is_valid():

            poll = form.save(commit=False)
            poll.house = house
            poll.created_by = request.user
            poll.save()

            questions = {}

            # استخراج سوالات
            for key, value in request.POST.items():

                match = re.match(r'questions\[(\d+)\]\[(\w+)\]', key)

                if match:
                    q_index = int(match.group(1))
                    field = match.group(2)

                    if q_index not in questions:
                        questions[q_index] = {}

                    questions[q_index][field] = value

            # ذخیره سوالات
            for q_index, q_data in questions.items():

                question = Question.objects.create(
                    poll=poll,
                    title=q_data.get("title"),
                    question_type=q_data.get("type"),
                    order=q_index
                )

                choices = request.POST.getlist(f'questions[{q_index}][choices][]')

                for choice in choices:
                    if choice.strip():
                        Choice.objects.create(
                            question=question,
                            title=choice
                        )

            messages.success(request, "نظرسنجی با موفقیت ثبت شد")

            return redirect("poll_list")

    else:
        form = PollCreateForm()

    return render(request, "create_poll.html", {
        "form": form,
        "house": house,
    })


class PollListView(ListView):
    template_name = 'poll_list.html'
    context_object_name = 'polls'

    def get_paginate_by(self, queryset):
        paginate = self.request.GET.get('paginate')
        if paginate == '1000':
            return None  # نمایش همه آیتم‌ها
        return int(paginate or 20)

    def get_queryset(self):
        house = MyHouse.objects.filter(user=self.request.user).first()
        query = self.request.GET.get('q', '')

        # پیام‌های فعال کاربر
        queryset = Poll.objects.filter(
            house=house
        ).distinct()

        # فیلتر جستجو
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query)

            ).distinct()

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['paginate'] = self.request.GET.get('paginate', '20')
        return context


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def edit_poll(request, poll_id):
    poll = get_object_or_404(Poll, id=poll_id, created_by=request.user)

    house = poll.house

    if request.method == "POST":

        form = PollCreateForm(request.POST, instance=poll)

        if form.is_valid():
            poll = form.save(commit=False)
            poll.house = house
            poll.created_by = request.user
            poll.save()

            # --- حذف سوالات و گزینه‌های قدیمی (برای سادگی) ---
            poll.questions.all().delete()

            # استخراج سوالات از POST
            questions = {}
            for key, value in request.POST.items():
                match = re.match(r'questions\[(\d+)\]\[(\w+)\]', key)
                if match:
                    q_index = int(match.group(1))
                    field = match.group(2)
                    questions.setdefault(q_index, {})[field] = value

            # ذخیره دوباره سوالات و گزینه‌ها
            for q_index, q_data in questions.items():

                question = Question.objects.create(
                    poll=poll,
                    title=q_data.get("title"),
                    question_type=q_data.get("type"),
                    order=q_index
                )

                choices = request.POST.getlist(f'questions[{q_index}][choices][]')

                for choice in choices:
                    if choice.strip():
                        Choice.objects.create(
                            question=question,
                            title=choice
                        )

            messages.success(request, "نظرسنجی با موفقیت ویرایش شد")
            return redirect("poll_list")

        else:
            messages.error(request, "فرم معتبر نیست. لطفاً خطاها را بررسی کنید.")

    else:
        form = PollCreateForm(instance=poll)

    # استخراج سوالات و گزینه‌ها برای نمایش در فرم ویرایش
    questions_data = []
    for q in poll.questions.all().order_by("order"):
        choices = list(q.choices.values_list("title", flat=True))
        questions_data.append({
            "id": q.id,
            "title": q.title,
            "type": q.question_type,
            "choices": choices,
            "order": q.order
        })

    return render(request, "edit_poll.html", {
        "form": form,
        "house": house,
        "poll": poll,
        "questions": questions_data,
    })


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def delete_poll(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    try:
        poll.delete()
        messages.success(request, f'{poll.title} با موفقیت حذف گردید!')
        return redirect('poll_list')
    except ProtectedError:
        messages.error(request, "امکان حذف این شارژ به دلیل وابستگی وجود ندارد!")


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def polls_list_pdf(request):
    house = None
    if request.user.is_authenticated:
        house = MyHouse.objects.filter(residents=request.user).order_by('-created_at').first()

    # 🔍 جستجو
    query = request.GET.get('q', '').strip()

    polls = Poll.objects.filter(house=house).order_by('-created_at')

    if query:
        search_q = (
                Q(title__icontains=query) |
                Q(description__icontains=query)
        )

        polls = polls.filter(search_q)

    polls = polls.order_by('-created_at')

    font_url = request.build_absolute_uri('/static/fonts/BYekan.ttf')
    css = CSS(string=f"""
               @page {{ size: A4 landscape; margin: 1cm; }}
               body {{
                   font-family: 'BYekan', sans-serif;
               }}
               @font-face {{
                   font-family: 'BYekan';
                   src: url('{font_url}');
               }}
           """)

    # Render HTML template
    template = get_template("polls_report_pdf.html")
    context = {
        'font_path': font_url,
        'polls': polls,
        'query': query,
        'house': house,
        'today': timezone.now(),
    }
    html = template.render(context)

    # Generate PDF
    page_pdf = io.BytesIO()
    HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(page_pdf, stylesheets=[css])

    page_pdf.seek(0)

    # Generate the final PDF response
    pdf_merger = PdfWriter()
    pdf_merger.append(page_pdf)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="polls_list_report.pdf"'
    pdf_merger.write(response)
    return response


@login_required(login_url=settings.LOGIN_URL_MIDDLE_ADMIN)
def poll_detail(request, poll_id):
    house = MyHouse.objects.filter(user=request.user).first()

    poll = get_object_or_404(
        Poll.objects.prefetch_related("questions__choices"),
        pk=poll_id,
        house=house,
    )


    voted = Vote.objects.filter(
        question__poll=poll,
        user=request.user,

    ).exists()

    user_count = User.objects.filter(
        manager=request.user,
        is_active=True
    ).count()

    voted_count = Vote.objects.filter(
        question__poll=poll
    ).values('user').distinct().count()  # تعداد واحدهایی که رأی داده‌اند

    not_voted = user_count - voted_count

    vote_chart = {
        "labels": ["رأی داده‌اند", "رأی نداده‌اند"],
        "data": [voted_count, not_voted]
    }

    choices_data = (
        Choice.objects
        .filter(question__poll=poll)
        .annotate(
            total_vote=Count(
                'vote',
                filter=Q(vote__isnull=False)
            )
        )
        .filter(total_vote__gt=0)
        .values('title', 'total_vote')
    )
    # ساخت داده‌ای که به چارت می‌رود
    poll_chart_data = {
        "labels": [item["title"] for item in choices_data],
        "data": [item["total_vote"] for item in choices_data]
    }

    return render(request, "poll_detail.html", {
        "poll": poll,
        "voted": voted,
        "vote_chart": vote_chart,
        # "user_count": user_count,
        "poll_chart_data": poll_chart_data
    })
