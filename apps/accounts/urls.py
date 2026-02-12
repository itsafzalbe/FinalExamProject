from rest_framework_simplejwt.views import TokenRefreshView
from .views import SignupView, VerifyCodeView, ResendCodeView, CompleteRegistrationView, LoginView, LogoutView, UserProfileViewSet, check_username_availability, check_email_availability
from django.urls import path
app_name = 'accounts'
urlpatterns= [
    # registering the user urls
    path('signup/', SignupView.as_view(), name='signup'),
    path('verify-code/', VerifyCodeView.as_view(), name='verify-code'),
    path('resend-code/', ResendCodeView.as_view(), name='resend-code'),
    path('complete-registration/', CompleteRegistrationView.as_view(), name='complete-registration'),

    #auth urls
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    #profile urls
    path('profile/', UserProfileViewSet.as_view({'get': 'list', 'put': 'update', 'patch': 'update'}), name='profile'),
    path('profile/change-password/', UserProfileViewSet.as_view({'post': 'change_password'}), name = 'change-password'),
    path('profile/delete/', UserProfileViewSet.as_view({'delete': 'delete_account'}), name='delete-account'),
    path('profile/statistics/', UserProfileViewSet.as_view({'get': 'statistics'}), name='profile-statistics'),

    #additionals
    path('check-username/', check_username_availability, name='check-username'),
    path('check-email/', check_email_availability, name='check-email'),

]
