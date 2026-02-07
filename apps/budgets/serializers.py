from rest_framework import serializers
from .models import Budget
from transactions.models import Category
from cards.models import Currency


class BudgetSerializer(serializers.ModelSerializer):
    """Serializer for listing budgets"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True)
    
    class Meta:
        model = Budget
        fields = [
            'id', 'name', 'category', 'category_name', 'category_icon', 'category_color',
            'amount', 'currency', 'currency_code', 'currency_symbol',
            'period', 'alert_threshold', 'is_active', 'created_at'
        ]


class BudgetDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single budget"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    category_type = serializers.CharField(source='category.type', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)
    currency_name = serializers.CharField(source='currency.name', read_only=True)
    currency_symbol = serializers.CharField(source='currency.symbol', read_only=True)
    spent_amount = serializers.SerializerMethodField()
    percentage_used = serializers.SerializerMethodField()
    is_over_budget = serializers.SerializerMethodField()
    
    class Meta:
        model = Budget
        fields = [
            'id', 'name', 
            'category', 'category_name', 'category_icon', 'category_color', 'category_type',
            'amount', 'currency', 'currency_code', 'currency_name', 'currency_symbol',
            'period', 'alert_threshold', 'is_active',
            'spent_amount', 'percentage_used', 'is_over_budget',
            'created_at', 'updated_at'
        ]
    
    def get_spent_amount(self, obj):
        """Get current spending for this budget"""
        return obj.get_spent_amount()
    
    def get_percentage_used(self, obj):
        """Get percentage of budget used"""
        return obj.get_percentage_used()
    
    def get_is_over_budget(self, obj):
        """Check if budget is exceeded"""
        return obj.is_over_budget()


class BudgetCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating budgets"""
    
    class Meta:
        model = Budget
        fields = [
            'name', 'category', 'amount', 'currency',
            'period', 'alert_threshold', 'is_active'
        ]
    
    def validate_category(self, value):
        """Ensure category is expense type"""
        if value.type != 'expense':
            raise serializers.ValidationError(
                "Budgets can only be created for expense categories"
            )
        return value
    
    def validate_alert_threshold(self, value):
        """Ensure threshold is between 1 and 100"""
        if value < 1 or value > 100:
            raise serializers.ValidationError(
                "Alert threshold must be between 1 and 100"
            )
        return value
    
    def validate(self, data):
        """Additional validations"""
        # Auto-generate name if not provided
        if 'name' not in data or not data['name']:
            period = data.get('period', 'monthly')
            category_name = data['category'].name
            data['name'] = f"{period.capitalize()} {category_name} Budget"
        
        return data


class BudgetProgressSerializer(serializers.Serializer):
    """Serializer for budget progress details"""
    budget = BudgetSerializer()
    spent = serializers.DecimalField(max_digits=15, decimal_places=2)
    remaining = serializers.DecimalField(max_digits=15, decimal_places=2)
    percentage_used = serializers.DecimalField(max_digits=5, decimal_places=2)
    is_over_budget = serializers.BooleanField()
    days_remaining = serializers.IntegerField()