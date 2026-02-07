from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from apps.accounts.models import CustomUser
from apps.cards.models import *

class Category(models.Model):
    CATEGORY_TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]

    ICON_CHOICES = [
        ('🍔', 'Food'),
        ('🚗', 'Transport'),
        ('🏠', 'Housing'),
        ('💰', 'Salary'),
        ('🎮', 'Entertainment'),
        ('🛒', 'Shopping'),
        ('💊', 'Healthcare'),
        ('📚', 'Education'),
        ('✈️', 'Travel'),
        ('💳', 'Bills'),
        ('🎁', 'Gifts'),
        ('👔', 'Business'),
        ('📱', 'Subscriptions'),
        ('🏋️', 'Fitness'),
        ('🎨', 'Hobbies'),
        ('📊', 'Investment'),
        ('🔧', 'Maintenance'),
        ('👨‍👩‍👧', 'Family'),
        ('🐕', 'Pets'),
        ('💅', 'Personal Care'),
        ('📦', 'Other'),
    ]

    COLOR_CHOICES = [
        ('#FF6B6B', 'Red'),
        ('#4ECDC4', 'Teal'),
        ('#45B7D1', 'Blue'),
        ('#FFA07A', 'Orange'),
        ('#98D8C8', 'Green'),
        ('#F7DC6F', 'Yellow'),
        ('#BB8FCE', 'Purple'),
        ('#85929E', 'Gray'),
        ('#E74C3C', 'Dark Red'),
        ('#3498DB', 'Sky Blue'),
    ]

    name = models.CharField(max_length=100, help_text="Category name (e.g., Food, Salary, Transport)")
    type = models.CharField(max_length=10, choices=CATEGORY_TYPE_CHOICES, help_text="Income or Expense")
    icon = models.CharField(max_length=10, choices=ICON_CHOICES, default='📦')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='categories', null=True, blank=True, help_text="If null, this is a default system category")
    parent_category = models.ForeignKey('self', on_delete=models.CASCADE, related_name='subcategories', null=True, blank=True, help_text="Parent category for creating subcategories")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['type', 'name']
        indexes = [
            models.Index(fields=['user', 'type', 'is_active']),
        ]
    
    def __str__(self):
        if self.parent_category:
            return f"{self.parent_category.name} > {self.name}"
        return self.name
    
    @property
    def is_default(self):
        return self.user is None
    
    @property
    def full_name(self):
        if self.parent_category:
            return f"{self.parent_category.name} - {self.name}"
        return self.name

class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='transactions')
    card = models.ForeignKey(Card, on_delete=models.PROTECT, related_name='transactions', help_text='Which card/wallet was used')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='transactions')
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], help_text="Amount in card's currenct")
    amount_in_user_currency = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Amount converted to user's default currency")
    exchange_rate_used = models.DecimalField(max_digits=20, decimal_places=6, default=1, help_text="Exchange rate at time of transaction")
    title = models.CharField(max_length=200, help_text="Short description (e.g., 'Grocery shopping')")
    description = models.TextField(blank=True, null=True, help_text="Additional notes or details'")
    date = models.DateField(default=timezone.now, help_text="Transaction date")
    receipt_image = models.ImageField(upload_to='receipt/%Y/%m/%d/', null=True, blank=True, help_text="Upload receipt photo")
    location = models.CharField(max_length=200, blank=True, null=True, help_text="Where the transaction occured")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transactions'
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', '-date']),
            models.Index(fields=['user', 'type', '-date']),
            models.Index(fields=['card', '-date']),
            models.Index(fields=['category', '-date']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title} ({self.amount} {self.card.currency.code})"
    
    def save(self, *args, **kwargs):
        user_currency = Currency.objects.get(code=self.user.default_currency)
        card_currency = self.card.currency

        if card_currency != user_currency:
            rate = ExchangeRate.get_latest_rate(card_currency, user_currency)
            if rate:
                self.exchange_rate_used = rate
                self.amount_in_user_currency = self.amount * rate
            else:
                self.exchange_rate_used = Decimal('1.0')
                self.amount_in_user_currency = self.amount
        else:
            self.exchange_rate_used = Decimal('1.0')
            self.amount_in_user_currency = self.amount

        is_new = self.pk is None

        if not is_new:
            old_transaction = Transaction.objects.get(pk=self.pk)
            if old_transaction.type == 'income':
                old_transaction.card.balance -= old_transaction.amount
            else:
                old_transaction.card.balance += old_transaction.amount
            old_transaction.card.save()

        super().save(*args, **kwargs)
        self.card.update_balance(self.amount, self.type)
    
    def delete(self, *args, **kwargs):
        if self.type == 'income':
            self.card.balance -= self.amount
        else:
            self.card.balance += self.amount
        self.card.save()

        super().delete(*args, **kwargs)

class TransactionTag(models.Model):
    name = models.CharField(max_length=50, help_text="Tag name (e.g., 'urgent', 'work', 'vacation')")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='tags', null=True, blank=True, help_text="If null, this is a default system tag")
    color = models.CharField(max_length=7, default='#4ECDC4', help_text="Tag color for UI (hex code)")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'transaction_tags'
        verbose_name = 'Transaction Tag'
        verbose_name_plural = 'Transaction Tags'
        ordering = ['name']
        unique_together = ['name', 'user']
    
    def __str__(self):
        return f"#{self.name}"
    
    @property
    def is_default(self):
        return self.user is None

class TransactionTagRelation(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='transaction_tags')
    tag = models.ForeignKey(TransactionTag, on_delete=models.CASCADE, related_name='tagged_transactions')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'transaction_tag_relations'
        verbose_name = 'Transaction-Tag Relation'
        verbose_name_plural = 'Transaction-Tag Relations'
        unique_together = ['transaction', 'tag']
    
    def __str__(self):
        return f"{self.transaction.title} - {self.tag.name}"


















# Creating Default Categories (One-time setup)

# from transactions.models import Category

# # Income categories
# income_categories = [
#     Category(name='Salary', type='income', icon='💰', color='#98D8C8'),
#     Category(name='Freelance', type='income', icon='💼', color='#45B7D1'),
#     Category(name='Business', type='income', icon='👔', color='#4ECDC4'),
#     Category(name='Investment', type='income', icon='📊', color='#F7DC6F'),
#     Category(name='Gift', type='income', icon='🎁', color='#BB8FCE'),
#     Category(name='Other Income', type='income', icon='💵', color='#85929E'),
# ]

# # Expense categories
# expense_categories = [
#     Category(name='Food', type='expense', icon='🍔', color='#FF6B6B'),
#     Category(name='Transport', type='expense', icon='🚗', color='#FFA07A'),
#     Category(name='Shopping', type='expense', icon='🛒', color='#E74C3C'),
#     Category(name='Entertainment', type='expense', icon='🎮', color='#BB8FCE'),
#     Category(name='Bills', type='expense', icon='💳', color='#85929E'),
#     Category(name='Healthcare', type='expense', icon='💊', color='#FF6B6B'),
#     Category(name='Education', type='expense', icon='📚', color='#3498DB'),
#     Category(name='Travel', type='expense', icon='✈️', color='#45B7D1'),
#     Category(name='Housing', type='expense', icon='🏠', color='#98D8C8'),
#     Category(name='Subscriptions', type='expense', icon='📱', color='#4ECDC4'),
#     Category(name='Other Expense', type='expense', icon='📦', color='#85929E'),
# ]

# Category.objects.bulk_create(income_categories + expense_categories)





# Creating Subcategories
# # Get parent category
# food = Category.objects.get(name='Food', user=None)

# # Create subcategories
# Category.objects.create(
#     name='Groceries',
#     type='expense',
#     icon='🛒',
#     parent_category=food
# )

# Category.objects.create(
#     name='Restaurants',
#     type='expense',
#     icon='🍽️',
#     parent_category=food
# )

# Category.objects.create(
#     name='Fast Food',
#     type='expense',
#     icon='🍕',
#     parent_category=food
# )











# Creating Default Tags (One-time setup)
# from transactions.models import TransactionTag

# default_tags = [
#     TransactionTag(name='urgent', color='#FF6B6B'),
#     TransactionTag(name='work', color='#4ECDC4'),
#     TransactionTag(name='personal', color='#45B7D1'),
#     TransactionTag(name='family', color='#98D8C8'),
#     TransactionTag(name='vacation', color='#FFA07A'),
#     TransactionTag(name='investment', color='#F7DC6F'),
#     TransactionTag(name='business', color='#BB8FCE'),
#     TransactionTag(name='gift', color='#E74C3C'),
#     TransactionTag(name='luxury', color='#F7DC6F'),
#     TransactionTag(name='essential', color='#85929E'),
# ]

# TransactionTag.objects.bulk_create(default_tags)