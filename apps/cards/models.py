from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.accounts.models import CustomUser

class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True, help_text="Currency code (e.g., USD, UZS, EUR)")
    name = models.CharField(max_length=50, help_text="Full currency name (e.g., Us Dollar)")
    symbol = models.CharField(max_length=10, help_text="Currency symbol (e.g., $, so'm, €)")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'currencies'
        verbose_name = 'Currency'
        verbose_name_plural = 'Currencies'
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class ExchangeRate(models.Model):
    from_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='rates_from')
    to_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='rates_to')
    rate = models.DecimalField(max_digits=20, decimal_places=6, validators=[MinValueValidator(Decimal('0.000001'))], help_text="Exchange rate: 1 from_currency = X to_currency")
    date = models.DateField(help_text="Date when this rate was recored")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'exchange_rates'
        verbose_name = 'Exchange Rate'
        verbose_name_plural = 'Exchange Rates'
        ordering = ['-date', 'from_currency', 'to_currency']
        unique_together = ['from_currency', 'to_currency', 'date']
        indexes = [
            models.Index(fields=['from_currency', 'to_currency', '-date']),
        ]

    def __str__(self):
        return f"1 {self.from_currency.code} = {self.rate} {self.to_currency.code} ({self.date})"
    
    @classmethod
    def get_latest_rate(cls, from_currency, to_currency):
        if from_currency == to_currency:
            return Decimal('1.0')
        
        rate = cls.objects.filter(
            from_currency=from_currency,
            to_currency = to_currency
        ).order_by('-date').first()

        if rate:
            return rate.rate
        
        reverse_rate = cls.objects.filter(
            from_currency=to_currency,
            to_currency=from_currency
        ).order_by('-date').first()

        if reverse_rate:
            return Decimal('1.0')/reverse_rate.rate
        
        return None
    
    @classmethod
    def convert(cls, amount, from_currency, to_currency):
        if from_currency == to_currency:
            return amount
        
        rate = cls.get_latest_rate(from_currency, to_currency)

        if rate:
            return amount * rate
        
        return None

# Data must be entered by admin before publishing
class CardType(models.Model):
    name = models.CharField(
        max_length=50, 
        unique=True,
        help_text="Card type name (e.g., Humo, Visa, Cash)"
    )

    logo = models.ImageField(
        upload_to='card_logos/',
        null= True,
        blank=True,
        help_text="Card brand logo"
    )
    is_international = models.BooleanField(
        default=False,
        help_text="True for Visa/Mastercard, False for Humo/Uzcard"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'card_types'
        verbose_name = 'Card Type'
        verbose_name_plural = 'Card Types'
        ordering = ['name']

    def __str__(self):
        return self.name

class Card(models.Model):
    CARD_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('blocked', 'Blocked'),
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
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='cards')
    card_type = models.ForeignKey(CardType, on_delete=models.PROTECT, related_name='cards')
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='cards')
    card_name = models.CharField(max_length=100, help_text="Custom name for the card (e.g., 'My Main Waller')")
    card_number_last4 = models.CharField(max_length=4, blank=True, null=True, help_text="Last 4 digits of card number (optional, for identification)")
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Current balance in card's currency")
    initial_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Starting balance when card was created")
    bank_name = models.CharField(max_length=100, blank=True, null=True, help_text="Bank name (e.g., TBC Bank, Kapitalbank)")
    color = models.CharField(max_length=7, choices=COLOR_CHOICES, default='#4ECDC4', help_text="Color for UI display (hex code)")
    status = models.CharField(max_length=10, choices=CARD_STATUS_CHOICES, default='active')
    is_default = models.BooleanField(default=False, help_text="Default card for transactions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cards'
        verbose_name = 'Card'
        verbose_name_plural = 'Cards'
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'is_default']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.card_name} ({self.currency.code})"
    
    def get_balance_in_currency(self, target_currency):
        if self.currency == target_currency:
            return self.balance
        
        return ExchangeRate.convert(self.balance, self.currency, target_currency)
    
    def update_balance(self, amount, transaction_type):
        if transaction_type == 'income':
            self.balance += amount
        elif transaction_type == 'expenxe':
            self.balance -= 'amount'
        
        self.save()

    def can_withdraw(self, amount):
        return self.balance >= amount
    
    def save(self, *args, **kwargs):
        if self.is_default:
            Card.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        
        super().save(*args, **kwargs)













#Creating Currencies (One-time setup)
# from cards.models import Currency

# # Create common currencies
# currencies = [
#     Currency(code='UZS', name='Uzbekistan Sum', symbol="so'm"),
#     Currency(code='USD', name='US Dollar', symbol='$'),
#     Currency(code='EUR', name='Euro', symbol='€'),
#     Currency(code='RUB', name='Russian Ruble', symbol='₽'),
#     Currency(code='KZT', name='Kazakhstani Tenge', symbol='₸'),
#     Currency(code='TRY', name='Turkish Lira', symbol='₺'),
# ]
# Currency.objects.bulk_create(currencies)




#Creating Card Types (One-time setup)
# from cards.models import CardType

# card_types = [
#     CardType(name='Humo', is_international=False),
#     CardType(name='Uzcard', is_international=False),
#     CardType(name='Visa', is_international=True),
#     CardType(name='Mastercard', is_international=True),
#     CardType(name='Cash', is_international=False),
#     CardType(name='Savings', is_international=False),
# ]
# CardType.objects.bulk_create(card_types)



# Creating Exchange Rates
# from cards.models import Currency, ExchangeRate
# from datetime import date
# from decimal import Decimal

# usd = Currency.objects.get(code='USD')
# uzs = Currency.objects.get(code='UZS')
# eur = Currency.objects.get(code='EUR')
# rub = Currency.objects.get(code='RUB')

# # Create exchange rates for today
# ExchangeRate.objects.create(
#     from_currency=usd,
#     to_currency=uzs,
#     rate=Decimal('12650.00'),
#     date=date.today()
# )

# ExchangeRate.objects.create(
#     from_currency=eur,
#     to_currency=uzs,
#     rate=Decimal('13800.00'),
#     date=date.today()
# )

# ExchangeRate.objects.create(
#     from_currency=rub,
#     to_currency=uzs,
#     rate=Decimal('135.00'),
#     date=date.today()
# )









