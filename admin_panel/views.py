from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ProtectedError
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView, CreateView, DeleteView, UpdateView

from admin_panel.forms import announcementForm, UnitForm, RenterForm
from admin_panel.models import Announcement
from user_app.models import Unit, Renter

app_name = 'admin_panel'


def admin_dashboard(request):
    announcements = Announcement.objects.filter(is_active=True)

    context = {
        'announcements': announcements
    }
    return render(request, 'shared/home_template.html', context)


def site_header_component(request):
    return render(request, 'shared/notification_template.html')


class AnnouncementView(CreateView):
    model = Announcement
    template_name = 'admin_panel/announcement.html'
    form_class = announcementForm
    success_url = reverse_lazy('announcement')

    def form_valid(self, form):
        self.object = form.save(commit=False)
        # announce_instance = form.instance
        messages.success(self.request, 'اطلاعیه با موفقیت ثبت گردید!')
        return super(AnnouncementView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['announcements'] = Announcement.objects.all().order_by('-created_at')
        return context


class AnnouncementUpdateView(UpdateView):
    model = Announcement
    template_name = 'admin_panel/announcement.html'
    form_class = announcementForm
    success_url = reverse_lazy('announcement')

    def form_valid(self, form):
        edit_instance = form.instance
        self.object = form.save(commit=False)
        messages.success(self.request, 'اطلاعیه با موفقیت ویرایش گردید!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['announcements'] = Announcement.objects.filter(is_active=True)
        return context


def announcement_delete(request, pk):
    announce = get_object_or_404(Announcement, id=pk)
    print(announce.id)

    try:
        announce.delete()
        messages.success(request, 'اظلاعیه با موفقیت حذف گردید!')
    except ProtectedError:
        messages.error(request, " امکان حذف وجود ندارد! ")
    return redirect(reverse('announcement'))


def unit_Management(request):
    return render(request, 'admin_panel/unit_Management.html')


class UnitRegisterView(LoginRequiredMixin, CreateView):
    model = Unit
    form_class = UnitForm
    success_url = reverse_lazy('add_unit')
    template_name = 'admin_panel/unit_register.html'

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'واحد با موفقیت ثبت گردید!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(UnitRegisterView, self).get_context_data(**kwargs)
        context['units'] = Unit.objects.all()
        return context


class RenterRegisterView(LoginRequiredMixin, CreateView):
    model = Renter
    form_class = RenterForm
    success_url = reverse_lazy('add_renter')
    template_name = 'admin_panel/renter_register.html'

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'اطلاعات مستاجر با موفقیت ثبت گردید!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(RenterRegisterView, self).get_context_data(**kwargs)
        context['renters'] = Renter.objects.all()
        return context

    # class UnitUpdateView(LoginRequiredMixin, UpdateView):
    #     model = Unit
    #     form_class = UnitForm
    #     success_url = reverse_lazy('')
    #     template_name = 'admin_panel/unit_management.html'
