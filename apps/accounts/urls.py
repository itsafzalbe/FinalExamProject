from rest_framework_simplejwt.views import TokenRefreshView
from .views import SignupView, VerifyCodeView, ResendCodeView, CompleteRegistrationView, LoginView, LogoutView, UserProfileViewSet, check_username_availability, check_email_availability
from django.urls import path


from .template_views import (
    signup_view,
    verify_code_view,
    complete_registration_view,
    login_view,
    logout_view,
    profile_view,
    change_password_view,
    forgot_password_view,
    delete_account_view,
)


app_name = 'accounts'




urlpatterns= [
    #registering the user urls
    # path('signup/', SignupView.as_view(), name='signup'),
    # path('verify-code/', VerifyCodeView.as_view(), name='verify-code'),
    # path('resend-code/', ResendCodeView.as_view(), name='resend-code'),
    # path('complete-registration/', CompleteRegistrationView.as_view(), name='complete-registration'),


    # #auth urls
    # path('login/', LoginView.as_view(), name='login'),
    # path('logout/', LogoutView.as_view(), name='logout'),
    # path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),



    # #profile urls
    # path('profile/', UserProfileViewSet.as_view({'get': 'list', 'put': 'update', 'patch': 'update'}), name='profile'),
    # path('profile/change-password/', UserProfileViewSet.as_view({'post': 'change_password'}), name = 'change-password'),
    # path('profile/delete/', UserProfileViewSet.as_view({'delete': 'delete_account'}), name='delete-account'),
    # path('profile/statistics/', UserProfileViewSet.as_view({'get': 'statistics'}), name='profile-statistics'),




    # #additionals
    # path('check-username/', check_username_availability, name='check-username'),
    # path('check-email/', check_email_availability, name='check-email'),
    

    #template views

    # path('signup/', signup_view, name='signup'),
    # path('verify-code/', verify_code_view, name='verify_code'),
    # path('complete-registration/', complete_registration_view, name='complete_registration'),
    # path('login/', login_view, name='login'),
    # path('logout/', logout_view, name='logout'),
    # path('profile/', profile_view, name='profile'),
    # path('change-password/', change_password_view, name='change_password'),
    # path('forgot-password/', forgot_password_view, name='forgot_password'),
    # path('delete-account/', delete_account_view, name='delete_account'),


]
