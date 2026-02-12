from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Q, Count
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import *
from .serializers import *
from .filters import BudgetFilter








class BudgetViewSet(viewsets.ModelViewSet):
    """
    Endpoints:
     GET /api/budgets/ - list user budgets
     POST /api/budgets/ -create
     GET /api/budgets/{id}/ - get a budget by its id
     PUT/PATCH /api/budgets/{id}/ update the budget
     DELETE /api/budgets/{id}/ - delete the budget
     GET /api/budgets/{id}/progress/ -get budget progress
     GET /api/budgets/active/ get the active budgets only
     GET /api/budgets/overview/ -get the budgets overview
     GET /api/budgets/alerts/ - get the budgets alerts
     POST /api/budgets/{id}/toggle_active/ - change the active budget
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = BudgetFilter
    search_fields= ['name', 'category__name']
    ordering_fields = ['created_at', 'amount', 'name']
    ordering=['-created_at']

    def get_queryset(self):
        return Budget.objects.filter(user= self.request.user).select_related('category', 'currency')
    

    def get_serializer(self):
        if self.action in ['create', 'update', 'partial_update']:
            return BudgetCreateSerializer
        elif self.action == 'retrieve':
            return BudgetDetailSerializer
        return BudgetSerializer
    

    def perform_create(self, serializer):
        serializer.save(user = self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        category = serializer.validated_data['category']
        period = serializer.validated_data['period']

        existing = Budget.objects.filter(user=request.user, category=category, period=period, is_active=True).exists()

        if existing:
            return Response({
                'error': f"You already have an active {period} budget for {category.name}",
                'suggestion': "Update the existing budget or deactivate it first"
            }, status=status.HTTP_400_BAD_REQUEST)
        budget = serializer.save()
        return Response(
            BudgetDetailSerializer(budget).data,
            status=status.HTTP_201_CREATED
        )
    
    def destroy(self, request, *args, **kwargs):
        budget = self.get_object()
        return super().destroy(request, *args, **kwargs)
    

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        budget = self.get_object()

        spent = budget.get_spent_amount()
        percentage = budget.get_percentage_used()
        remaining = budget.amount - spent

        from datetime import date
        today = date.today()

        if budget.period == 'weekly':
            period_start = today - timedelta(days=today.weekday())
            period_end = period_start + timedelta(days=6)
        elif budget.period == 'monthly':
            period_start = today.replace(day=1)
            if today.month ==12:
                period_end = today.replace(year=today.year +1, month=1, day=1) - timedelta(days=1)
            else:
                period_end = today.replace(month=today.month +1, day=1) - timedelta(days=1)
        elif budget.period == 'yearly':
            period_start = today.replace(month=1, day= 1)
            period_end = today.replace(month=12, day=31)
        else:
            period_start = today
            period_end = today



        days_in_period = (period_end - period_start).days +1
        days_elapsed = (today - period_start).days + 1
        days_remaining = (period_end - today).days

        average_daily_spending = spent /days_elapsed if days_elapsed >0 else Decimal('0')

        suggested_daily_limit = remaining/days_remaining if days_remaining > 0 else Decimal('0')

        if budget.is_over_budget():
            status_text = 'over_budget'
        elif percentage >= budget.alert_threshold:
            status_text = 'warning'
        elif percentage >= 50:
            status_text = 'on_track'
        else:
            status_text = 'good'

        return Response({
            'budget': BudgetSerializer(budget).data,
            'period': {
                'start': period_start,
                'end': period_end,
                'days_total': days_in_period,
                'days_elapsed': days_elapsed,
                'days_remaining': max(days_remaining, 0)
            },
            'spent': spent,
            'remaining': max(remaining, Decimal('0')),
            'percentage_used': percentage,
            'is_over_budget': budget.is_over_budget(),
            'average_daily_speding': average_daily_spending,
            'suggested_daily_limit': suggested_daily_limit,
            'status': status_text
        })
    

    @action(detail=False, methods=['get'])
    def active(self, request):
        budgets = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(budgets, many=True)
        return Response(serializer.data)
    


    @action(detail=False, methods=['get'])
    def overview(self, request):
        budgets = self.get_queryset().filter(is_active = True)

        if not budgets.exists():
            return Response({
                'total_budgets': 0,
                'active_budgets': 0,
                'messages': 'No active budgets found'
            })
        
        from apps.cards.models import Currency, ExchangeRate
        u_crncy = Currency.objects.get(code=request.user.default_currency)

        total_budget_amount = Decimal('0')
        total_spent = Decimal('0')
        budgets_over_limit = 0
        budgets_at_warning = 0

        budgets_data = []

        for bdgt in budgets:
            if bdgt.currency == u_crncy:
                budget_amount = bdgt.amount
                spent_amount = bdgt.get_spent_amount()
            else:
                budget_amount = ExchangeRate.convert(bdgt.amount, bdgt.currency, u_crncy) or bdgt.amount

                spent_amount_original = bdgt.get_spent_amount()
                spent_amount = ExchangeRate.convert(spent_amount_original, bdgt.currency, u_crncy, ) or spent_amount_original
                
            total_budget_amount += budget_amount
            total_spent += spent_amount

            percentage = bdgt.get_percentage_used()
            if bdgt.is_over_budget():
                budgets_over_limit += 1
            elif percentage >= bdgt.alert_threshold:
                budgets_at_warning += 1


            budget_data = BudgetSerializer(bdgt).data
            budget_data['spent'] = bdgt.get_spent_amount()
            budget_data['percentage_used'] = percentage
            budget_data['is_over_budget'] = bdgt.is_over_budget()
            budgets_data.append(budget_data)
        
        total_remaining =total_budget_amount - total_spent
        overall_percentage = (total_spent/total_budget_amount*100) if total_budget_amount > 0 else 0


        return Response({
            'total_budgets': budgets.count(),
            'active_budgets': budgets.filter(is_active=True).count(),
            'total_budget_amount': total_budget_amount,
            'total_spent': total_spent,
            'total_remaining': total_remaining,
            'overall_percentage': round(overall_percentage, 2),
            'budgets_over_limit': budgets_over_limit,
            'budgets_at_warning': budgets_at_warning,
            'currency': request.user.default_currency,
            'budgets': budgets_data

        })
    
    @action(detail=False, methods=['get'])
    def alerts(self, request):
        budgets =self.get_queryset().filter(is_active=True)
        alerts = []

        for budget in budgets:
            percentage = budget.get_percentage_used()

            if budget.is_over_budget():
                over_amount = budget.get_spent_amount() - budget.amount
                alerts.append({
                    'budget': BudgetSerializer(budget).data,
                    'alert_type': 'over_budget',
                    'severity': 'high',
                    'message': f"You have exceeded your {budget.name} by {over_amount:,.0f} {budget.currency.code}",
                    'percentage_used': percentage
                })
            elif percentage >= budget.alert_threshold:
                remaining = budget.amount - budget.get_spent_amount()
                alerts.append({
                    'budget': BudgetSerializer(budget).data,
                    'alert_type': 'warning',
                    'severity': 'medium',
                    'message': f"You have used {percentage:.1f}% of your {budget.name}. {remaining:,.0f} {budget.currency.code} remaining",
                    'percentage_used': percentage

                })
        
        alerts.sort(key=lambda x: (x['severity'] == 'medium', -x['percentage_used']))

        return Response({
            'alert_count': len(alerts),
            'alerts': alerts
        })
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        budget = self.get_object()

        budget.is_active = not budget.is_active
        budget.save()

        status_text = 'activated' if budget.is_active else 'deactivated'

        return Response({
            'message': f"Budget {status_text}",
            'is_active': budget.is_active,
            'budget': BudgetSerializer(budget).data
        })
    
    @action(detail=False , methods=['get'])
    def by_category(self, request):
        budgets =self.get_queryset().filter(is_active=True)
        
        from collections import defaultdict
        categories_dict = defaultdict(list)

        for budget in budgets:
            budget_data = BudgetSerializer(budget).data
            budget_data['spent'] = budget.get_spent_amount()
            budget_data['percentage_used'] = budget.get_percentage_used()
            budget_data['is_over_budget'] = budget.is_over_budget()

            categories_dict[budget.category.id].append(budget_data)
        
        result = []
        for category_id, budgets_list in categories_dict.items():
            category = budgets[0].category if budgets else None
            if category:
                result.append({
                    'category_id': category_id,
                    'category_name': category.name,
                    'category_icon': category.icon,
                    'category_color': category.color,
                    'budgets': budgets_list
                })
        
        return Response({
            'categories': result
        })
    
    @action(detail=False, methods=['get'])
    def by_period(self, request):
        budgets = self.get_queryset().filter(is_active=True)

        periods = {
            'weekly': [],
            'monthly': [],
            'yearly': []
        }

        for budget in budgets:
            budget_data = BudgetSerializer(budget).data
            budget_data['spent'] = budget.get_spent_amount()
            budget_data['percentage_used'] = budget.get_percentage_used()
            budget_data['is_over_budget'] = budget.is_over_budget()

            periods[budget.period].append(budget_data)

        return Response({
            'periods': periods
        })
    
    @action(detail=True, methods=['get'])
    def spending_history(self, request, pk=None):
        from apps.transactions.models import Transaction
        from django.db.models.functions import TruncMonth
        from datetime import datetime

        budget = self.get_object()
        months_back = int(request.query_params.get('months_back', 6))

        today = timezone.now().date()
        start_date = today - timedelta(days=30, * months_back)
        transactions = Transaction.objects.filter(user=request.user, category=budget.category, type='expense', date__gte=start_date).annotate(month=TruncMonth('date')).values('month').annotate(total=Sum('amount_in_user_currency')).order_by('month')

        history =[]
        for item in transactions:
            month = item['month']
            spent = item['total']
            percentage = (spent/ budget.amount *100) if budget.amount > 0 else 0

            history.append({
                'period': month.strftime('%Y-%m'),
                'spent': spent,
                'budget_amount': budget.amount,
                'percentage': round(percentage, 2),
                'was_over_budget': spent > budget.amount

            })

        return Response({
            'budget': BudgetSerializer(budget).data,
            'history': history
        })