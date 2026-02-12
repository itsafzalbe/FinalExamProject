from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from decimal import Decimal
from django.shortcuts import get_object_or_404
from .models import CardTransfer
from apps.cards.models import *
from .serializers import *



class TransferAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, action=None, pk=None):
        if action is None:
            qs = CardTransfer.objects.filter(user=request.user)

            card = request.GET.get("card")
            if card:
                qs = qs.filter(Q(from_card_id=card) | Q(to_card_id=card))
            total = qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")

            return Response({
                'total_transferred': float(total),
                'results': TransferSerializer(qs, many=True).data
            })

        if action == 'detail':
            obj = get_object_or_404(CardTransfer, pk=pk, user=request.user)
            return Response(TransferSerializer(obj).data)

        if action == 'rate':
            f= request.GET.get("from")
            t= request.GET.get("to")

            if not f or not t:
                return Response({"error": "Missing currency codes"}, status=400)

            from_c = get_object_or_404(Currency, code=f)
            to_c = get_object_or_404(Currency, code=t)

            if from_c == to_c:
                return Response({"rate": 1.0})

            rate = ExchangeRate.get_latest_rate(from_c, to_c)

            if not rate:
                return Response({"error": "Rate not available"}, status=404)
            return Response({"rate": float(rate)})

        if action == 'calculate':
            try:
                amount = Decimal(request.GET.get("amount"))
                from_card = Card.objects.get(id = request.GET.get("from_card"), user = request.user)
                to_card = Card.objects.get(id = request.GET.get("to_card"), user = request.user)

                if from_card == to_card:
                    return Response({"error": "Same card"}, status=400)

                if amount > from_card.balance:
                    return Response({"error": "Insufficient balance"}, status=400)

                if from_card.currency != to_card.currency:
                    rate  = ExchangeRate.get_latest_rate(from_card.currency, to_card.currency)
                    converted  = amount * rate
                else:
                    rate = Decimal('1')
                    converted = amount

                return  Response({
                    'amount': float(amount),
                    'converted': float(converted),
                    'exchange_rate': float(rate),
                    'new_from_balance': float(from_card.balance - amount),
                    'new_to_balance': float(to_card.balance +converted),

                })
            except Exception as e:
                return Response({"error": str(e)}, status=400)

        if action == 'history':
            transfers = CardTransfer.objects.filter(user=request.user)

            stats = transfers.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"), total=Sum("amount")).order_by("-month")[:6]

            return Response({
                "recent": TransferSerializer(transfers[:20], many=True).data,
                "monthly_stats": stats,
                "total_count": transfers.count(),
            })


    def post(self, request, action=None):

        serializer = CardTransferSerializer(data=request.data, context={'request': request})

        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)

