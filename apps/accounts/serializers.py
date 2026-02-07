from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser


class UserProfileSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=False, allow_blank=True)
    default_currency = serializers.CharField(required = False)
    timezone = serializers.CharField(required =False)
    date_of_birth = serializers.DateField(required = False, allow_null =True)



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'phone_number', 'date_of_birth', 'default_currency', 'auth_status', 'created_at'
        ]
        read_only_fields= ['id', 'email', 'auth_status', 'created_at']



class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    def validate_email(self, value):
        return value.lower()

class VerifyCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length = 4, min_length =4)

    def validate_email(self, value):
        return value.lower()
    

class ResendCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    def validate_email(self, value):
        return value.lower()





class CompleteRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(max_length =150, min_length =3)
    first_name = serializers.CharField(max_length =150, required = False, allow_blank=True)
    last_name = serializers.CharField(max_length =150, required = False, allow_blank=True)
    phone_number = serializers.CharField(required = False, allow_blank =True)
    date_of_birth = serializers.DateField(required = False, allow_null =True)
    password = serializers.CharField(write_only= True, min_length =8)
    password_confirm = serializers.CharField(write_only= True, min_length =8)

    def validate_email(self, value):
        return value.lower()
    
    def validate_username(self, value):
        if CustomUser.objects.filter(username = value).exists():
            raise serializers.ValidationError("Username alreaady taken")
        return value
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': "Passwords do not match"})
        
        try:
            validate_password(data['password'])
        except Exception as e:
            raise serializers.ValidationError({
                'password': list(e.messages)
            })
        
        return data



class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only= True)




class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only = True)
    new_password = serializers.CharField(write_only = True, min_length =8)
    new_password_confirm = serializers.CharField(write_only = True, min_length = 8)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value
    
    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Passwords do not match'})
        
        try:
            validate_password(data['new_password'])
        except Exception as e:
            raise serializers.ValidationError({'new_password': list(e.messages)})
        
        return data


class UpdateProfileSerializer(serializers.Serializer):
    class Meta:
        model= CustomUser
        fileds = ['first_name', 'last_name', 'username', 'phone_number', 'date_of_birth', 'default_currency']

    def validate_username(self, value):
        user = self.context.get('request').user if self.context.get('request') else self.instance
        if CustomUser.objects.filter(username= value).exclude(id=user.id).exists():
            raise serializers.ValidationError('Username already taken')
        return value