# dashboard/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
 
 # Import models needed later
from orders.models import Order, OrderItem
from inventory.models import Product
from django.utils import timezone
from django.db.models import Sum, Count, F, DecimalField, Value, CharField
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
 
     relevant_order_statuses = [Order.ORDER_STATUS_COMPLETED, Order.ORDER_STATUS_PROCESSING]
 
     # Query OrderItems, group by product, sum quantity, order, limit
     top_products_data = OrderItem.objects.filter(
         order__status__in=relevant_order_statuses,
         product__isnull=False # Ensure product link exists
     ).values(
         'product__name' # Group by product name
     ).annotate(
         total_quantity=Sum('quantity') # Sum quantities for each product
     ).order_by(
         '-total_quantity' # Order by most sold first
     )[:5] # Limit to top 5
 
     print("--- Top Products Query Results ---")
     print(top_products_data) # Print the QuerySet result
     print(f"Found {len(top_products_data)} top products.")

     # Prepare data specifically for Chart.js
     top_products_labels = [item['product__name'] for item in top_products_data]
     top_products_values = [item['total_quantity'] for item in top_products_data]
     # --- END Top Selling Products Data ---

     print("Labels:", top_products_labels) # Print the extracted labels
     print("Values:", top_products_values) # Print the extracted values
     print("--------------------------------")

 
     context = {
        'page_title': 'Dashboard',
        'todays_sales': todays_sales,
        'pending_orders_count': pending_orders_count,
        'low_stock_count': low_stock_count,
        # --- Add Chart Data to Context ---
        'top_products_labels': top_products_labels,
        'top_products_values': top_products_values,
     }
     return render(request, 'dashboard/dashboard_home.html', context)