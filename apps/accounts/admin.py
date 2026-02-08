from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, EmailVerification


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    # Columns shown in user list
    list_display = (
        'id',
        'username',
        'email',
        'auth_status',
        'default_currency',
        'is_staff',
        'is_active',
        'created_at',
    )

    # Filters on the right
    list_filter = (
        'auth_status',
        'is_staff',
        'is_active',
        'default_currency',
        'created_at',
    )

    # Search box
    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name',
        'phone_number',
    )

    ordering = ('-created_at',)

    # Read-only fields
    readonly_fields = (
        'created_at',
        'updated_at',
        'last_login',
    )

    # User edit form layout
    fieldsets = (
        (None, {
            'fields': ('username', 'email', 'password')
        }),
        ('Personal Info', {
            'fields': (
                'first_name',
                'last_name',
                'phone_number',
                'date_of_birth',
                'default_currency',
            )
        }),
        ('Authentication Status', {
            'fields': ('auth_status',)
        }),
        ('Permissions', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            )
        }),
        ('Important Dates', {
            'fields': ('last_login', 'created_at', 'updated_at')
        }),
    )

    # Add user form layout
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'username',
                'password1',
                'password2',
                'auth_status',
                'is_staff',
                'is_active',
            ),
        }),
    )


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'code',
        'is_verified',
        'created_at',
        'expiration_time',
    )

    list_filter = (
        'is_verified',
        'created_at',
    )

    search_fields = (
        'user__email',
        'code',
    )

    readonly_fields = (
        'created_at',
    )

    ordering = ('-created_at',)