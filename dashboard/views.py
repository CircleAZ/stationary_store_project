# dashboard/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
 
 # Import models needed later
from orders.models import Order
from inventory.models import Product
from django.utils import timezone
from django.db.models import Sum, Count, F, DecimalField, Value
from decimal import Decimal
from django.db.models.functions import Coalesce
 
 # Create your views here.
 
@login_required
def dashboard_view(request):
     """ Displays the main dashboard with summary statistics. """
     today = timezone.localdate() # Get today's date in the current timezone
 
     # 1. Today's Sales
     # Sum 'total_amount' for orders created today (consider completed/processing only?)
     # Using Coalesce to handle case where Sum might return None if no orders today
     todays_sales_agg = Order.objects.filter(
         created_at__date=today,
         # Optional: Filter by status relevant to sales total
         # status__in=[Order.ORDER_STATUS_PROCESSING, Order.ORDER_STATUS_COMPLETED]
     ).aggregate(
         total_sales=Coalesce(Sum('total_amount'), Decimal('0.00'), output_field=DecimalField())
     )
     todays_sales = todays_sales_agg['total_sales']
 
     # 2. Pending Orders
     # Count orders with status 'Pending' or 'Processing'
     pending_orders_count = Order.objects.filter(
         status__in=[Order.ORDER_STATUS_PENDING, Order.ORDER_STATUS_PROCESSING]
     ).count()
 
     # 3. Low Stock Items
     # Count products where stock_quantity <= low_stock_threshold
     low_stock_count = Product.objects.filter(
         stock_quantity__lte=F('low_stock_threshold')
         # Optional: Add filter(is_active=True) if applicable
     ).count()
 
 
     context = {
         'page_title': 'Dashboard',
         'todays_sales': todays_sales,          # Pass calculated value
         'pending_orders_count': pending_orders_count, # Pass calculated value
         'low_stock_count': low_stock_count,       # Pass calculated value
     }
     return render(request, 'dashboard/dashboard_home.html', context)