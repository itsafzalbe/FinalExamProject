from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.cards.models import *


class CardTransfer(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='card_transfers')
    from_card = models.ForeignKey('cards.Card', on_delete=models.PROTECT, related_name='outgoing_transfers')
    to_card = models.ForeignKey('cards.Card', on_delete=models.PROTECT, related_name='incoming_transfers')
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=6, null=True, blank=True,
                                        help_text='Rate used to convert from source to destination currency')
    converted_amount = models.DecimalField(max_digits=15, decimal_places=2,
                                           help_text='Amount received in destination card currency')
    description = models.CharField(max_length=255, blank=True, null=True, help_text="Optional note about this transfer")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Card Transfer'
        verbose_name_plural = 'Card Transfers'

    def __str__(self):
        return f"Transfer: {self.from_card.card_name} -> {self.to_card.card_name} ({self.amount})"

    def save(self, *args, **kwargs):
        if self.from_card.currency != self.to_card.currency:
            from apps.cards.models import ExchangeRate

            rate = self.exchange_rate or ExchangeRate.get_latest_rate(
                self.from_card.currency,
                self.to_card.currency
            )

            if not rate:
                raise ValueError("Exchange rate not found")

            self.exchange_rate = rate
            self.converted_amount = self.amount * rate

        else:
            self.exchange_rate = Decimal('1.000000')
            self.converted_amount = self.amount

        if not self.pk:
            self.from_card.balance -= self.amount
            self.from_card.save()

            self.to_card.balance += self.converted_amount
            self.to_card.save()

        super().save(*args, **kwargs)

    def get_fee_amount(self):
        return Decimal('0.00')

    def is_same_currency(self):
        return self.from_card.currency == self.to_card.currency

