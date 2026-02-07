# 1
# # POST /api/auth/signup/
# {
#     "email": "bobur@example.com"
# }

# # Backend Logic:
# from accounts.models import CustomUser

# # Check if email exists
# if CustomUser.objects.filter(email=email).exists():
#     return error("Email already registered")

# # Create user with NEW status
# user = CustomUser.objects.create(
#     email=email,
#     auth_status=NEW
# )
# # username is auto-generated: user_a1b2c3d4

# # Generate and send verification code
# code = user.generate_verification_code()
# send_verification_email(user.email, code)  # Your email function

# # Response:
# {
#     "message": "Verification code sent to your email",
#     "email": "bobur@example.com"
# }







# 2

# # POST /api/auth/verify-code/
# {
#     "email": "bobur@example.com",
#     "code": "1234"
# }

# # Backend Logic:
# user = CustomUser.objects.get(email=email)

# if not user.verify_code(code):
#     return error("Invalid or expired code")

# # Response:
# {
#     "message": "Email verified successfully",
#     "auth_status": "CODE_VERIFIED"
# }



# 3
# # POST /api/auth/complete-registration/
# {
#     "email": "bobur@example.com",
#     "username": "bobur_dev",
#     "first_name": "Bobur",
#     "last_name": "Karimov",
#     "phone_number": "+998901234567",
#     "date_of_birth": "1995-05-15",
#     "password": "SecurePass123!",
#     "password_confirm": "SecurePass123!"
# }

# # Backend Logic:
# user = CustomUser.objects.get(email=email)

# # Check auth status
# if user.auth_status != CODE_VERIFIED:
#     return error("Please verify your email first")

# # Check username uniqueness
# if CustomUser.objects.filter(username=username).exclude(id=user.id).exists():
#     return error("Username already taken")

# # Validate passwords match
# if password != password_confirm:
#     return error("Passwords do not match")

# # Complete registration
# user.complete_registration(
#     username=username,
#     first_name=first_name,
#     last_name=last_name,
#     password=password,
#     phone_number=phone_number,
#     date_of_birth=date_of_birth
# )

# # Generate JWT tokens
# tokens = user.get_tokens()

# # Response:
# {
#     "message": "Registration completed successfully",
#     "user": {
#         "id": user.id,
#         "email": "bobur@example.com",
#         "username": "bobur_dev",
#         "first_name": "Bobur",
#         "last_name": "Karimov"
#     },
#     "tokens": {
#         "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
#         "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
#     }
# }







#4
# # POST /api/auth/resend-code/
# {
#     "email": "bobur@example.com"
# }

# # Backend Logic:
# user = CustomUser.objects.get(email=email)

# if not user.can_resend_code():
#     return error("Please wait 2 minutes before requesting new code")

# code = user.generate_verification_code()
# send_verification_email(user.email, code)

# # Response:
# {
#     "message": "New verification code sent"
# }






#5
# # POST /api/auth/login/
# {
#     "username": "bobur_dev",  # Can use username or email
#     "password": "SecurePass123!"
# }

# # Backend Logic:
# from django.contrib.auth import authenticate

# # Try to authenticate
# user = authenticate(username=username, password=password)

# if not user:
#     # Try with email if username failed
#     try:
#         user_obj = CustomUser.objects.get(email=username)
#         user = authenticate(username=user_obj.username, password=password)
#     except CustomUser.DoesNotExist:
#         pass

# if not user:
#     return error("Invalid credentials")

# if user.auth_status != DONE:
#     return error("Please complete your registration")

# # Generate tokens
# tokens = user.get_tokens()

# # Response:
# {
#     "message": "Login successful",
#     "user": {
#         "id": user.id,
#         "email": "bobur@example.com",
#         "username": "bobur_dev",
#         "first_name": "Bobur",
#         "last_name": "Karimov",
#         "photo": "/media/users_photo/bobur.jpg"
#     },
#     "tokens": {
#         "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
#         "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
#     }
# }
# ```

# ## Database States

# **After Step 1 (Email entered):**
# ```
# CustomUser:
# - id: 1
# - email: "bobur@example.com"
# - username: "user_a1b2c3d4" (auto-generated)
# - auth_status: "NEW"
# - password: "" (unusable)

# EmailVerification:
# - user_id: 1
# - code: "1234"
# - is_verified: False
# - expiration_time: [5 minutes from now]
# ```

# **After Step 2 (Code verified):**
# ```
# CustomUser:
# - auth_status: "CODE_VERIFIED" ← Changed

# EmailVerification:
# - is_verified: True ← Changed
# ```

# **After Step 3 (Registration complete):**
# ```
# CustomUser:
# - email: "bobur@example.com"
# - username: "bobur_dev" ← Changed
# - first_name: "Bobur"
# - last_name: "Karimov"
# - phone_number: "+998901234567"
# - date_of_birth: "1995-05-15"
# - auth_status: "DONE" ← Changed
# - password: [hashed] ← Set

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta


from .models import CustomUser, EmailVerification
from .serializers import *
from .utils import send_verification_email






class SignupView(generics.CreateAPIView):
    serializer_class = SignupSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception = True)

        email = serializer.validated_data['email']

        existing_user = CustomUser.objects.filter(email=email).first()
        if existing_user and existing_user.auth_status == 'done':
            return Response({'error': 'User with this email already exists'}, status=status.HTTP_400_BAD_REQUEST)
        
        if existing_user and existing_user.auth_status in ['new', 'code_verifiead']:
            user = existing_user
        else:
            user = CustomUser.objects.create(email=email, auth_status = 'new')
        
        code = user.generate_verification_code()

        try:
            send_verification_email(user.email, code)
        except Exception as e:
            return Response({
                'error': f"Failed tp send email: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return Response({
            'message': 'Verification code sent to your email',
            'email': user.email
        }, status=status.HTTP_201_CREATED)




class VerifyCodeView(generics.GenericAPIView):
    serializer_class = VerifyCodeSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        code=serializer.validated_data['code']

        try: 
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if not user.verify_code(code):
            return Response({
                'error': 'Invalid or expired verification code'
            }, status=status.HTTP_400_BAD_REQUEST)



        return Response({
            'message': 'Email verified successfully',
            'auth_status': user.auth_status
        })
    



class ResendCodeView(generics.GenericAPIView):
    serializer_class = ResendCodeSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data = request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'User not found',
            }, status=status.HTTP_404_NOT_FOUND)
        
        if user.auth_status == 'done':
            return Response({
                'error': 'Email already verified and registration completed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not user.can_resend_code():
            return Response({
                'error': 'Please wait 2 minutes before requesting a new code'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        code = user.generate_verification_code()

        try:
            send_verification_email(user.email, code)
        except Exception as e:
            return Response({
                'error': f"Failed to send email: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'message': 'New verification code sent to your email'
        })



class CompleteRegistrationView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = CompleteRegistrationSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email=serializer.validated_data['email']
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'User not found'

            }, status=status.HTTP_404_NOT_FOUND)
        
        if user.auth_status != 'code_verified':
            return Response({
                'error':'Please verify your email first'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user.complete_registration(
                username=serializer.validated_data['username'],
                first_name=serializer.validated_data.get('first_name', ''),
                last_name=serializer.validated_data.get('last_name', ''),
                password=serializer.validated_data['password'],
                phone_number=serializer.validated_data.get('phone_number'),
                date_of_birth=serializer.validated_data.get('date_of_birth'),
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        tokens  = user.get_tokens()

        return Response({
            'message': "Registration ocmpleted successfully",
            'user': UserSerializer(user).data,
            'tokens': tokens
        }, status=status.HTTP_201_CREATED)
        




class LoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post (self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']


        user = authenticate(username=username, password=password)

        if not user:
            try:
                user_obj = CustomUser.objects.get(email=username)
                user = authenticate(username=user_obj.username, password=password)
            except CustomUser.DoesNotExist:
                pass
        
        if not user:
            return Response({
                'error': 'Invalid credentials',
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if user.auth_status != 'done':
            return Response({
                'error': 'Please complete your registration first'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        tokens =user.get_tokens()

        return Response({
            'message': 'Login successful',
            'user': UserSerializer(user).data,
            'tokens': tokens
            
        })


class LogoutView(generics.GenericAPIView):
    permission_classes =[IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response(
                    {
                        'error': 'Refresh token is required'
                    }, status=status.HTTP_400_BAD_REQUEST
                )
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({
                'message': 'Logout successful'
            })
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class UserProfileViewSet(viewsets. ViewSet):
    permission_classes = [IsAuthenticated]
    def list(self, request):
        serializer =UserSerializer(request.user)
        return Response(serializer.data)
    

    def update(self, request):
        serializer = UpdateProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'message': 'Profile updated successfully',
            'user': UserSerializer(request.user).data
        })
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data = request.data, context ={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({
            'message': 'Password changed successfully'
        })
    
    @action(detail=False, methods=['delete'])
    def delete_account(self, request):
        password = request.data.get('password')

        if not password:
            return Response({
                'error': 'Password is required to delete account'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not request.user.check_password(password):
            return Response({'error': 'invalid password'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user = request.user

        user.delete()

        return Response({
            'message': 'Account deleted successfully'
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        from apps.transactions.models import Transaction
        from apps.cards.models import Card
        from apps.budgets.models import Budget


        user = request.user

        total_cards = Card.objects.filter(user=user, status='active').count()
        total_transactions = Transaction.objects.filter(user=user).count()
        total_budgets = Budget.objects.filter(user=user, is_active=True).count()

        from apps.cards.models import ExchangeRate, Currency
        user_currency = Currency.objects.get(code=user.default_currency)

        total_balance = 0
        cards = Card.objects.filter(user=user, status='active')
        for card in cards:
            if card.currency == user_currency:
                total_balance += card.balance
            else:
                converted = ExchangeRate.convert(card.balance, card.currency, user_currency)
                if converted:
                    total_balance+=converted
        return Response({
            'total_cards': total_cards,
            'total_transactions': total_transactions,
            'total_budgets': total_budgets,
            'total_balance': total_balance,
            'currency': user.default_currency,
            'member_since': user.created_at

        })
    




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_username_aviability(request):

    username = request.query_params.get('username')
    if not username:
        return Response({
            'error': "Username parameter is required"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    exists = CustomUser.objects.filter(username=username).exclude(id = request.user.id).exists()
    return Response({'aviable': not exists})
    
    
    


@api_view(['GET'])
@permission_classes([AllowAny])
def check_email_availability(request):
    email = request.query_params.get('email')
    if not email:
        return Response({
            'error': "Email parameter is required",
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = CustomUser.objects.filter(email=email.lower()).first()

    if user and user.auth_status == 'done':
        available = False
    else:
        available = True

    return Response({
        'available': available
    })
