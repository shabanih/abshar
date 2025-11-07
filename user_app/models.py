from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


# Create your models here.

class User(AbstractUser):
    full_name = models.CharField(max_length=200, verbose_name='نام')
    mobile = models.CharField(max_length=11, unique=True, verbose_name='موبایل')
    username = models.CharField(max_length=150, unique=True, verbose_name='نام کاربری')

    otp = models.PositiveIntegerField(null=True, blank=True, verbose_name='کد فعالسازی')
    otp_create_time = models.DateTimeField(null=True, blank=True, verbose_name='زمان ارسال کد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت')

    # This is the key field for user hierarchy:
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_users',
        verbose_name='مدیر سطح میانی'
    )

    is_middle_admin = models.BooleanField(default=False, verbose_name='مدیر سطح میانی')

    objects = UserManager()

    USERNAME_FIELD = 'mobile'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.full_name} - {self.mobile}"

    def get_full_name(self):
        return self.full_name


class Bank(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='کاربر (مدیر)'
    )
    house = models.ForeignKey(
        'MyHouse',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='banks',
        verbose_name='ساختمان مرتبط'
    )
    bank_name = models.CharField(max_length=100, verbose_name='نام بانک')
    account_no = models.CharField(max_length=100, verbose_name='شماره حساب')
    account_holder_name = models.CharField(max_length=100, verbose_name='نام صاحب حساب')
    sheba_number = models.CharField(max_length=100, verbose_name='شماره شبا')
    cart_number = models.CharField(max_length=100, verbose_name='شماره کارت')
    initial_fund = models.PositiveIntegerField(verbose_name='موجودی اولیه صندوق')
    create_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return f"{self.bank_name} - {self.cart_number}"


class MyHouse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, verbose_name='نام ساختمان')
    user_type = models.CharField(max_length=100, null=True, blank=True, verbose_name='نوع کاربری')
    city = models.CharField(max_length=100, null=True, blank=True, verbose_name='شهر')
    address = models.CharField(max_length=200, verbose_name='آدرس')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return self.name


class Unit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='کاربر')
    unit = models.IntegerField(unique=True, verbose_name='واحد')
    unit_phone = models.CharField(max_length=8, null=True, blank=True, verbose_name='')
    floor_number = models.IntegerField()
    area = models.IntegerField()
    bedrooms_count = models.IntegerField()
    parking_number = models.CharField(max_length=10, null=True, blank=True)
    parking_count = models.IntegerField()
    parking_place = models.CharField(max_length=100, null=True, blank=True, verbose_name='موقعیت پارکینگ ')
    extra_parking_first = models.CharField(max_length=100, null=True, blank=True, verbose_name='موقعیت پارکینگ اول')
    extra_parking_second = models.CharField(max_length=100, null=True, blank=True, verbose_name='موقعیت پارکینگ دوم')
    unit_details = models.TextField(null=True, blank=True, verbose_name='توضیحات ساختمان')
    owner_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='نام مالک')
    owner_mobile = models.CharField(max_length=11, verbose_name='همراه مالک')
    owner_national_code = models.CharField(max_length=10, null=True, blank=True, verbose_name='کد ملی')
    purchase_date = models.DateField(null=True, blank=True, verbose_name='تاریخ خرید')
    owner_people_count = models.CharField(max_length=10, null=True, blank=True, verbose_name='تعداد نفرات مالک')
    owner_details = models.TextField(null=True, blank=True, verbose_name='توضیحات مالک')
    status_residence = models.CharField(max_length=100, null=True, blank=True, verbose_name='وضعیت سکونت')
    is_renter = models.BooleanField(default=False, verbose_name=' مستاجر دارد؟', null=True, blank=True)
    people_count = models.IntegerField(null=True, blank=True, verbose_name='تعداد نفرات')
    parking_counts = models.IntegerField(null=True, blank=True, verbose_name='تعداد پارکینگ اضافه')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیر فعال')

    def __str__(self):
        return self.owner_name

    def get_active_renter(self):
        return self.renters.filter(renter_is_active=True).first()

    def save(self, *args, **kwargs):
        # --- Calculate extra parking count ---
        count = 0
        if self.extra_parking_first:
            count += 1
        if self.extra_parking_second:
            count += 1
        self.parking_counts = count

        # --- Update people_count based on owner or renter ---
        if self.is_renter:
            # if this unit has an active renter, use their people count
            if hasattr(self, 'renters'):
                active_renter = self.renters.filter(renter_is_active=True).first()
                if active_renter and hasattr(active_renter, 'renter_people_count'):
                    self.people_count = active_renter.renter_people_count
        else:
            # if it's owned (not rented), use owner_people_count
            if self.owner_people_count:
                try:
                    self.people_count = int(self.owner_people_count)
                except ValueError:
                    self.people_count = None  # handle invalid input gracefully

        super().save(*args, **kwargs)


class Renter(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, verbose_name='واحد', related_name='renters', null=True,
                             blank=True)
    renter_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='نام مستاجر')
    renter_mobile = models.CharField(max_length=11, null=True, blank=True, verbose_name='همراه')
    renter_national_code = models.CharField(max_length=10, null=True, blank=True, verbose_name='کد ملی')
    renter_people_count = models.CharField(max_length=10, null=True, blank=True, verbose_name='تعداد نفرات')
    start_date = models.DateField(null=True, blank=True, verbose_name='تاریخ شروع اجاره')
    end_date = models.DateField(null=True, blank=True, verbose_name='تاریخ پایان اجاره')
    contract_number = models.CharField(max_length=100, null=True, blank=True, verbose_name='شماره قرارداد')
    estate_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='نام مشاور املاک')
    first_charge = models.IntegerField(null=True, blank=True, verbose_name='شارژ اولیه', default=0)
    renter_details = models.TextField(null=True, blank=True, verbose_name='توضیحات مستاجر')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    renter_is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return self.renter_name
