from rest_framework import serializers
from .models import *
from decimal import Decimal




class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ['id', 'code', 'name', 'symbol', 'is_active', 'created_at']
        read_only_fields = ['created_at']


class ExchangeRateSerializer(serializers.ModelSerializer):
    from_currency_code= serializers.CharField(source='from_currency.code', read_only = True)
    from_currency_name= serializers.CharField(source='from_currency.name', read_only = True)
    to_currency_code= serializers.CharField(source='to_currency.code', read_only = True)
    to_currency_name= serializers.CharField(source='to_currency.name', read_only = True)

    class Meta:
        model = ExchangeRate
        fields = ['id', 'from_currency', 'from_currency_code', 'from_currency_name', 'to_currency', 'to_currency_code', 'to_currency_name', 'rate', 'date', 'created_at']
        read_only_fields = ['created_at']







class CardTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardType
        fields = ['id', 'name', 'logo', 'is_international', 'is_active', 'created_at']
        read_only_fields = ['created_at']



class CardSerializer(serializers.ModelSerializer):
    card_type_name = serializers.CharField(source = 'card_type.name', read_only = True)
    card_type_logo = serializers.ImageField(source = 'card_type.logo', read_only = True)
    currency_code = serializers.CharField(source = 'currency.code', read_only = True)
    currency_symbol = serializers.CharField(source = 'currency.symbol', read_only = True)

    class Meta:
        model= Card
        fields = ['id', 'card_name', 'card_type', 'card_type_name', 'card_type_logo', 'currency', 'currency_code', 'currency_symbol', 'balance', 'card_number_last4', 'bank_name', 'color', 'status', 'is_default', 'created_at']




class CardDetailSerializer(serializers.ModelSerializer):
    card_type_name = serializers.CharField(source='card_type.name', read_only=True)
    card_type_logo = serializers.CharField(source='card_type.logo', read_only=True)
    card_type_is_international = serializers.BooleanField(source = 'card_type.is_international', read_only=True)
    currency_code =serializers.CharField(source='currency.code', read_only=True)
    currency_name =serializers.CharField(source='currency.name', read_only=True)
    currency_symbol =serializers.CharField(source='currency.symbol', read_only=True)
    transaction_count = serializers.SerializerMethodField()

    class Meta:
        model = Card
        fields = ['id', 'card_name', 'card_type_name', 'card_type_logo', 'card_type_is_international',
                  'currency', 'currency_code', 'currency_name', 'currency_symbol',
                  'balance', 'initial_balance', 'card_number_last4', 'bank_name',
                  'color', 'status', 'is_default', 'transaction_count', 'created_at', 'updated_at'
        ]

    def get_transaction_count(self, obj):
        return obj.transactions.count()




class CardCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Card
        fields = [
            'card_type', 'currency', 'card_name', 'card_number_last4', 'balance', 'initial_balance', 'bank_name', 'color', 'status', 'is_default'

        ]
    
    def validate_card_number_last4(self, value):
        if value and (not value.isdigit() or len(value) != 4):
            raise serializers.ValidationError('Card number last 4 digits must be exactly 4 digits')
        return value
    
    def validate(self, data):
        if 'initial_balance' not in data and 'balance' in data:
            data['initial_balance'] = data['balance']   

        return data     




class CardBalanceUpdateSerializer(serializers.Serializer):
    new_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    reason = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate_new_balance(self, value):
        if value< 0:
            raise serializers.ValidationError("Balance cannot be negative")
        return value



class CurrencyConversionSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    from_currency = serializers.CharField(max_length =3)
    to_currency = serializers.CharField(max_length =3)


    def validate_amount(self, value):
        if value<=0: 
            raise serializers.ValidationError("AMount must be greater than 0")
        return value
    
