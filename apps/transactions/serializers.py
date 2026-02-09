from rest_framework import serializers
from .models import *



class CategorySerializer(serializers.ModelSerializer):
    is_default = serializers.ReadOnlyField()
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Category 
        fields = ['id', 'name', 'type', 'icon', 
            'parent_category', 'is_default', 'full_name',
            'is_active', 'created_at']
        read_only_fields= ['created_at']


class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['name', 'type', 'icon', 'parent_category', 'is_active']

    def validate_parent_category(self, value):
        if value:
            request = self.context.get('request')
            if value.user and value.user != request.user:
                raise serializers.ValidationError("Cannot use another user's category as parent")
        return value





class TransactionTagSerializer(serializers.ModelSerializer):
    is_default = serializers.ReadOnlyField()

    class Meta:
        model = TransactionTag
        fields = ['id', 'name', 'color', 'is_default', 'created_at']
        read_only_fields = ['created_at']


class TransactionSerializer(serializers.ModelSerializer):
    card_name = serializers.CharField(source = 'card.card_name', read_only = True)
    card_currency = serializers.CharField(source = 'card.currency.code', read_only = True)
    category_name = serializers.CharField(source = 'category.name', read_only = True)
    category_icon = serializers.CharField(source = 'category.icon', read_only = True)
    category_color = serializers.CharField(source = 'category.color', read_only = True)
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields= ['id', 'type', 'title', 'amount', 'date', 'card', 'card_name', 'card_currency', 'category', 'category_name', 'category_icon', 'category_color', 'amount_in_user_currency', 'tags', 'created_at']


    def get_tags(self, obj):
        tag_relations = obj.transaction_tags.all()
        return TransactionTagSerializer([relation.tag for relation in tag_relations], many = True).data


class TransactionDetailSerializer(serializers.ModelSerializer):
    card_name = serializers.CharField(source = 'card.card_name', read_only = True)
    card_currency = serializers.CharField(source = 'card.currency.code', read_only = True)
    card_type = serializers.CharField(source = 'card.card_type.name', read_only = True)

    category_name = serializers.CharField(source = 'category.name', read_only = True)
    category_icon = serializers.CharField(source = 'category.icon', read_only = True)
    category_color = serializers.CharField(source = 'category.color', read_only = True)
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            'id', 'type', 'title', 'description', 'amount', 'date',
            'card', 'card_name', 'card_currency', 'card_type','category', 'category_name', 'category_icon', 'category_color',
            'amount_in_user_currency', 'exchange_rate_used', 'receipt_image', 'location', 'tags', 'created_at', 'updated_at'
        ]

    def get_tags(self, obj):
        tag_relations = obj.transaction_tags.all()
        return TransactionTagSerializer([relation.tag for relation in tag_relations], many = True).data

    




class TransactionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['card', 'category', 'type', 'amount', 'title', 'description', 'date', 'receipt_image', 'location']

    def validate_card(self, value):
        request= self.context.get('request')
        if value.user != request.user:
            raise serializers.ValidationError("You can only create transaction for your ownn cards ")
        return value
    
    def validate(self, data):
        if data['category'].type != data['type']:
            raise serializers.ValidationError({
                'category': f"Category type must match transaction type ({data['type']})"
            })
        
        if data['type'] == 'expense':
            card = data['card']
            if not card.can_withdraw(data['amount']):
                raise serializers.ValidationError({'amount': f"Insufficient balance. Card has {card.balance} {card.currency.code}"})
        return data




class TransactionStatisticsSerializer(serializers.Serializer):
    period =  serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    currency = serializers.CharField()
    total_income = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_expense = serializers.DecimalField(max_digits=15, decimal_places=2)
    net = serializers.DecimalField(max_digits=15, decimal_places=2)
    income_count = serializers.IntegerField()
    expense_count = serializers.IntegerField()
    total_transactions = serializers.IntegerField()

