from django.contrib import admin
from .models import *


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'icon', 'user', 'parent_category', 'is_active', 'created_at')
    list_filter = ('type', 'is_active', 'user')
    search_fields = ('name',)
    ordering = ('type', 'name')


class TransactionTagInline(admin.TabularInline):
    model = TransactionTagRelation
    extra = 1


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'type', 'amount', 'card', 'category', 'date', 'created_at')
    list_filter = ('type', 'date', 'category', 'card')
    search_fields = ('title', 'description', 'user__username')
    date_hierarchy = 'date'
    readonly_fields = ('amount_in_user_currency', 'exchange_rate_used', 'created_at', 'updated_at')
    inlines = [TransactionTagInline]
    ordering = ('-date', '-created_at')

    fieldsets = (
        ('Basic Info', {
            "fields": ( 'user', 'card', 'category', 'type')
        }),
        ('Amount', {
            "fields": ('amount', 'amount_in_user_currency', 'exchange_rate_used')
        }),
        ('Details', {
            "fields": ('title', 'description', 'date', 'location', 'receipt_image')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    

@admin.register(TransactionTag)
class TransactiontagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'user', 'created_at')
    list_filter = ('user',)
    search_fields = ('name', )
    ordering = ('name', )

@admin.register(TransactionTagRelation)
class TransactionTagRelationAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'tag', 'created_at')
    list_filter = ('tag',)
    search_fields = ('transaction__title', 'tag__name')
    ordering = ('-created_at',)

