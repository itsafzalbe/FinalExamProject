from django.contrib import admin
from .models import *



@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'category', 'amount', 'currency', 'period', 'status', 'start_date', 'created_at')
    list_filter = ('status', 'period', 'is_recurring', 'category')
    search_fields = ('user__username', 'name', 'category__name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at', )

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'category', 'name')
        }),
        ('Budget Settings', {
            'fields': ('amount', 'currency', 'period', 'start_date', 'end_date')
        }),
        ('Alert Settings', {
            'fields': ('alert_threshold', 'alert_sent')
        }),
        ('Status', {
            'fields': ('status', 'is_recurring')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    
    )

@admin.register(BudgetAlert)
class BudgetAlertAdmin(admin.ModelAdmin):
    list_display = ('budget', 'alert_type', 'spent_amount', 'percentage_used', 'is_read', 'created_at')
    list_filter = ('alert_type', 'is_read', 'created_at')
    search_fields = ('budget__name', 'budget__user__username', 'message')
    readonly_fields = ('created_at', )
    ordering = ('-created_at', )

@admin.register(BudgetHistory)
class BudgetHistoryAdmin(admin.ModelAdmin):
    list_display = ('budget', 'period_start', 'period_end', 'budget_amount', 'spent_amount', 'percentage_used', 'was_exceeded')
    list_filter = ('was_exceeded', 'period_end')
    search_fields = ('budget__name', 'budget__user__username')
    readonly_fields = ('created_at', )
    ordering = ('-period_end', )
