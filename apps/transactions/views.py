from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from .models import Category, Transaction, TransactionTag, TransactionTagRelation
from .serializers import (
    CategorySerializer,
    CategoryCreateSerializer,
    TransactionSerializer,
    TransactionCreateSerializer,
    TransactionDetailSerializer,
    TransactionTagSerializer,
    TransactionStatisticsSerializer,
)
from .filters import TransactionFilter
from apps.cards.models import Card


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing categories.
    
    Endpoints:
    - GET /api/transactions/categories/ - List all categories (default + user's custom)
    - POST /api/transactions/categories/ - Create custom category
    - GET /api/transactions/categories/{id}/ - Get specific category
    - PUT/PATCH /api/transactions/categories/{id}/ - Update custom category
    - DELETE /api/transactions/categories/{id}/ - Delete custom category
    - GET /api/transactions/categories/income/ - List only income categories
    - GET /api/transactions/categories/expense/ - List only expense categories
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'type']
    ordering_fields = ['name', 'type', 'created_at']
    ordering = ['type', 'name']
    
    def get_queryset(self):
        """
        Return default categories + user's custom categories.
        Filter inactive categories.
        """
        user = self.request.user
        return Category.objects.filter(
            Q(user=None) | Q(user=user),  # Default or user's custom
            is_active=True
        )
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CategoryCreateSerializer
        return CategorySerializer
    
    def perform_create(self, serializer):
        """Set user when creating custom category"""
        serializer.save(user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        """Only allow deletion of user's custom categories"""
        category = self.get_object()
        
        if category.user is None:
            return Response(
                {'error': 'Cannot delete default categories'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if category.user != request.user:
            return Response(
                {'error': 'You can only delete your own categories'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if category is being used
        if category.transactions.exists():
            return Response(
                {'error': 'Cannot delete category that has transactions. Set it as inactive instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'])
    def income(self, request):
        """Get only income categories"""
        categories = self.get_queryset().filter(type='income')
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expense(self, request):
        """Get only expense categories"""
        categories = self.get_queryset().filter(type='expense')
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def with_subcategories(self, request):
        """Get categories grouped with their subcategories"""
        categories = self.get_queryset().filter(parent_category=None)
        result = []
        
        for category in categories:
            category_data = CategorySerializer(category).data
            subcategories = category.subcategories.filter(is_active=True)
            category_data['subcategories'] = CategorySerializer(subcategories, many=True).data
            result.append(category_data)
        
        return Response(result)


class TransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing transactions.
    
    Endpoints:
    - GET /api/transactions/ - List all user's transactions
    - POST /api/transactions/ - Create new transaction
    - GET /api/transactions/{id}/ - Get specific transaction
    - PUT/PATCH /api/transactions/{id}/ - Update transaction
    - DELETE /api/transactions/{id}/ - Delete transaction
    - GET /api/transactions/statistics/ - Get statistics
    - GET /api/transactions/recent/ - Get recent transactions
    - GET /api/transactions/by_category/ - Group by category
    - GET /api/transactions/by_date/ - Group by date
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TransactionFilter
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['date', 'amount', 'created_at']
    ordering = ['-date', '-created_at']
    
    def get_queryset(self):
        """Return only user's transactions"""
        return Transaction.objects.filter(user=self.request.user).select_related(
            'card', 'category', 'card__currency', 'card__card_type'
        ).prefetch_related('transaction_tags__tag')
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TransactionCreateSerializer
        elif self.action == 'retrieve':
            return TransactionDetailSerializer
        return TransactionSerializer
    
    def perform_create(self, serializer):
        """Set user when creating transaction"""
        serializer.save(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Create transaction with tags"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get tags from request
        tag_ids = request.data.get('tags', [])
        
        # Create transaction
        transaction = serializer.save()
        
        # Add tags
        if tag_ids:
            for tag_id in tag_ids:
                try:
                    tag = TransactionTag.objects.get(id=tag_id)
                    # Check if tag belongs to user or is default
                    if tag.user is None or tag.user == request.user:
                        TransactionTagRelation.objects.create(
                            transaction=transaction,
                            tag=tag
                        )
                except TransactionTag.DoesNotExist:
                    pass
        
        headers = self.get_success_headers(serializer.data)
        return Response(
            TransactionDetailSerializer(transaction).data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )
    
    def update(self, request, *args, **kwargs):
        """Update transaction with tags"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Update transaction
        transaction = serializer.save()
        
        # Update tags if provided
        if 'tags' in request.data:
            tag_ids = request.data.get('tags', [])
            
            # Remove old tags
            TransactionTagRelation.objects.filter(transaction=transaction).delete()
            
            # Add new tags
            for tag_id in tag_ids:
                try:
                    tag = TransactionTag.objects.get(id=tag_id)
                    if tag.user is None or tag.user == request.user:
                        TransactionTagRelation.objects.create(
                            transaction=transaction,
                            tag=tag
                        )
                except TransactionTag.DoesNotExist:
                    pass
        
        return Response(TransactionDetailSerializer(transaction).data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get transaction statistics.
        Query params:
        - start_date: Start date (YYYY-MM-DD)
        - end_date: End date (YYYY-MM-DD)
        - period: 'today', 'week', 'month', 'year', 'all'
        """
        period = request.query_params.get('period', 'month')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Calculate date range
        today = timezone.now().date()
        
        if start_date and end_date:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        elif period == 'today':
            start = today
            end = today
        elif period == 'week':
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
        elif period == 'month':
            start = today.replace(day=1)
            if today.month == 12:
                end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        elif period == 'year':
            start = today.replace(month=1, day=1)
            end = today.replace(month=12, day=31)
        else:  # all
            start = None
            end = None
        
        # Get transactions in range
        transactions = self.get_queryset()
        if start and end:
            transactions = transactions.filter(date__gte=start, date__lte=end)
        
        # Calculate statistics
        income_transactions = transactions.filter(type='income')
        expense_transactions = transactions.filter(type='expense')
        
        total_income = income_transactions.aggregate(
            total=Sum('amount_in_user_currency')
        )['total'] or Decimal('0')
        
        total_expense = expense_transactions.aggregate(
            total=Sum('amount_in_user_currency')
        )['total'] or Decimal('0')
        
        # Category breakdown
        category_breakdown = transactions.values(
            'category__name', 'category__icon', 'category__color', 'type'
        ).annotate(
            total=Sum('amount_in_user_currency'),
            count=Count('id')
        ).order_by('-total')
        
        # Top categories
        top_expense_categories = expense_transactions.values(
            'category__name', 'category__icon'
        ).annotate(
            total=Sum('amount_in_user_currency')
        ).order_by('-total')[:5]
        
        top_income_categories = income_transactions.values(
            'category__name', 'category__icon'
        ).annotate(
            total=Sum('amount_in_user_currency')
        ).order_by('-total')[:5]
        
        data = {
            'period': period,
            'start_date': start,
            'end_date': end,
            'currency': request.user.default_currency,
            'total_income': total_income,
            'total_expense': total_expense,
            'net': total_income - total_expense,
            'income_count': income_transactions.count(),
            'expense_count': expense_transactions.count(),
            'total_transactions': transactions.count(),
            'category_breakdown': list(category_breakdown),
            'top_expense_categories': list(top_expense_categories),
            'top_income_categories': list(top_income_categories),
        }
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent transactions (last 10)"""
        limit = int(request.query_params.get('limit', 10))
        transactions = self.get_queryset()[:limit]
        serializer = self.get_serializer(transactions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """
        Group transactions by category with totals.
        Query params: start_date, end_date, type (income/expense)
        """
        transactions = self.get_queryset()
        
        # Filter by date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            transactions = transactions.filter(date__gte=start_date)
        if end_date:
            transactions = transactions.filter(date__lte=end_date)
        
        # Filter by type
        transaction_type = request.query_params.get('type')
        if transaction_type in ['income', 'expense']:
            transactions = transactions.filter(type=transaction_type)
        
        # Group by category
        result = transactions.values(
            'category__id',
            'category__name',
            'category__icon',
            'category__color',
            'category__type'
        ).annotate(
            total_amount=Sum('amount_in_user_currency'),
            transaction_count=Count('id')
        ).order_by('-total_amount')
        
        return Response(list(result))
    
    @action(detail=False, methods=['get'])
    def by_date(self, request):
        """
        Group transactions by date.
        Query params: start_date, end_date, group_by (day/week/month)
        """
        transactions = self.get_queryset()
        
        # Filter by date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            transactions = transactions.filter(date__gte=start_date)
        if end_date:
            transactions = transactions.filter(date__lte=end_date)
        
        # Group by date
        from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
        
        group_by = request.query_params.get('group_by', 'day')
        
        if group_by == 'week':
            trunc_func = TruncWeek
        elif group_by == 'month':
            trunc_func = TruncMonth
        else:
            trunc_func = TruncDate
        
        result = transactions.annotate(
            period=trunc_func('date')
        ).values('period').annotate(
            total_income=Sum('amount_in_user_currency', filter=Q(type='income')),
            total_expense=Sum('amount_in_user_currency', filter=Q(type='expense')),
            income_count=Count('id', filter=Q(type='income')),
            expense_count=Count('id', filter=Q(type='expense'))
        ).order_by('period')
        
        return Response(list(result))
    
    @action(detail=False, methods=['get'])
    def by_card(self, request):
        """Group transactions by card"""
        transactions = self.get_queryset()
        
        # Filter by date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            transactions = transactions.filter(date__gte=start_date)
        if end_date:
            transactions = transactions.filter(date__lte=end_date)
        
        result = transactions.values(
            'card__id',
            'card__card_name',
            'card__currency__code',
            'card__card_type__name'
        ).annotate(
            total_income=Sum('amount', filter=Q(type='income')),
            total_expense=Sum('amount', filter=Q(type='expense')),
            transaction_count=Count('id')
        ).order_by('-transaction_count')
        
        return Response(list(result))
    
    @action(detail=False, methods=['get'])
    def monthly_trend(self, request):
        """
        Get monthly income/expense trend for the last 12 months.
        """
        from django.db.models.functions import TruncMonth
        
        # Get last 12 months
        today = timezone.now().date()
        start_date = today - timedelta(days=365)
        
        transactions = self.get_queryset().filter(date__gte=start_date)
        
        result = transactions.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            income=Sum('amount_in_user_currency', filter=Q(type='income')),
            expense=Sum('amount_in_user_currency', filter=Q(type='expense')),
            net=Sum('amount_in_user_currency', filter=Q(type='income')) - 
                Sum('amount_in_user_currency', filter=Q(type='expense'))
        ).order_by('month')
        
        return Response(list(result))
    
    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        """
        Delete multiple transactions at once.
        Body: {"transaction_ids": [1, 2, 3]}
        """
        transaction_ids = request.data.get('transaction_ids', [])
        
        if not transaction_ids:
            return Response(
                {'error': 'No transaction IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get transactions
        transactions = self.get_queryset().filter(id__in=transaction_ids)
        count = transactions.count()
        
        # Delete
        transactions.delete()
        
        return Response({
            'message': f'{count} transactions deleted successfully',
            'deleted_count': count
        })


class TransactionTagViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing transaction tags.
    
    Endpoints:
    - GET /api/transactions/tags/ - List all tags (default + user's custom)
    - POST /api/transactions/tags/ - Create custom tag
    - GET /api/transactions/tags/{id}/ - Get specific tag
    - PUT/PATCH /api/transactions/tags/{id}/ - Update custom tag
    - DELETE /api/transactions/tags/{id}/ - Delete custom tag
    """
    serializer_class = TransactionTagSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering = ['name']
    
    def get_queryset(self):
        """Return default tags + user's custom tags"""
        user = self.request.user
        return TransactionTag.objects.filter(
            Q(user=None) | Q(user=user)
        )
    
    def perform_create(self, serializer):
        """Set user when creating custom tag"""
        serializer.save(user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        """Only allow deletion of user's custom tags"""
        tag = self.get_object()
        
        if tag.user is None:
            return Response(
                {'error': 'Cannot delete default tags'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if tag.user != request.user:
            return Response(
                {'error': 'You can only delete your own tags'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        """Get all transactions with this tag"""
        tag = self.get_object()
        transactions = Transaction.objects.filter(
            user=request.user,
            transaction_tags__tag=tag
        ).distinct()
        
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)