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
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger # For pagination
from decimal import Decimal
from .forms import OrderStatusUpdateForm 
from django.views.decorators.http import require_POST

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

           # --- 1. Extract Data (MODIFIED) ---
            customer_id = data.get('customer_id')
            items_data = data.get('items', [])
            discount_str = str(data.get('discount', '0'))
            payment_method_id = data.get('payment_method_id')
            # --- Change 'amount_paid' key to match input name ---
            initial_payment_str = str(data.get('initial_payment', '0')) # <-- Use 'initial_payment'
            # --- End Change ---
            payment_status = data.get('payment_status') # JS suggested this, but backend recalculates below
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
                # --- Use initial_payment_str ---
                initial_payment = Decimal(initial_payment_str) # <-- Convert initial payment
                # --- End Change ---
            except InvalidOperation:
                 return JsonResponse({'success': False, 'error': 'Invalid number format for discount or initial payment.'}, status=400)


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
                    amount_paid=initial_payment
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

                new_order.subtotal = order_subtotal
                new_order.tax_amount = tax_amount
                new_order.total_amount = max((order_subtotal + tax_amount) - discount, Decimal('0.00'))
                # Maybe update payment status based on amount_paid vs total_amount?
                if new_order.amount_paid >= new_order.total_amount:
                     final_payment_status = Order.PAYMENT_STATUS_PAID
                elif new_order.amount_paid > Decimal('0.00'):
                     final_payment_status = Order.PAYMENT_STATUS_PARTIAL
                else:
                     final_payment_status = Order.PAYMENT_STATUS_PENDING

                new_order.payment_status = final_payment_status
                # Save calculated totals
                if final_payment_status in [Order.PAYMENT_STATUS_PAID, Order.PAYMENT_STATUS_PARTIAL]:
                     new_order.status = Order.ORDER_STATUS_PROCESSING # Or use status sent from JS? Decide workflow.
                else:
                     new_order.status = Order.ORDER_STATUS_PENDING # Or use status sent from JS?

                new_order.save(update_fields=['subtotal', 'tax_amount', 'total_amount', 'payment_status', 'status']) # Add status


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

@login_required
def order_list_view(request):
    """ Displays a list of all past orders, potentially paginated. """
    # Get all orders, use select_related for efficiency to fetch related Customer/User
    order_list = Order.objects.select_related('customer', 'created_by').all() # .all() implies default ordering ('-created_at')

    # Pagination (Optional but recommended for long lists)
    paginator = Paginator(order_list, 20) # Show 20 orders per page
    page_number = request.GET.get('page')
    try:
        orders = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        orders = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        orders = paginator.page(paginator.num_pages)


    context = {
        'orders': orders, # Pass the paginated orders object
        'page_title': 'Order History'
    }
    return render(request, 'orders/order_list.html', context)

@login_required
def order_detail_view(request, pk):
    """ Displays the details of a single order and the status update form. """
    order = get_object_or_404(
        Order.objects.select_related('customer', 'created_by', 'payment_method')
                     .prefetch_related('items', 'items__product'),
        pk=pk
    )

    # --- Calculate amount due ---
    
    amount_due = max(order.total_amount - order.amount_paid, Decimal('0.00'))
    # --- End calculation ---

    status_update_form = OrderStatusUpdateForm(initial={'status': order.status})

    context = {
        'order': order,
        'amount_due': amount_due,
        'status_update_form': status_update_form, # <-- Pass form to context
        'page_title': f'Order Details {str(order.pk)[:8]}'
    }
    return render(request, 'orders/order_detail.html', context)

@login_required
@require_POST # This view should only accept POST requests
def order_update_status_view(request, pk):
    """ Handles POST request to update the status of a specific order. """
    order = get_object_or_404(Order, pk=pk)
    form = OrderStatusUpdateForm(request.POST) # Bind POST data to the form

    if form.is_valid():
        new_status = form.cleaned_data['status']

        # Optional: Add logic here to check if status transition is valid
        # (e.g., cannot go from Completed back to Pending?)
        # For now, we allow any valid status change.

        order.status = new_status
        order.save(update_fields=['status']) # Save only the status field
        messages.success(request, f"Order {str(order.pk)[:8]} status updated to '{order.get_status_display()}'.")
    else:
        # This shouldn't happen with a simple choice field unless request is manipulated,
        # but good to handle it. Maybe add error message based on form.errors
        messages.error(request, "Invalid status selected.")

    # Always redirect back to the order detail page
    return redirect('orders:order_detail', pk=order.pk)
# --- END Status Update View ---