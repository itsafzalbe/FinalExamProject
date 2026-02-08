from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CurrencyViewSet, ExchangeRateViewSet, CardTypeViewSet, CardViewSet



router = DefaultRouter()
router.register(r'currencies', CurrencyViewSet, basename = 'currency')
router.register(r'exchange-rates', ExchangeRateViewSet, basename = 'exchange-rate')
router.register(r'card-types', CardTypeViewSet, basename = 'card-type')
router.register(r'cards', CardViewSet, basename = 'card')


urlpatterns = [
    path('', include(router.urls)),
]