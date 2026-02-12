from rest_framework import serializers
from decimal import Decimal
from .models import *



class TransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardTransfer
        fields = "__all__"
        read_only_fields = ('user', 'exchange_rate', 'converted_amount', 'created_at')

    def validate(self, data):
        request = self.context['request']
        user = request.user

        from_card = data.get('from_card')
        to_card = data.get('to_card')
        amount = data.get('amount')

        if from_card.user != user or to_card.user != user:
            raise serializers.ValidationError("Invalid card")

        if from_car  == to_card:
            raise serializers.ValidationError("Cannot transfer to the same card")

        if amount< Decimal('0.01'):
            raise serializers.ValidationError("Minimum amount to transfer is 0.01")

        if amount > from_card.balance:
            raise serializers.ValidationError("Insufficient funds")

        return  data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return CardTransfer.objects.create(**validated_data)
