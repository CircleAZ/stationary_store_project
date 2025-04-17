# orders/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse # <-- Import JsonResponse
from django.db.models import Q # <-- Import Q objects for complex lookups
from .models import PaymentMethod
from customers.models import Customer
from inventory.models import Product
from django.contrib import messages # Keep messages import if needed elsewhere

# Create your views here.

@login_required # Ensure only logged-in users can access POS
def order_create_view(request):
    """
    Displays the Point of Sale interface for creating new orders.
    Handles GET request initially. POST logic will be complex later.
    """
    # For now, just render the template.
    # We can pass initial data like payment methods later.
    context = {
        'page_title': 'Create New Order (POS)'
    }
    return render(request, 'orders/order_create.html', context)

@login_required
def customer_search_api(request):
    """
    API endpoint to search for customers based on a query parameter 'q'.
    Returns customer data as JSON.
    """
    query = request.GET.get('q', None) # Get the search query from GET params
    customers_data = [] # Initialize empty list for results

    if query:
        # Search across multiple fields using Q objects (OR condition)
        # iContains = case-insensitive contains
        lookup = (
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(phone_number__icontains=query) | # Assumes phone_number stores local part now
            Q(email__icontains=query)
        )
        # Query the database
        customers = Customer.objects.filter(lookup)[:10] # Limit to top 10 results

        # Format the results for JSON response
        for customer in customers:
            customers_data.append({
                'id': customer.pk,
                'text': f"{customer.full_name} ({customer.full_phone_number or customer.email or 'No contact'})" # Display text for dropdown
            })
    else:
        # Optional: Return recent/favorite customers if query is empty? Or just empty list.
        pass # Return empty list if no query

    # Return the data as a JSON response
    return JsonResponse({'results': customers_data})
# --- END Customer Search API View ---

# --- NEW Product Search API View ---
@login_required
def product_search_api(request):
    """
    API endpoint to search for products based on a query parameter 'q'.
    Returns product data (including price) as JSON.
    """
    query = request.GET.get('q', None)
    products_data = []

    if query:
        lookup = (
            Q(name__icontains=query) |
            Q(category__name__icontains=query) | # Search by category name
            Q(manufacturer__icontains=query)    # Search by manufacturer
            # Add SKU or other fields if needed: | Q(sku__iexact=query)
        )
        # Filter products (consider adding .filter(is_active=True) if you have an active flag)
        products = Product.objects.filter(lookup)[:15] # Limit results

        # Format results
        for product in products:
            products_data.append({
                'id': product.pk,
                'text': f"{product.name} ({product.category.name if product.category else 'No Category'})", # Display text
                'price': product.selling_price, # Include current selling price
                'stock': product.stock_quantity # Optional: include stock
            })
    else:
        pass # Return empty list if no query

    return JsonResponse({'results': products_data})
# --- END Product Search API View ---
