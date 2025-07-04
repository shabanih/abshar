# Generated by Django 5.2 on 2025-06-05 06:39

import django.contrib.auth.models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('full_name', models.CharField(max_length=200, verbose_name='نام')),
                ('mobile', models.CharField(max_length=11, unique=True, verbose_name='موبایل')),
                ('username', models.CharField(max_length=150, unique=True, verbose_name='نام کاربری')),
                ('otp', models.PositiveIntegerField(blank=True, null=True, verbose_name='کد فعالسازی')),
                ('otp_create_time', models.DateTimeField(blank=True, null=True, verbose_name='زمان ارسال کد')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال/غیرفعال')),
                ('created_time', models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت')),
                ('is_middle_admin', models.BooleanField(default=False, verbose_name='مدیر سطح میانی')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('manager', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='managed_users', to=settings.AUTH_USER_MODEL, verbose_name='مدیر سطح میانی')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Bank',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('house_name', models.CharField(blank=True, max_length=100, null=True, verbose_name='نام ساختمان')),
                ('bank_name', models.CharField(max_length=100, verbose_name='نام بانک')),
                ('account_no', models.CharField(max_length=100, verbose_name='شماره حساب ')),
                ('account_holder_name', models.CharField(max_length=100, verbose_name='نام صاحب حساب')),
                ('sheba_number', models.CharField(max_length=100, verbose_name='شماره شبا')),
                ('cart_number', models.CharField(max_length=100, verbose_name='شماره کارت')),
                ('initial_fund', models.PositiveIntegerField(verbose_name='موجود اولیه صندوق')),
                ('create_at', models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال/غیرفعال')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Unit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('unit', models.IntegerField(unique=True, verbose_name='واحد')),
                ('unit_phone', models.CharField(blank=True, max_length=8, null=True, verbose_name='')),
                ('floor_number', models.IntegerField()),
                ('area', models.IntegerField()),
                ('bedrooms_count', models.IntegerField()),
                ('parking_number', models.CharField(blank=True, max_length=10, null=True)),
                ('parking_count', models.IntegerField()),
                ('parking_place', models.CharField(blank=True, max_length=100, null=True, verbose_name='موقعیت پارکینگ ')),
                ('extra_parking_first', models.CharField(blank=True, max_length=100, null=True, verbose_name='موقعیت پارکینگ اول')),
                ('extra_parking_second', models.CharField(blank=True, max_length=100, null=True, verbose_name='موقعیت پارکینگ دوم')),
                ('unit_details', models.TextField(blank=True, null=True, verbose_name='توضیحات ساختمان')),
                ('owner_name', models.CharField(blank=True, max_length=100, null=True, verbose_name='نام مالک')),
                ('owner_mobile', models.CharField(max_length=11, verbose_name='همراه مالک')),
                ('owner_national_code', models.CharField(blank=True, max_length=10, null=True, verbose_name='کد ملی')),
                ('purchase_date', models.DateField(blank=True, null=True, verbose_name='تاریخ خرید')),
                ('owner_people_count', models.CharField(blank=True, max_length=10, null=True, verbose_name='تعداد نفرات مالک')),
                ('owner_details', models.TextField(blank=True, null=True, verbose_name='توضیحات مالک')),
                ('status_residence', models.CharField(blank=True, max_length=100, null=True, verbose_name='وضعیت سکونت')),
                ('is_owner', models.BooleanField(blank=True, default=False, null=True, verbose_name='مالک یا مستاجر')),
                ('people_count', models.IntegerField(blank=True, null=True, verbose_name='تعداد نفرات')),
                ('parking_counts', models.IntegerField(blank=True, null=True, verbose_name='تعداد پارکینگ اضافه')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='زمان ایجاد')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال/غیر فعال')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='کاربر')),
            ],
        ),
        migrations.CreateModel(
            name='Renter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('renter_name', models.CharField(blank=True, max_length=100, null=True, verbose_name='نام مستاجر')),
                ('renter_mobile', models.CharField(blank=True, max_length=11, null=True, verbose_name='همراه')),
                ('renter_national_code', models.CharField(blank=True, max_length=10, null=True, verbose_name='کد ملی')),
                ('renter_people_count', models.CharField(blank=True, max_length=10, null=True, verbose_name='تعداد نفرات')),
                ('start_date', models.DateField(blank=True, null=True, verbose_name='تاریخ شروع اجاره')),
                ('end_date', models.DateField(blank=True, null=True, verbose_name='تاریخ پایان اجاره')),
                ('contract_number', models.CharField(blank=True, max_length=100, null=True, verbose_name='شماره قرارداد')),
                ('estate_name', models.CharField(blank=True, max_length=100, null=True, verbose_name='نام مشاور املاک')),
                ('first_charge', models.IntegerField(blank=True, default=0, null=True, verbose_name='شارژ اولیه')),
                ('renter_details', models.TextField(blank=True, null=True, verbose_name='توضیحات مستاجر')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='')),
                ('renter_is_active', models.BooleanField(default=True, verbose_name='')),
                ('unit', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='renters', to='user_app.unit', verbose_name='واحد')),
            ],
        ),
    ]
