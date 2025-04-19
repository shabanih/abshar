from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


# Create your models here.

class User(AbstractUser):
    name = models.CharField(max_length=200, verbose_name='نام')
    mobile = models.CharField(max_length=11, unique=True, verbose_name='موبایل')
    username = models.CharField(max_length=11, verbose_name='نام کاربری')
    otp = models.PositiveIntegerField(null=True, blank=True, verbose_name='کد فعالسازی')
    otp_create_time = models.DateTimeField(auto_now_add=True, verbose_name='زمان')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت')
    objects = UserManager()

    USERNAME_FIELD = 'mobile'
    REQUIRED_FIELDS = ['username']

    # backend = 'account_app.mybackend.MobileBackend'

    def get_username(self):
        return self.username


class MyHouse(models.Model):
    name = models.CharField(max_length=100, verbose_name='نام ساختمان')
    address = models.CharField(max_length=100, verbose_name='آدرس')
    account_no = models.CharField(max_length=100, verbose_name='شماره حساب شبا')
    account_name = models.CharField(max_length=100, verbose_name='نام صاحب حساب')
    cart_no = models.CharField(max_length=100, verbose_name='شماره کارت')
    cart_name = models.CharField(max_length=100, verbose_name='نام صاحب کارت')
    initial_fund = models.CharField(max_length=100, verbose_name='موجود اولیه صندوق')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField()

    def __str__(self):
        return self.name


class Unit(models.Model):
    unit = models.IntegerField(unique=True, verbose_name='واحد')
    unit_phone = models.CharField(max_length=8, null=True, blank=True, verbose_name='')
    floor_number = models.IntegerField()
    area = models.IntegerField()
    bedrooms_count = models.IntegerField()
    parking_number = models.IntegerField()
    parking_count = models.IntegerField()
    parking_place = models.CharField(max_length=100, null=True, blank=True, verbose_name='')
    owner_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='نام مالک')
    owner_mobile = models.CharField(max_length=11, unique=True, verbose_name='همراه مالک')
    owner_national_code = models.CharField(max_length=10, null=True, blank=True, verbose_name='')
    purchase_date = models.DateField(null=True, blank=True, verbose_name='تاریخ خرید')
    status = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return str(self.unit)


class Renter(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, verbose_name='واحد مسکونی')
    renter_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='نام مستاجر')
    renter_mobile = models.CharField(max_length=11, unique=True, verbose_name='همراه مستاجر')
    renter_national_code = models.CharField(max_length=10, null=True, blank=True, verbose_name='')
    people_count = models.IntegerField()
    start_date = models.DateField(null=True, blank=True, verbose_name='تاریخ شروع اجاره')
    end_date = models.DateField(null=True, blank=True, verbose_name='تاریخ پایان اجاره')
    contract_number = models.CharField(max_length=100, null=True, blank=True, verbose_name='شماره قرارداد')
    estate_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='نام مشاور املاک')
    first_charge = models.IntegerField(null=True, blank=True, verbose_name='شارژ اولیه')

    def __str__(self):
        return self.renter_name
