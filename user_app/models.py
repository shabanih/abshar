from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils import timezone


class ChargeMethod(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True, verbose_name='')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')

    def __str__(self):
        return self.name


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
    charge_methods = models.ManyToManyField(
        'ChargeMethod',
        blank=True,
        verbose_name='روش‌های شارژ قابل دسترسی'
    )

    is_middle_admin = models.BooleanField(default=False, verbose_name='مدیر سطح میانی')

    objects = UserManager()

    USERNAME_FIELD = 'mobile'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.full_name}"

    def get_full_name(self):
        return self.full_name

    @property
    def charge_method_ids(self):
        return list(self.charge_methods.values_list('id', flat=True))

    @staticmethod
    def get_manager_for_user(user):
        if user.manager and user.manager.is_middle_admin:
            return user.manager
        return None


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
    is_default = models.BooleanField(default=False, verbose_name='حساب پیش فرض')
    create_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def save(self, *args, **kwargs):
        if self.is_default:
            # همه بانک‌های دیگر را برای همان کاربر غیرپیش‌فرض می‌کنیم
            Bank.objects.filter(user=self.user, is_default=True).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_default(cls, user, house=None):
        qs = cls.objects.filter(user=user, is_default=True, is_active=True)
        if house:
            qs = qs.filter(house=house)
        return qs.first()

    def __str__(self):
        return f"{self.bank_name} - {self.account_no}"


class MyHouse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    residents = models.ManyToManyField(User, related_name='houses', blank=True, verbose_name='ساکنین')
    name = models.CharField(max_length=100, verbose_name='نام ساختمان')
    floor_counts = models.PositiveIntegerField(default=1)
    unit_counts = models.PositiveIntegerField(default=1)
    user_type = models.CharField(max_length=100, null=True, blank=True, verbose_name='نوع کاربری')
    city = models.CharField(max_length=100, null=True, blank=True, verbose_name='شهر')
    address = models.CharField(max_length=200, verbose_name='آدرس')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    def __str__(self):
        return self.name


class Unit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='کاربر')
    unit = models.IntegerField(verbose_name='واحد')
    myhouse = models.ForeignKey(
        MyHouse,
        on_delete=models.CASCADE,
        related_name='units',
        null=True,  # اگر دیتای قدیمی داری
        blank=True
    )
    owner_bank = models.ForeignKey(Bank, on_delete=models.CASCADE, null=True, blank=True, verbose_name='شماره حساب')

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
    owner_people_count = models.PositiveIntegerField(null=True, blank=True, verbose_name='تعداد نفرات مالک')
    owner_details = models.TextField(null=True, blank=True, verbose_name='توضیحات مالک')
    status_residence = models.CharField(max_length=100, null=True, blank=True, verbose_name='وضعیت سکونت')
    is_renter = models.BooleanField(default=False, verbose_name=' مستاجر دارد؟', null=True, blank=True)
    people_count = models.IntegerField(null=True, blank=True, verbose_name='تعداد نفرات')
    parking_counts = models.IntegerField(null=True, blank=True, verbose_name='تعداد پارکینگ اضافه')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ایجاد')
    first_charge_owner = models.IntegerField(null=True, blank=True, verbose_name='شارژ اولیه مالک', default=0)
    owner_payment_date = models.DateField(null=True, blank=True)
    owner_transaction_no = models.CharField(max_length=30, null=True, blank=True)

    is_active = models.BooleanField(default=True, verbose_name='فعال/غیر فعال')

    class Meta:
        unique_together = ('user', 'unit')
        verbose_name = "واحد"
        verbose_name_plural = "واحدها"

    def __str__(self):
        return f"واحد {self.unit} -  {self.user}"

    def get_unit(self):
        return f"واحد {self.unit} - {self.owner_name}"

    def get_active_renter(self):
        return self.renters.filter(renter_is_active=True).first()

    def get_label(self):
        renter = self.get_active_renter()
        return f"واحد {self.unit} - {renter.renter_name}" if renter else f"واحد {self.unit} - {self.owner_name}"


    def get_label_invoice(self):
        renter = self.get_active_renter()
        return f" {renter.renter_name}" if renter else f"{self.owner_name}"

    def update_people_count(self):
        renter = self.get_active_renter()
        if renter:
            self.people_count = int(renter.renter_people_count or 0)
        else:
            self.people_count = int(self.owner_people_count or 0)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old = None

        if not is_new:
            old = Unit.objects.get(pk=self.pk)

        # --- Calculate extra parking count ---
        count = 0
        if self.extra_parking_first:
            count += 1
        if self.extra_parking_second:
            count += 1
        self.parking_counts = count

        super().save(*args, **kwargs)  # ذخیره اولیه برای گرفتن PK
        self.update_people_count()
        super().save(update_fields=['people_count'])

        # --- Calculate people_count AFTER PK exists ---
        active_renter = self.get_active_renter()
        if active_renter:
            self.people_count = int(active_renter.renter_people_count or 0)
        else:
            self.people_count = int(self.owner_people_count or 0)

        # ثبت تاریخچه تغییر مالک
        from .models import UnitResidenceHistory

        if is_new:
            # واحد جدید → ثبت مالک اولیه
            UnitResidenceHistory.objects.create(
                unit=self,
                resident_type='owner',
                name=self.owner_name,
                mobile=self.owner_mobile,
                people_count=int(self.owner_people_count or 0),
                from_date=timezone.now().date(),
                changed_by=self.user
            )
        elif old.owner_name != self.owner_name:
            # تغییر مالک موجود
            UnitResidenceHistory.objects.filter(
                unit=self,
                resident_type='owner',
                to_date__isnull=True
            ).update(to_date=timezone.now().date())

            UnitResidenceHistory.objects.create(
                unit=self,
                resident_type='owner',
                name=self.owner_name,
                mobile=self.owner_mobile,
                people_count=int(self.owner_people_count or 0),
                from_date=timezone.now().date(),
                changed_by=self.user
            )


class Renter(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, verbose_name='واحد', related_name='renters', null=True,
                             blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='کاربر')
    renter_bank = models.ForeignKey(Bank, on_delete=models.CASCADE, null=True, blank=True, verbose_name='شماره حساب')
    renter_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='نام مستاجر')
    renter_mobile = models.CharField(max_length=11, null=True, blank=True, verbose_name='همراه')
    renter_national_code = models.CharField(max_length=10, null=True, blank=True, verbose_name='کد ملی')
    renter_people_count = models.CharField(max_length=10, null=True, blank=True, verbose_name='تعداد نفرات')
    start_date = models.DateField(null=True, blank=True, verbose_name='تاریخ شروع اجاره')
    end_date = models.DateField(null=True, blank=True, verbose_name='تاریخ پایان اجاره')
    contract_number = models.CharField(max_length=100, null=True, blank=True, verbose_name='شماره قرارداد')
    estate_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='نام مشاور املاک')
    first_charge_renter = models.IntegerField(null=True, blank=True, verbose_name='شارژ اولیه مستاجر', default=0)
    renter_details = models.TextField(null=True, blank=True, verbose_name='توضیحات مستاجر')
    renter_payment_date = models.DateField(null=True, blank=True)
    renter_transaction_no = models.CharField(max_length=30, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='')
    renter_is_active = models.BooleanField(default=True, verbose_name='')

    def __str__(self):
        return self.renter_name

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old = None

        if not is_new:
            old = Renter.objects.get(pk=self.pk)

        super().save(*args, **kwargs)

        # ==============================
        # مستاجر فعال شد
        # ==============================
        if is_new and self.renter_is_active:
            UnitResidenceHistory.objects.create(
                unit=self.unit,
                resident_type='renter',
                renter=self,
                name=self.renter_name,
                mobile=self.renter_mobile,
                people_count=int(self.renter_people_count or 0),
                from_date=self.start_date or timezone.now().date(),
                changed_by=self.user
            )

        if not self.renter_is_active and (is_new or not old.renter_is_active):
            # ⛔ بستن مالک فعال
            UnitResidenceHistory.objects.filter(
                unit=self.unit,
                resident_type='owner',
                to_date__isnull=True
            ).update(to_date=self.start_date or timezone.now().date())

            # ⛔ بستن مستاجر فعال قبلی
            UnitResidenceHistory.objects.filter(
                unit=self.unit,
                resident_type='renter',
                to_date__isnull=True
            ).update(to_date=self.start_date or timezone.now().date())

            # ✅ ثبت مستاجر جدید
            UnitResidenceHistory.objects.create(
                unit=self.unit,
                resident_type='renter',
                renter=self,
                name=self.renter_name,
                mobile=self.renter_mobile,
                people_count=int(self.renter_people_count or 0),
                from_date=self.start_date or timezone.now().date(),
                changed_by=self.user
            )

        # ==============================
        # مستاجر غیرفعال شد
        # ==============================
        if old and old.renter_is_active and not self.renter_is_active:
            # بستن سابقه مستاجر
            UnitResidenceHistory.objects.filter(
                renter=self,
                to_date__isnull=True
            ).update(to_date=self.end_date or timezone.now().date())

            # 🔁 فعال شدن مجدد مالک
            UnitResidenceHistory.objects.create(
                unit=self.unit,
                resident_type='owner',
                name=self.unit.owner_name,
                mobile=self.unit.owner_mobile,
                people_count=int(self.unit.owner_people_count or 0),
                from_date=self.end_date or timezone.now().date(),
                changed_by=self.user
            )


class UnitResidenceHistory(models.Model):
    RESIDENT_TYPE_CHOICES = (
        ('owner', 'مالک'),
        ('renter', 'مستاجر'),
    )

    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name='residence_histories'
    )

    resident_type = models.CharField(
        max_length=10,
        choices=RESIDENT_TYPE_CHOICES
    )

    # اطلاعات شخص
    name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=20)
    people_count = models.IntegerField(default=0)

    # فقط برای مستاجر
    renter = models.ForeignKey(
        Renter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    from_date = models.DateField()
    to_date = models.DateField(null=True, blank=True)

    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='unit_residence_changes'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def is_active(self):
        return self.to_date is None

    def __str__(self):
        return f"{self.get_resident_type_display()} | {self.name} | واحد {self.unit.unit}"


class CalendarNote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    year = models.IntegerField()
    month = models.IntegerField()
    day = models.IntegerField()
    note = models.TextField(blank=True)

    class Meta:
        unique_together = ('user', 'year', 'month', 'day')

    def __str__(self):
        return f"{self.user} - {self.year}/{self.month}/{self.day}"
