from django.urls import path
from .views import SupportAPI

urlpatterns = [
    path("support/", SupportAPI.as_view()),
    path("support/<str:action>/", SupportAPI.as_view()),
    path("support/<str:action>/<int:user_id>/", SupportAPI.as_view()),
]