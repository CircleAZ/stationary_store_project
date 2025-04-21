# reports/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F, Q, DecimalField, OuterRef, Subquery, Value, IntegerField
from django.db.models.functions import Coalesce
from decimal import Decimal
from orders.models import Order, OrderItem
from inventory.models import Product  
from customers.models import Customer
from .forms import DateRangeForm

@login_required
def sales_summary_report_view(request):
    """ Generates and displays a sales summary report based on different periods. """
    page_title = "Sales Summary Report"
    today = timezone.localdate()
    start_of_week = today - timezone.timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)

    # Base queryset - filter orders relevant for sales (adjust as needed)
    base_orders_qs = Order.objects.filter(
        status__in=[Order.ORDER_STATUS_COMPLETED, Order.ORDER_STATUS_PROCESSING]
    )

    form = DateRangeForm(request.GET or None) # Populate with GET data if present
    start_date = None
    end_date = None
    date_range_stats = None # Initialize stats for the custom range

    if form.is_valid():
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')

    base_orders_qs = Order.objects.filter(
        status__in=[Order.ORDER_STATUS_COMPLETED, Order.ORDER_STATUS_PROCESSING]
    )

    # --- Calculate Stats for different periods ---

    # Today
    today_stats = base_orders_qs.filter(
        created_at__date=today
    ).aggregate(
        total_sales=Coalesce(Sum('total_amount'), Decimal('0.00'), output_field=DecimalField()),
        order_count=Count('pk'),
        avg_order_value=Avg('total_amount') # Avg returns None if count is 0
    )
    today_stats['avg_order_value'] = today_stats['avg_order_value'] or Decimal('0.00') # Handle None case

    # This Week (from start of week to today)
    week_stats = base_orders_qs.filter(
        created_at__date__gte=start_of_week
    ).aggregate(
        total_sales=Coalesce(Sum('total_amount'), Decimal('0.00'), output_field=DecimalField()),
        order_count=Count('pk'),
        avg_order_value=Avg('total_amount')
    )
    week_stats['avg_order_value'] = week_stats['avg_order_value'] or Decimal('0.00')

    # This Month (from start of month to today)
    month_stats = base_orders_qs.filter(
        created_at__date__gte=start_of_month
    ).aggregate(
        total_sales=Coalesce(Sum('total_amount'), Decimal('0.00'), output_field=DecimalField()),
        order_count=Count('pk'),
        avg_order_value=Avg('total_amount')
    )
    month_stats['avg_order_value'] = month_stats['avg_order_value'] or Decimal('0.00')

    # All Time
    all_time_stats = base_orders_qs.aggregate(
         total_sales=Coalesce(Sum('total_amount'), Decimal('0.00'), output_field=DecimalField()),
        order_count=Count('pk'),
        avg_order_value=Avg('total_amount')
    )
    all_time_stats['avg_order_value'] = all_time_stats['avg_order_value'] or Decimal('0.00')


    filtered_qs = base_orders_qs # Start with the base queryset
    if start_date:
        filtered_qs = filtered_qs.filter(created_at__date__gte=start_date)
    if end_date:
        # Add 1 day to end_date for __lte if you want inclusive range,
        # or use __lt for exclusive end date if using datetime.
        # For __date lookup, <= end_date is usually sufficient.
        filtered_qs = filtered_qs.filter(created_at__date__lte=end_date)

    # Only calculate if dates were provided or if form wasn't submitted (show all-time initially)
    # Let's calculate even if only one date is given
    if start_date or end_date:
         date_range_stats = filtered_qs.aggregate(
             total_sales=Coalesce(Sum('total_amount'), Decimal('0.00'), output_field=DecimalField()),
             order_count=Count('pk'),
             avg_order_value=Avg('total_amount')
         )
         date_range_stats['avg_order_value'] = date_range_stats['avg_order_value'] or Decimal('0.00')



    context = {
        'page_title': page_title,
        'form': form, # Pass the form to the template
        'start_date': start_date, # Pass selected dates for display
        'end_date': end_date,
        'date_range_stats': date_range_stats, # Pass stats for the custom range
        'today_stats': today_stats,
        'week_stats': week_stats,
        'month_stats': month_stats,
        'all_time_stats': all_time_stats,
    }
    return render(request, 'reports/sales_summary_report.html', context)

@login_required
def sales_by_product_report_view(request):
    """ Generates a report summarizing sales data grouped by product. """
    page_title = "Sales by Product Report"

    # Define relevant order statuses for sales calculation
    relevant_order_statuses = [Order.ORDER_STATUS_COMPLETED, Order.ORDER_STATUS_PROCESSING]

    # Annotate Product QuerySet with sales data from related OrderItems
    # We query Products and look 'backwards' to find related sales.
    products_with_sales = Product.objects.annotate(
        # Subquery to calculate total quantity sold for this product
        total_quantity_sold=Coalesce(
            Subquery(
                OrderItem.objects.filter(
                    product=OuterRef('pk'), # Link to the outer Product query
                    order__status__in=relevant_order_statuses # Filter by order status
                ).values('product') # Group by product (implicitly)
                 .annotate(total_qty=Sum('quantity')) # Calculate sum of quantity
                 .values('total_qty') # Select only the calculated sum
            ),
            0, # Default to 0 if no sales
             output_field=IntegerField()
        ),
        # Subquery to calculate total revenue for this product
        total_revenue=Coalesce(
            Subquery(
                 OrderItem.objects.filter(
                    product=OuterRef('pk'),
                    order__status__in=relevant_order_statuses
                ).values('product')
                 .annotate(total_rev=Sum(F('quantity') * F('price'))) # Sum of (qty * price)
                 .values('total_rev')
            ),
            Decimal('0.00'), # Default to 0.00 if no sales
            output_field=DecimalField()
        )
    ).filter(
        total_quantity_sold__gt=0 # Only include products that have actually been sold
    ).order_by(
        '-total_revenue' # Order by highest revenue first
    ) # You could order by '-total_quantity_sold' instead

    context = {
        'page_title': page_title,
        'products_sales_data': products_with_sales,
    }
    return render(request, 'reports/sales_by_product_report.html', context)
# --- END Sales by Product View ---

@login_required
def sales_by_customer_report_view(request):
    """ Generates a report summarizing sales data grouped by customer. """
    page_title = "Sales by Customer Report"

    # Define relevant order statuses for sales calculation
    relevant_order_statuses = [Order.ORDER_STATUS_COMPLETED, Order.ORDER_STATUS_PROCESSING]

    # Annotate Customer QuerySet with order data
    # Start with Customer model and look 'forward' using related_name 'orders'
    customers_with_sales = Customer.objects.annotate(
        total_spent=Coalesce(
            Sum(
                'orders__total_amount', # Double underscore to traverse relationship
                filter=Q(orders__status__in=relevant_order_statuses) # Filter orders being summed
            ),
            Decimal('0.00'),
            output_field=DecimalField()
        ),
        order_count=Count(
            'orders',
            filter=Q(orders__status__in=relevant_order_statuses) # Filter orders being counted
        )
    ).filter(
        order_count__gt=0 # Only include customers who have placed relevant orders
    ).order_by(
        '-total_spent' # Show top spenders first
    )

    context = {
        'page_title': page_title,
        'customers_sales_data': customers_with_sales,
    }
    return render(request, 'reports/sales_by_customer_report.html', context)
# --- END Sales by Customer View ---

# --- NEW Profit & Loss View ---
@login_required
def profit_loss_report_view(request):
    """ Calculates and displays a basic profit and loss overview. """
    page_title = "Profit & Loss Overview"

    # Define relevant order statuses for P&L (usually Completed)
    relevant_order_statuses = [Order.ORDER_STATUS_COMPLETED] # Adjust if needed

    # Calculate Total Revenue from relevant orders
    revenue_agg = Order.objects.filter(
        status__in=relevant_order_statuses
    ).aggregate(
        total_revenue=Coalesce(Sum('total_amount'), Decimal('0.00'), output_field=DecimalField())
    )
    total_revenue = revenue_agg['total_revenue']

    # Calculate Total Cost of Goods Sold (COGS) from items in relevant orders
    cogs_agg = OrderItem.objects.filter(
        order__status__in=relevant_order_statuses,
        cost_price__isnull=False # Only include items where cost was recorded
    ).aggregate(
        total_cogs=Coalesce(Sum(F('quantity') * F('cost_price')), Decimal('0.00'), output_field=DecimalField())
    )
    total_cogs = cogs_agg['total_cogs']

    # Calculate Gross Profit
    gross_profit = total_revenue - total_cogs

    # Calculate Gross Profit Margin (%)
    gross_profit_margin = (gross_profit / total_revenue * 100) if total_revenue else Decimal('0.00')

    context = {
        'page_title': page_title,
        'total_revenue': total_revenue,
        'total_cogs': total_cogs,
        'gross_profit': gross_profit,
        'gross_profit_margin': gross_profit_margin,
        # Add date filters later
    }
    return render(request, 'reports/profit_loss_report.html', context)
# --- END P&L View ---

