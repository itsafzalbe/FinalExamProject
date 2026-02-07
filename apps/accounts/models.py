from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.timezone import now
from django.core.validators import RegexValidator
import uuid
import random
from datetime import timedelta 
from rest_framework_simplejwt.tokens import RefreshToken

NEW = 'new'
CODE_VERIFIED = 'code_verified'
DONE = 'done'

class CustomUser(AbstractUser):
    AUTH_STATUS_CHOICES = (
        (NEW, "NEW"),
        (CODE_VERIFIED, "CODE_VERIFIED"),
        (DONE, "DONE"),
    )

    CURRENCY_CHOICES = [
        ('UZS', 'Uzbekistan Sum'),
        ('USD', 'US Dollar'),
        ('EUR', 'Euro')
    ]

    email = models.EmailField(unique=True, db_index= True)
    username = models.CharField(max_length =150, unique =True, db_index = True)
    auth_status = models.CharField(max_length=20, choices= AUTH_STATUS_CHOICES, default=NEW)
    auth_status = models.CharField(max_length=20, choices= AUTH_STATUS_CHOICES, default=NEW)

    phone_regex = RegexValidator(
        regex=r"^\+998\d{9}$",
        message = "Phone number must be entered in the format: '+998912345678'"
    )

    phone_number = models.CharField(
        validators = [phone_regex],
        max_length = 20,
        blank = True,
        null = True
    )

    date_of_birth = models.DateField(blank=True, null=True)
    default_currency = models.CharField(
        max_length = 3,
        choices = CURRENCY_CHOICES,
        default = 'UZS'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FILEDS = ['email']

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username

    def generate_verification_code(self):
        code = ''.join([str(random.randint(0, 9)) for _ in range(4)])

        EmailVerification.objects.filter(
            user = self,
            is_verified = False
        ).delete()

        EmailVerification.objects.create(
            user = self,
            code = code
        )

        return code

    def generate_username(self):
        if not self.username or self.username.startswith('user_'):
            base_username = f"user_{uuid.uuid4().hex[:8]}"
            username = base_username
            counter = 1

            while CustomUser.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            self.username = username

    def get_tokens(self):
        refresh = RefreshToken.for_user(self)
        return {
                'access': str(refresh.access_token),
                'refresh': str(refresh)
        }

    def can_resend_code(self):
        last_code = EmailVerification.objects.filter(
            user =self,
            is_verified= False
        ).order_by('-created_at').first()

        if not last_code:
            return True

        time_passed = now() - last_code.created_at
        return time_passed.total_seconds() > 120

    def verify_code(self, code):
        verification = EmailVerification.objects.filter(
            user= self,
            code=code,
            is_verified = False
        ).order_by('-created_at').first()

        if not verification:
            return False

        if verification.is_expired():
            return False

        verification.is_verified = True
        verification.save()

        self.auth_status = CODE_VERIFIED
        self.save()

        return True

    def complete_registration(self, username=None, first_name=None, last_name=None, password=None, phone_number=None, date_of_birth=None):
        if self.auth_status != CODE_VERIFIED:
            raise ValueError("Email must be verified before completing registration")

        if username:
            self.username = username
        if first_name:
            self.first_name = first_name
        if last_name:
            self.last_name = last_name
        if phone_number:
            self.phone_number = phone_number
        if date_of_birth:
            self.date_of_birth = date_of_birth

        if password:
            self.set_password(password)

        self.auth_status = DONE
        self.save()

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()

        if not self.pk:
            self.generate_username()

        super().save(*args, **kwargs)


class EmailVerification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='verification_codes')
    code = models.CharField(max_length =4)
    is_verified = models.BooleanField(default= False)
    expiration_time= models.DateTimeField(null=True, blank =True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'email_verifications'
        verbose_name = 'Email Verification'
        verbose_name_plural = 'Email Verifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.code}"

    def is_expired(self):
        if not self.expiration_time:
            return True
        return now() > self.expiration_time

    def save(self, *args, **kwargs):
        if not self.pk:
            self.expiration_time = now() + timedelta(minutes = 2)
        super().save(*args, **kwargs)
