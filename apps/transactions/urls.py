from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'tags', TransactionTagViewSet, basename='transaction-tag')


urlpatterns = [
    
    path('', include(router.urls)) 
]
