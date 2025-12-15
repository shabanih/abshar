from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, ProtectedError
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView, ListView, UpdateView
from django.views.generic.edit import FormMixin

from admin_panel.forms import MessageToUserForm
from admin_panel.models import MessageToUser
from notifications.models import SupportUser, SupportFile, SupportMessage, Notification, AdminTicket, AdminTicketFile, \
    AdminTicketMessage, MiddleAdminNotification
from user_app.forms import SupportUserForm, SupportMessageForm, MiddleAdminTicketForm, MiddleAdminMessageForm
from user_app.models import User, Unit


# class SupportUserCreateView(CreateView):
#     model = SupportUser
#     template_name = 'user_send_ticket.html'
#     form_class = SupportUserForm
#     success_url = reverse_lazy('user_support_ticket')
#
#     def form_valid(self, form):
#         obj = form.save(commit=False)
#         obj.user = self.request.user
#         obj.is_sent = True
#         obj.is_read = False  # مدیر هنوز پیام را نخوانده
#         obj.save()
#
#         # ذخیره فایل‌ها
#         files = self.request.FILES.getlist('file')
#         file_objects = [SupportFile.objects.create(support_user=obj, file=f) for f in files]
#
#         # پیام اولیه
#         initial_message = form.cleaned_data.get('message')
#         if initial_message:
#             msg = SupportMessage.objects.create(
#                 support_user=obj,
#                 sender=self.request.user,
#                 message=initial_message
#             )
#             for fobj in file_objects:
#                 msg.attachments.add(fobj)
#
#         # نوتیفیکیشن برای همه مدیران میانی
#         middle_admin_users = User.objects.filter(is_middle_admin=True)
#         for admin in middle_admin_users:
#             Notification.objects.create(
#                 user=admin,
#                 ticket=obj,
#                 title="تیکت جدید",
#                 message=f"یک پیام جدید از کاربر {self.request.user.mobile} دریافت شد.",
#                 link=f"/admin-panel/ticket/{obj.id}/"
#             )
#
#         messages.success(
#             self.request,
#             'تیکت با موفقیت ارسال گردید. کارشناسان ما طی ۳ تا ۵ ساعت آینده پاسخ خواهند داد.'
#         )
#         return redirect(self.success_url)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['tickets'] = SupportUser.objects.filter(
#             user=self.request.user
#         ).order_by('-created_at')
#         return context
class SupportUserCreateView(CreateView):
    model = SupportUser
    template_name = 'user_send_ticket.html'
    form_class = SupportUserForm
    success_url = reverse_lazy('tickets')

    def form_valid(self, form):
        # 1️⃣ ایجاد تیکت
        obj = form.save(commit=False)
        obj.user = self.request.user
        obj.is_sent = True
        obj.save()

        # 2️⃣ ذخیره فایل‌ها
        files = self.request.FILES.getlist('file')
        file_objects = [SupportFile.objects.create(support_user=obj, file=f) for f in files]

        # 3️⃣ ایجاد پیام اولیه
        initial_message = form.cleaned_data.get('message')
        if initial_message:
            msg = SupportMessage.objects.create(
                support_user=obj,
                sender=self.request.user,
                message=initial_message,
                is_read=False  # پیام هنوز توسط مدیر خوانده نشده
            )
            for fobj in file_objects:
                msg.attachments.add(fobj)

        channel_layer = get_channel_layer()

        # فقط مدیر مربوط به کاربر
        middle_admin = obj.user.manager  # obj = SupportUser که الان ایجاد شده
        if middle_admin and middle_admin.is_middle_admin:
            # نوتیفیکیشن (اختیاری)
            Notification.objects.create(
                user=middle_admin,
                ticket=obj,
                title="تیکت جدید",
                message=f"یک پیام جدید از کاربر {self.request.user.mobile} دریافت شد.",
                link=f"/admin-panel/ticket/{obj.id}/"
            )
            # WebSocket broadcast
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{middle_admin.id}",
                {"type": "send_ticket_count"}
            )

        messages.success(
            self.request,
            'تیکت با موفقیت ارسال گردید. کارشناسان ما طی ۳ تا ۵ ساعت آینده پاسخ خواهند داد.'
        )
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tickets'] = SupportUser.objects.filter(user=self.request.user).order_by('-created_at')
        return context


class TicketsView(ListView):
    model = SupportUser
    template_name = 'user_ticket.html'
    context_object_name = 'tickets'

    def get_paginate_by(self, queryset):
        paginate = self.request.GET.get('paginate')
        if paginate == '1000':
            return None  # نمایش همه
        return int(paginate or 20)

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        qs = SupportUser.objects.filter(user=self.request.user)
        if query:
            qs = qs.filter(
                Q(subject__icontains=query) |
                Q(message__icontains=query) |
                Q(ticket_no__icontains=query)
            )
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


def user_ticket_detail(request, pk):
    ticket = get_object_or_404(SupportUser, id=pk, user=request.user)
    form = SupportMessageForm()

    # پیام‌های مدیر به کاربر → به خوانده‌شده تبدیل شوند
    unread_admin_messages = SupportMessage.objects.filter(
        support_user=ticket,
        sender__is_middle_admin=True,
        is_read=False
    )

    if unread_admin_messages.exists():
        unread_admin_messages.update(is_read=True)

        # کانتر مدیر صفر شود → فقط مدیر مربوطه
        channel_layer = get_channel_layer()
        middle_admin = ticket.user.manager
        if middle_admin and middle_admin.is_middle_admin:
            async_to_sync(channel_layer.group_send)(
                f"user_{middle_admin.id}",
                {"type": "send_ticket_count"}
            )

    # ارسال پیام جدید توسط کاربر
    if request.method == 'POST':
        if ticket.is_closed:
            messages.error(request, "این تیکت بسته شده و نمی‌توانید پیام جدید ارسال کنید.")
            return redirect('ticket_detail', pk=ticket.id)

        form = SupportMessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.support_user = ticket
            msg.sender = request.user
            msg.is_read = False  # پیام جدید کاربر → برای مدیر خوانده نشده
            msg.save()

            # ذخیره فایل اختیاری
            file_obj = request.FILES.get('file')
            if file_obj:
                file_instance = SupportFile.objects.create(file=file_obj, support_user=ticket)
                msg.attachments.add(file_instance)

            # وضعیت تیکت
            ticket.is_answer = False
            ticket.is_closed = False
            ticket.save()

            # نوتیفیکیشن و کانتر مدیر → فقط مدیر مربوطه
            channel_layer = get_channel_layer()
            middle_admin = ticket.user.manager
            if middle_admin and middle_admin.is_middle_admin:
                Notification.objects.create(
                    user=middle_admin,
                    ticket=ticket,
                    title="پیام جدید کاربر",
                    message=f"یک پیام جدید از کاربر {request.user.mobile} دریافت شد.",
                    link=f"/admin-panel/ticket/{ticket.id}/"
                )
                async_to_sync(channel_layer.group_send)(
                    f"user_{middle_admin.id}",
                    {"type": "send_ticket_count"}
                )

            return redirect('ticket_detail', pk=ticket.id)

    messages_list = ticket.messages.filter(support_user=ticket).order_by('-created_at')
    return render(request, 'user_ticket_details.html', {
        'ticket': ticket,
        'messages': messages_list,
        'form': form
    })


def close_ticket(request, pk):
    ticket = get_object_or_404(SupportUser, id=pk)
    ticket.is_closed = True
    ticket.save()
    # messages.success(request, "تیکت بسته شد.")
    return redirect('ticket_detail', pk=ticket.id)


# =============================================

class MiddleTicketsView(ListView):
    model = SupportUser
    template_name = 'middle_tickets.html'
    context_object_name = 'tickets'

    def get_paginate_by(self, queryset):
        paginate = self.request.GET.get('paginate')
        if paginate == '1000':
            return None  # نمایش همه
        return int(paginate or 20)

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        qs = SupportUser.objects.filter(user__manager=self.request.user)
        if query:
            qs = qs.filter(
                Q(subject__icontains=query) |
                Q(message__icontains=query) |
                Q(ticket_no__icontains=query)
            )
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


def middleAdmin_ticket_detail(request, pk):
    ticket = get_object_or_404(SupportUser, id=pk)
    form = SupportMessageForm()

    # پیام‌های کاربر که توسط مدیر هنوز خوانده نشده‌اند → خوانده شده شوند
    unread_messages = ticket.messages.filter(
        sender=ticket.user,
        is_read=False
    )
    if unread_messages.exists():
        unread_messages.update(is_read=True)

        # صفر کردن کانتر مدیر (WebSocket)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{request.user.id}",
            {"type": "send_ticket_count"}
        )

    if request.method == 'POST':
        form = SupportMessageForm(request.POST, request.FILES)
        if form.is_valid():
            # ایجاد پیام جدید توسط مدیر
            msg = form.save(commit=False)
            msg.support_user = ticket
            msg.sender = request.user
            msg.is_read = False  # پیام هنوز توسط کاربر خوانده نشده
            msg.save()

            # ذخیره فایل اختیاری
            file_obj = request.FILES.get('file')
            if file_obj:
                file_instance = SupportFile.objects.create(file=file_obj, support_user=ticket)
                msg.attachments.add(file_instance)

            # بروزرسانی وضعیت تیکت
            ticket.is_answer = True
            ticket.is_closed = False
            ticket.save()

            # 🔥 ارسال کانتر به کاربر (فقط کاربر دریافت می‌کند)
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{ticket.user.id}",
                {"type": "send_ticket_count"}
            )

            return redirect('middleAdmin_ticket_detail', pk=ticket.id)

    messages_list = ticket.messages.filter(support_user=ticket).order_by('-created_at')

    return render(request, 'middle_ticket_detail.html', {
        'ticket': ticket,
        'messages_list': messages_list,
        'form': form
    })


def middle_close_ticket(request, pk):
    ticket = get_object_or_404(SupportUser, id=pk)
    ticket.is_closed = True
    ticket.save()
    # messages.success(request, "تیکت بسته شد.")
    return redirect('middleAdmin_ticket_detail', pk=ticket.id)


def middle_open_ticket(request, pk):
    ticket = get_object_or_404(SupportUser, id=pk)
    ticket.is_closed = False
    ticket.save()
    # messages.success(request, "تیکت باز شد.")
    return redirect('middleAdmin_ticket_detail', pk=ticket.id)


def middle_is_waiting(request, pk):
    ticket = get_object_or_404(SupportUser, id=pk)
    ticket.is_waiting = True
    ticket.save()
    return redirect('middleAdmin_ticket_detail', pk=ticket.id)


def middle_is_continue(request, pk):
    ticket = get_object_or_404(SupportUser, id=pk)
    ticket.is_waiting = False
    ticket.save()
    return redirect('middleAdmin_ticket_detail', pk=ticket.id)


# =================================================

class MiddleAdminTicketCreateView(CreateView):
    model = AdminTicket
    template_name = 'middleAdmin_send_ticket.html'
    form_class = MiddleAdminTicketForm
    success_url = reverse_lazy('middleAdmin_tickets')

    def form_valid(self, form):
        # 1️⃣ ایجاد تیکت
        obj = form.save(commit=False)
        obj.user = self.request.user
        obj.is_sent = True
        # 👇 اختصاص ادمین (فرض می‌کنیم تنها یک ادمین داریم)
        obj.assigned_admin = User.objects.filter(is_superuser=True).first()
        obj.middle_admin = self.request.user
        obj.save()

        # 2️⃣ ذخیره فایل‌ها
        files = self.request.FILES.getlist('file')
        file_objects = [AdminTicketFile.objects.create(ticket=obj, file=f) for f in files]

        # 3️⃣ پیام اولیه
        initial_message = form.cleaned_data.get('message')
        if initial_message:
            msg = AdminTicketMessage.objects.create(
                ticket=obj,
                sender=self.request.user,
                message=initial_message,
                is_read=False
            )
            for fobj in file_objects:
                msg.attachments.add(fobj)

        # 4️⃣ نوتیفیکیشن فقط برای ادمین اختصاصی
        if obj.assigned_admin:
            MiddleAdminNotification.objects.create(
                user=obj.assigned_admin,
                ticket=obj,
                title="تیکت جدید از مدیر میانی",
                message=f"یک پیام جدید از {self.request.user.full_name} دریافت شد.",
                link=f"/admin-panel/admin_ticket/{obj.id}/"
            )

            # 🔥 بروزرسانی کانتر WebSocket
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "admins_group",
                {"type": "send_admin_ticket_count"}
            )

        messages.success(
            self.request,
            'تیکت با موفقیت ارسال شد. کارشناسان ما پس از بررسی طی 3 تا 5 ساعت آینده پاسخ خواهند داد.'
        )
        return redirect(self.success_url)


class MiddleAdminTicketsView(ListView):
    model = AdminTicket
    template_name = 'middleAdmin_ticket.html'
    context_object_name = 'middleTickets'

    def get_paginate_by(self, queryset):
        paginate = self.request.GET.get('paginate')
        if paginate == '1000':
            return None  # نمایش همه
        return int(paginate or 20)

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        qs = AdminTicket.objects.filter(user=self.request.user)
        if query:
            qs = qs.filter(
                Q(subject__icontains=query) |
                Q(message__icontains=query) |
                Q(ticket_no__icontains=query)
            )
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


def MiddleAdmin_ticket_detail(request, pk):
    ticket = get_object_or_404(AdminTicket, id=pk)

    if ticket.middle_admin != request.user:
        messages.error(request, "شما اجازه ارسال پیام در این تیکت را ندارید.")
        return redirect('middleAdmin_tickets')

    form = MiddleAdminMessageForm()

    # پیام‌های ادمین که هنوز خوانده نشده‌اند → خوانده شوند
    unread_admin_messages = ticket.messages.filter(
        sender__is_superuser=True,
        is_read=False
    )
    if unread_admin_messages.exists():
        unread_admin_messages.update(is_read=True)

        # بروزرسانی کانتر WebSocket همان مدیر میانی
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"middle_admin_group_{request.user.id}",
            {"type": "send_admin_ticket_count"}
        )

    if request.method == 'POST':
        form = MiddleAdminMessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.ticket = ticket
            msg.sender = request.user
            msg.is_read = False
            msg.save()

            for f in request.FILES.getlist('file'):
                file_instance = AdminTicketFile.objects.create(file=f, ticket=ticket)
                msg.attachments.add(file_instance)

            ticket.is_answer = True
            ticket.is_closed = False
            ticket.save()

            MiddleAdminNotification.objects.create(
                user=ticket.middle_admin,
                ticket=ticket,
                title="پیام جدید از مدیر میانی",
                message="یک پیام جدید از مدیر میانی دریافت شد.",
                link=f"/middle-admin/admin_ticket/{ticket.id}/"
            )

            # ارسال نوتیف به ادمین ها
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "admins_group",
                {"type": "send_admin_ticket_count"}
            )

            return redirect('MAdmin_ticket_detail', pk=ticket.id)

    messages_list = ticket.messages.all().order_by('-created_at')

    return render(request, 'middleAdmin_ticket_detail.html', {
        'ticket': ticket,
        'messages_list': messages_list,
        'form': form
    })


def middlAdmin_close_ticket(request, pk):
    ticket = get_object_or_404(AdminTicket, id=pk)
    ticket.is_closed = True
    ticket.save()
    # messages.success(request, "تیکت بسته شد.")
    return redirect('middleAdmin_ticket_detail', pk=ticket.id)


# -------------------------------------------------------------------------------
class AdminTicketsView(ListView):
    model = AdminTicket
    template_name = 'admin_tickets.html'
    context_object_name = 'admin_tickets'

    def get_paginate_by(self, queryset):
        paginate = self.request.GET.get('paginate')
        if paginate == '1000':
            return None  # نمایش همه
        return int(paginate or 20)

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        qs = AdminTicket.objects.filter(user__is_middle_admin=True).select_related('user')
        if query:
            qs = qs.filter(
                Q(subject__icontains=query) |
                Q(message__icontains=query) |
                Q(ticket_no__icontains=query)
            )
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


def admin_ticket_detail(request, pk):
    ticket = get_object_or_404(AdminTicket, id=pk)

    # فقط ادمین اجازه دارد
    if not request.user.is_superuser:
        messages.error(request, "اجازه دسترسی ندارید.")
        return redirect('admin_tickets')

    form = MiddleAdminMessageForm()

    # پیام‌های خوانده‌نشده مدیر میانی → باید توسط ادمین خوانده شوند
    unread_messages = ticket.messages.filter(
        sender__is_middle_admin=True,
        is_read=False
    )

    if unread_messages.exists():
        unread_messages.update(is_read=True)

        # بروزرسانی کانتر مدیر میانی
        if ticket.middle_admin:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"middle_admin_group_{ticket.middle_admin.id}",
                {"type": "send_admin_ticket_count"}
            )

    if request.method == 'POST':
        form = MiddleAdminMessageForm(request.POST, request.FILES)
        if form.is_valid():

            msg = form.save(commit=False)
            msg.ticket = ticket
            msg.sender = request.user  # ادمین
            msg.is_read = False
            msg.save()

            # ذخیره فایل‌ها
            for f in request.FILES.getlist('file'):
                file_instance = AdminTicketFile.objects.create(file=f, ticket=ticket)
                msg.attachments.add(file_instance)

            ticket.is_answer = True
            ticket.is_closed = False
            ticket.save()

            # نوتیفیکیشن برای مدیر میانی
            if ticket.middle_admin:
                MiddleAdminNotification.objects.create(
                    user=ticket.middle_admin,
                    ticket=ticket,
                    title="پیام جدید از ادمین",
                    message=f"ادمین یک پیام جدید برای تیکت #{ticket.ticket_no} ارسال کرد.",
                    link=f"/middle-admin/admin_ticket/{ticket.id}/"
                )

                # آپدیت کانتر مدیر میانی
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"middle_admin_group_{ticket.middle_admin.id}",
                    {"type": "send_admin_ticket_count"}
                )

            return redirect('admin_ticket_detail', pk=ticket.id)

    messages_list = ticket.messages.all().order_by('-created_at')

    return render(request, 'admin_ticket_detail.html', {
        'ticket': ticket,
        'messages_list': messages_list,
        'form': form
    })


def admin_close_ticket(request, pk):
    ticket = get_object_or_404(AdminTicket, id=pk)
    ticket.is_closed = True
    ticket.save()
    # messages.success(request, "تیکت بسته شد.")
    return redirect('admin_ticket_detail', pk=ticket.id)


def admin_open_ticket(request, pk):
    ticket = get_object_or_404(AdminTicket, id=pk)
    ticket.is_closed = False
    ticket.save()
    # messages.success(request, "تیکت باز شد.")
    return redirect('admin_ticket_detail', pk=ticket.id)


def admin_is_waiting(request, pk):
    ticket = get_object_or_404(AdminTicket, id=pk)
    ticket.is_waiting = True
    ticket.save()
    return redirect('admin_ticket_detail', pk=ticket.id)


def admin_is_continue(request, pk):
    ticket = get_object_or_404(AdminTicket, id=pk)
    ticket.is_waiting = False
    ticket.save()
    return redirect('admin_ticket_detail', pk=ticket.id)


# ========================= Message To User ======

class MessageToUserListCreateView(FormMixin, ListView):
    model = MessageToUser
    form_class = MessageToUserForm
    template_name = 'message_to_user.html'
    context_object_name = 'user_messages'
    success_url = reverse_lazy('message_to_user')  # نام url همین صفحه

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_paginate_by(self, queryset):
        paginate = self.request.GET.get('paginate')
        if paginate == '1000':
            return None  # نمایش همه آیتم‌ها
        return int(paginate or 20)

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        queryset = MessageToUser.objects.filter(is_active=True)

        if query:
            queryset = queryset.filter(
                Q(user__full_name__icontains=query) |
                Q(title__icontains=query) |
                Q(message__icontains=query)
            ).distinct()

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.get_form()
        context['query'] = self.request.GET.get('q', '')
        context['paginate'] = self.request.GET.get('paginate', '20')
        return context

    # ✅ این بخش مهم‌ترین قسمت است
    def post(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        form = self.get_form()

        if form.is_valid():
            messages.success(request, 'پیام با موفقیت ثبت گردید')
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        message = form.save(commit=False)

        # اگر چند unit انتخاب شده
        units = form.cleaned_data['unit']

        for unit in units:
            MessageToUser.objects.create(
                user=unit.user,
                title=message.title,
                message=message.message,
                is_active=message.is_active
            )

        return super().form_valid(form)


@login_required
def ajax_units(request):
    if not request.user.is_authenticated:
        return JsonResponse({'results': []})

    user = request.user
    q = request.GET.get('q', '').strip()
    is_initial = request.GET.get('initial')

    managed_users = User.objects.filter(
        Q(manager=user) | Q(pk=user.pk)
    )

    units = Unit.objects.filter(
        is_active=True,
        user__in=managed_users
    )

    # 🔹 اگر سرچ انجام شده
    if q:
        units = units.filter(
            Q(unit__icontains=q) |
            Q(owner_name__icontains=q) |
            Q(renters__renter_name__icontains=q)
        ).distinct()

    # 🔹 اگر فقط کلیک شده (initial load)
    elif is_initial:
        units = units[:10]

    results = [
        {
            'id': u.id,
            'text': u.get_label()
        }
        for u in units[:20]  # محدودیت نهایی برای performance
    ]

    return JsonResponse({'results': results})

def message_user_delete(request, pk):
    message = get_object_or_404(MessageToUser, id=pk)
    try:
        message.delete()
        messages.success(request, 'پیام با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('message_to_user'))
