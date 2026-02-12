from rest_framework import serializers
from .models import SuppportMessage


class SupportSerializer(serializers.ModelSerializer):

    class Meta:
        model = SuppportMessage
        fields = "__all__"
        read_only_fields = ("user", "is_admin_reply", "is_read", "created_at")

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["user"] = validated_data.get("user", request.user)
        return SuppportMessage.objects.create(**validated_data)