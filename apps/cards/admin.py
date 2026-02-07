from django.contrib import admin
from .models import *



@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'symbol', 'is_active', 'created_at')
    list_filter = ('is_active', )
    search_fields = ('code', 'name')
    ordering = ('code', )

@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('from_currency', 'to_currency', 'rate', 'date', 'created_at')
    list_filter = ('date', 'from_currency', 'to_currency')
    search_fields = ('from_currency__code', 'to_currency__code')
    date_hierarchy = 'date'
    ordering = ('-date', 'from_currency')

@admin.register(CardType)
class CardTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_international', 'is_active', 'created_at')
    list_filter = ('is_international', 'is_active')
    search_fields = ('name',)


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ('user', 'card_name', 'card_type', 'currency', 'balance', 'status', 'is_default', 'created_at')
    list_filter = ('status', 'is_default', 'card_type', 'currency')
    search_fields = ('user__username', 'user__email', 'card_name', 'card_number_last4')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('created_at', )

    fieldsets = (
        ('Card Information', {
            'fields': ('user', 'card_type', 'currency', 'card_name', 'card_number_last4', 'bank_name')
        }),
        ('Balance', {
            'fields': ('balance', 'initial_balance')
        }),
        ('Settings', {
            'fields': ('color', 'status', 'is_default')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )