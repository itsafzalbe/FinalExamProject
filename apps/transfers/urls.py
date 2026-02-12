from django.urls import path
from .views import TransferAPI

urlpatterns = [
    path("transfers/", TransferAPI.as_view()),
    path("transfers/<str:action>/", TransferAPI.as_view()),
    path("transfers/<str:action>/<int:pk>/", TransferAPI.as_view()),
]