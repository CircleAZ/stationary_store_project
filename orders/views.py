# orders/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
import json
from django.db import transaction
from decimal import Decimal, InvalidOperation # <-- IMPORT Decimal AND InvalidOperation
from .models import PaymentMethod, Order, OrderItem # <-- IMPORT Order and OrderItem
from customers.models import Customer
from inventory.models import Product
from django.contrib import messages

# Create your views here.

@login_required
def order_create_view(request):
    """
    Displays the Point of Sale interface for creating new orders.
    Passes active payment methods to the template.
    """
    # Fetch active payment methods to populate the dropdown
    payment_methods = PaymentMethod.objects.filter(is_active=True)

    context = {
        'page_title': 'Create New Order (POS)',
        'payment_methods': payment_methods, # Pass methods to context
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

@login_required
def payment_method_add_modal_api(request):
    """ Handles POST submission from the Add Payment Method modal. """
    if request.method == 'POST':
        method_name = request.POST.get('name', '').strip()
        error_message = None

        if not method_name:
            error_message = "Payment method name cannot be empty."
        elif PaymentMethod.objects.filter(name__iexact=method_name).exists():
            error_message = f"Payment method '{method_name}' already exists."

        if error_message:
            return JsonResponse({'success': False, 'error': error_message}, status=400)
        else:
            try:
                new_method = PaymentMethod.objects.create(name=method_name, is_active=True)
                return JsonResponse({
                    'success': True,
                    'method_id': new_method.pk,
                    'method_name': new_method.name
                })
            except Exception as e:
                return JsonResponse({'success': False, 'error': f'Error saving payment method: {str(e)}'}, status=500)
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
# --- NEW View to handle final order creation ---
@login_required
def order_create_api(request):
    """ API endpoint to receive POS data and create an order. """
    if request.method == 'POST':
        try:
            # Decode JSON data sent from JavaScript
            data = json.loads(request.body)

            # --- 1. Extract Data ---
            customer_id = data.get('customer_id') # Can be None or empty string
            items_data = data.get('items', []) # List of {product_id, quantity, price}
            discount_str = str(data.get('discount', '0')) # Ensure string for Decimal conversion
            payment_method_id = data.get('payment_method_id')
            amount_paid_str = str(data.get('amount_paid', '0')) # Ensure string
            payment_status = data.get('payment_status')
            order_status = data.get('order_status')
            payment_reference = data.get('payment_reference', '')

            # --- 2. Basic Validation ---
            if not items_data:
                return JsonResponse({'success': False, 'error': 'Cannot create an empty order.'}, status=400)
            if payment_status not in [choice[0] for choice in Order.PAYMENT_STATUS_CHOICES]:
                 return JsonResponse({'success': False, 'error': 'Invalid payment status.'}, status=400)
            if order_status not in [choice[0] for choice in Order.ORDER_STATUS_CHOICES]:
                 return JsonResponse({'success': False, 'error': 'Invalid order status.'}, status=400)

            # --- 3. Prepare Data Structures ---
            customer = None
            if customer_id:
                customer = get_object_or_404(Customer, pk=customer_id) # Ensure customer exists if ID provided

            payment_method = None
            if payment_method_id:
                payment_method = get_object_or_404(PaymentMethod, pk=payment_method_id)

            try:
                discount = Decimal(discount_str)
                amount_paid = Decimal(amount_paid_str)
            except InvalidOperation:
                 return JsonResponse({'success': False, 'error': 'Invalid number format for discount or amount paid.'}, status=400)


            # --- 4. Database Transaction ---
            with transaction.atomic(): # Ensure all operations succeed or fail together
                # --- 5. Create Order Instance (Initial) ---
                new_order = Order.objects.create(
                    customer=customer,
                    created_by=request.user, # Assign logged-in user
                    status=order_status,
                    payment_status=payment_status,
                    payment_method=payment_method,
                    payment_reference=payment_reference,
                    # Totals will be calculated after items are added
                    # Discount will be applied when calculating total
                    amount_paid=amount_paid
                )

                # --- 6. Process Order Items ---
                order_subtotal = Decimal('0.00')
                for item_data in items_data:
                    product_id = item_data.get('product_id')
                    quantity = int(item_data.get('quantity', 0))
                    price_str = str(item_data.get('price', '0')) # Price snapshot from JS

                    if not product_id or quantity <= 0:
                        # Should have been validated by JS, but double-check
                        raise ValueError(f"Invalid item data received: {item_data}")

                    try:
                       price = Decimal(price_str)
                    except InvalidOperation:
                       raise ValueError(f"Invalid price format for item: {item_data}")

                    product = get_object_or_404(Product, pk=product_id)

                    # Check stock (optional but recommended)
                    if product.stock_quantity < quantity:
                         raise ValueError(f"Insufficient stock for {product.name}. Available: {product.stock_quantity}, Requested: {quantity}")

                    # Create OrderItem
                    OrderItem.objects.create(
                        order=new_order,
                        product=product,
                        # product_name is set automatically by OrderItem's save() method
                        price=price, # Use price sent from JS (snapshot)
                        quantity=quantity
                    )

                    # Update subtotal
                    order_subtotal += price * quantity

                    # Update Product Stock
                    product.stock_quantity -= quantity
                    product.save(update_fields=['stock_quantity']) # Efficiently save only stock

                # --- 7. Calculate Final Totals & Update Order ---
                # Add tax calculation logic here if needed (e.g., tax_rate = Decimal('0.05'))
                tax_amount = Decimal('0.00') # Placeholder for tax
                total_amount = (order_subtotal + tax_amount) - discount

                # Ensure total isn't negative after discount
                total_amount = max(total_amount, Decimal('0.00'))

                new_order.subtotal = order_subtotal
                new_order.tax_amount = tax_amount
                new_order.total_amount = total_amount
                # Maybe update payment status based on amount_paid vs total_amount?
                if amount_paid >= total_amount and payment_status != Order.PAYMENT_STATUS_REFUNDED:
                     new_order.payment_status = Order.PAYMENT_STATUS_PAID
                elif amount_paid > 0 and payment_status != Order.PAYMENT_STATUS_REFUNDED:
                     new_order.payment_status = Order.PAYMENT_STATUS_PARTIAL
                # Save calculated totals
                new_order.save(update_fields=['subtotal', 'tax_amount', 'total_amount', 'payment_status'])


            # --- 8. Return Success Response ---
            # Generate URL for the newly created order's detail page (need to create this view/url later)
            # order_detail_url = reverse('orders:order_detail', args=[new_order.pk])
            return JsonResponse({
                'success': True,
                'order_id': new_order.pk,
                'message': 'Order created successfully!'
                # 'redirect_url': order_detail_url # Send URL for JS to redirect
            })

        except (ValueError, InvalidOperation, Product.DoesNotExist, Customer.DoesNotExist, PaymentMethod.DoesNotExist) as e:
             # Handle specific expected errors during processing
             return JsonResponse({'success': False, 'error': str(e)}, status=400)
        except Exception as e:
             # Handle unexpected errors
             print(f"Unexpected error creating order: {e}") # Log for debugging
             return JsonResponse({'success': False, 'error': 'An unexpected error occurred.'}, status=500)
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

