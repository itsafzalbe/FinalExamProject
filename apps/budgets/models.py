from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from apps.accounts.models import *
from apps.cards.models import *
from apps.transactions.models import *




class Budget(models.Model):
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('exceeded', 'Exceeded'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="budgets")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='budgets', help_text="Budget applies to this category")
    name = models.CharField(max_length=200, help_text="Budget name (e.g., 'Weekly Food Budget')")
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], help_text="Maximum amount allowed for this period")
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="budgets", help_text="Currency for this budget")
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default='monthly', help_text="Budget reset period")
    start_date = models.DateField(help_text="When this budget starts")
    end_date = models.DateField(null=True, blank=True, help_text="When this budget ends (optional for recurring budgets)")
    alert_threshold = models.IntegerField(default=80, validators=[MinValueValidator(1), MaxValueValidator(100)], help_text="Send alert when this percentage is reached (e.g., 78%)")
    alert_sent = models.BooleanField(default=False, help_text="Whether alert has been sent for current period")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    is_recurring = models.BooleanField(default=True, help_text="If true, budget resets automatically each period")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'budgets'
        verbose_name = 'Budget'
        verbose_name_plural = 'Budgets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'period', 'start_date']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.name} ({self.amount} {self.currency.code})"
    
    def get_current_period_start(self):
        today = timezone.now().date()

        if self.period == 'daily':
            return today
        elif self.period == 'weekly':
            days_since_monday = today.weekday()
            return today - timedelta(days=days_since_monday)
        elif self.period == 'monthly':
            return today.replace(day=1)
        elif self.period == 'yearly':
            return today.replace(month=1, day=1)
        return self.start_date
    
    def get_current_period_end(self):
        period_start = self.get_current_period_end()

        if self.period == 'daily':
            return period_start
        elif self.period == 'weekly':
            return period_start + timedelta(days=6)
        elif self.period == 'monthly':
            if period_start.month == 12:
                next_month = period_start.replace(year=period_start.year +1, month =1, day =1)
            else:
                next_month = period_start.replace(month=period_start.month +1 , day=1)
            return next_month - timedelta(days=1)
        elif self.period =='yearly':
            return period_start.replace(month =12, day =31)
        
        return self.end_date or timezone.now().date()
    
    def get_spent_amount(self):
        from transactions.models import Transaction
        from cards.models import ExchangeRate

        period_start = self.get_current_period_start()
        period_end = self.get_current_period_end()

        transactions = Transaction.objects.filter(user = self.user, category= self.category, type='expense', date__gte=period_start, date_lte = period_end)

        total = Decimal('0.00')

        for transaction in transactions:
             
            if transaction.card.currency == self.currency:
                total += transaction.amount
            else:
                 convert = ExchangeRate.convert(transaction.amount, transaction.card.currency, self.currency)

                 if convert:
                      total += convert
        return total
    
    def get_remaining_amount(self):
        spent = self.get_spent_amount()
        return self.amount - spent
    
    def get_percentage_used(self):
        if self.amount == 0:
            return 0
        
        spent = self.get_spent_amount()
        percentage = (spent/self.amount) *100
        return round(percentage, 2)
    
    def is_exceeded(self):
        return self.get_spent_amount() > self.amount
    
    def should_send_alert(self):
        if self.alert_sent:
            return False
        percentage = self.get_percentage_used()
        return percentage >= self.alert_threshold
    
    def reset_for_new_period(self):
        self.alert_sent = False
        self.save()

    def update_status(self):
        if self.status == 'paused':
            return
        if self.is_exceeded():
            self.status = 'exceeded'
        
        elif self.end_date and timezone.now().date() > self.end_date:
            self.status = 'completed'

        else:
            self.status = 'active'
        

        self.save()
    


class BudgetAlert(models.Model):
    ALERT_TYPE_CHOICES = [
        ('threshold', 'Threshold Reached'),
        ('exceeded', 'Budget Exceeded'),
        ('near_end', 'Near Period End'),
    ]
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    message = models.TextField(help_text="Alert message sent to user")

    spent_amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="Amount spent when alert was triggered")
    percentage_used = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage of budget used when alert was triggered")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'budget_alerts'
        verbose_name = 'Budget Alert'
        verbose_name_plural = 'Budget Alerts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['budget', '-created_at']),
            models.Index(fields=['budget', 'is_read'])
        ]
    
    def __str__(self):
        return f" {self.budget.name } - {self.alert_type}, ({self.created_at.strftime('%Y-%m-%d')})"
    
class BudgetHistory(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='history')
    period_start = models.DateField()
    period_end = models.DateField()
    budget_amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="Budget limit for this period")
    spent_amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="Total spent during this period")
    remaining_amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="Amount remaining at period end")
    percentage_used = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage of budget used")
    was_exceeded = models.BooleanField(default=False, help_text="Whether budget was exceeded in this period")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'budget_history'
        verbose_name = 'Budget History'
        verbose_name_plural = 'Budget Histories'
        ordering = ['-period_end']
        indexes = [ models.Index(fields= ['budget', '-period_end']) ]

    
    def __str__(self):
        return f"{ self.budget.name}- {self.period_start} to {self.period_end}"
    
    @classmethod
    def create_snapshot(cls, budget):
        return cls.objects.create(
            budget=budget,
            period_start = budget.get_current_period_start(),
            period_end = budget.get_current_period_end(),
            budget_amount = budget.amount,
            spent_amount = budget.get_spent_amount(),
            remaining_amount = budget.get_remaining_amount(),
            percentage_used = budget.get_percentage_used(),
            was_exceeded = budget.is_exceeded()
        )