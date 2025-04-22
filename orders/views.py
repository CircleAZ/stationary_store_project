# orders/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, F
import json
from django.db import transaction
from decimal import Decimal, InvalidOperation # <-- IMPORT Decimal AND InvalidOperation
from .models import PaymentMethod, Order, OrderItem # <-- IMPORT Order and OrderItem
from customers.models import Customer
from inventory.models import Product
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger # For pagination
from .forms import OrderStatusUpdateForm 
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied

# Create your views here.
def user_in_group(user, group_name):
     return user.groups.filter(name=group_name).exists()


@login_required
def order_create_view(request):
    """
    Displays the Point of Sale interface for creating new orders.
    Passes active payment methods to the template.
    """
    # Fetch active payment methods to populate the dropdown
    
    is_manager = user_in_group(request.user, 'Manager')
    is_salesman = user_in_group(request.user, 'Salesman')
    if not (is_manager or is_salesman or request.user.is_superuser):
        raise PermissionDenied

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
    is_manager = user_in_group(request.user, 'Manager')
    is_salesman = user_in_group(request.user, 'Salesman')
    if not (is_manager or is_salesman or request.user.is_superuser):
        raise PermissionDenied

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
    is_manager = user_in_group(request.user, 'Manager')
    is_salesman = user_in_group(request.user, 'Salesman')
    if not (is_manager or is_salesman or request.user.is_superuser):
        raise PermissionDenied
    
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

                # --- 6. Process Order Items (MODIFIED) ---
                order_subtotal = Decimal('0.00')
                items_to_create_data = [] # Prepare data for bulk create

                for item_data in items_data:
                    product_id = item_data.get('product_id')
                    quantity = int(item_data.get('quantity', 0))
                    price_str = str(item_data.get('price', '0'))

                    if not product_id or quantity <= 0:
                        raise ValueError(f"Invalid item data received: {item_data}")

                    try:
                       price = Decimal(price_str)
                    except InvalidOperation:
                       raise ValueError(f"Invalid price format for item: {item_data}")

                    # Fetch product once
                    product = get_object_or_404(Product.objects.select_related('category'), pk=product_id) # select_related optional

                    # Check stock
                    if product.stock_quantity < quantity:
                         raise ValueError(f"Insufficient stock for {product.name}. Available: {product.stock_quantity}, Requested: {quantity}")

                    # Prepare data for OrderItem creation, including cost price
                    items_to_create_data.append(
                        OrderItem(
                            order=new_order,
                            product=product,
                            product_name=product.name, # Explicitly set name snapshot
                            price=price,              # Selling price snapshot
                            quantity=quantity,
                            cost_price=product.cost_price # <-- ADDED: Explicitly set cost price snapshot
                        )
                    )

                    # Update subtotal (based on selling price)
                    order_subtotal += price * quantity

                    # Update Product Stock (Done later outside loop for bulk update)
                    # product.stock_quantity -= quantity # Moved to bulk update below
                    # product.save(update_fields=['stock_quantity'])

                # --- Bulk Create OrderItems ---
                OrderItem.objects.bulk_create(items_to_create_data)

                # --- Bulk Update Stock (More efficient) ---
                # Prepare updates: {product_pk: quantity_change}
                stock_updates = {}
                for item_data in items_data:
                     product_id = item_data.get('product_id')
                     quantity = int(item_data.get('quantity', 0))
                     if product_id and quantity > 0:
                         stock_updates[product_id] = stock_updates.get(product_id, 0) - quantity

                for prod_pk, qty_change in stock_updates.items():
                    Product.objects.filter(pk=prod_pk).update(stock_quantity=F('stock_quantity') + qty_change) # Note: change is negative


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

# --- NEW View to record additional payment ---
@login_required
@require_POST # Should only be accessed via POST from the form
def order_add_payment_view(request, pk):
    """ Records an additional payment made towards an order. """
    order = get_object_or_404(Order, pk=pk)
    amount_due_before = max(order.total_amount - order.amount_paid, Decimal('0.00'))

    # --- Validation: Check if order can accept payment ---
    if order.payment_status in [Order.PAYMENT_STATUS_PAID, Order.PAYMENT_STATUS_REFUNDED] or \
       order.status == Order.ORDER_STATUS_CANCELLED:
        messages.error(request, "This order cannot receive additional payments.")
        return redirect('orders:order_detail', pk=order.pk)
    if amount_due_before <= 0:
         messages.warning(request, "This order does not have an amount due.")
         return redirect('orders:order_detail', pk=order.pk)
    # --- End Validation ---

    try:
        amount_str = request.POST.get('amount')
        if amount_str is None:
             raise ValueError("Payment amount not provided.")

        additional_amount = Decimal(amount_str)

        # Validate the entered amount
        if additional_amount <= 0:
            raise ValueError("Payment amount must be positive.")
        # Prevent overpayment beyond what's due? Optional, but usually good.
        if additional_amount > amount_due_before + Decimal('0.01'): # Allow for tiny float issues
             messages.warning(request, f"Payment amount (₹{additional_amount:.2f}) exceeds amount due (₹{amount_due_before:.2f}). Adjusting payment to amount due.")
             additional_amount = amount_due_before

        # --- Use a transaction for safety ---
        with transaction.atomic():
            # Update amount paid
            order.amount_paid += additional_amount
            order.amount_paid = round(order.amount_paid, 2) # Mitigate potential floating point issues

            # Recalculate payment status (Backend source of truth)
            if order.amount_paid >= order.total_amount - Decimal('0.01'): # Check if paid in full (with tolerance)
                order.payment_status = Order.PAYMENT_STATUS_PAID
                # Optional: Update order status if payment completes it
                if order.status in [Order.ORDER_STATUS_PENDING, Order.ORDER_STATUS_PROCESSING]:
                    order.status = Order.ORDER_STATUS_COMPLETED # Or specific 'Ready To Ship' etc.
            else:
                order.payment_status = Order.PAYMENT_STATUS_PARTIAL # Must be partial if not fully paid

            # Save the changes
            order.save(update_fields=['amount_paid', 'payment_status', 'status'])

            # Optional: Add logic here to record the specific transaction details
            # (e.g., create a separate PaymentTransaction model instance)
            # payment_ref_add = request.POST.get('payment_reference_add')
            # payment_method_add_id = request.POST.get('payment_method_add_id')
            # ... create PaymentTransaction(...) ...

            messages.success(request, f"₹{additional_amount:.2f} payment recorded successfully for Order {str(order.pk)[:8]}.")

    except (InvalidOperation, ValueError, TypeError) as e:
        messages.error(request, f"Invalid payment amount entered: {e}")
    except Exception as e:
        # Catch unexpected errors
        messages.error(request, f"An error occurred while recording payment: {e}")
        print(f"Error recording payment for order {pk}: {e}") # Log for debugging

    # Always redirect back to the detail page
    return redirect('orders:order_detail', pk=order.pk)
# --- END Add Payment View ---

@login_required
def order_get_items_api(request, pk):
    """ Returns current items for a given order as JSON. """
    order = get_object_or_404(Order.objects.prefetch_related('items', 'items__product'), pk=pk)
    items_data = []
    for item in order.items.all():
        items_data.append({
            'item_id': item.pk, # ID of the OrderItem itself
            'product_id': item.product.pk if item.product else None,
            'product_name': item.product_name, # Use the snapshot name
            'quantity': item.quantity,
            'price': str(item.price), # Send price as string for consistency
             # Optionally send current product stock if needed for validation in modal
             # 'current_stock': item.product.stock_quantity if item.product else 0
        })
    return JsonResponse({'success': True, 'items': items_data})
# --- END API View ---

@login_required
@require_POST # Expect POST with JSON body
def order_update_items_api(request, pk):
    """
    Updates the items within an existing order based on data submitted
    from the edit items modal. Handles stock adjustments and recalculates totals.
    """
    order = get_object_or_404(Order.objects.prefetch_related('items', 'items__product'), pk=pk)

    # --- Validation: Check if order can be edited ---
    if order.status not in [Order.ORDER_STATUS_PENDING, Order.ORDER_STATUS_PROCESSING]:
        return JsonResponse({'success': False, 'error': f'Order cannot be edited in {order.get_status_display()} status.'}, status=400)

    try:
        data = json.loads(request.body)
        submitted_items_data = data.get('items', []) # List of {item_id, product_id, quantity, price}

        with transaction.atomic():
            # Get current items from DB for comparison {item_pk: item_obj}
            current_items_dict = {item.pk: item for item in order.items.all()}
            submitted_item_ids = set() # Keep track of items submitted from modal

            new_subtotal = Decimal('0.00')
            items_to_create = []
            updates_to_perform = [] # Store (item_obj, new_quantity, stock_diff)
            deletions_to_perform = [] # Store item_obj to delete

            # --- Process Submitted Items ---
            for item_data in submitted_items_data:
                item_id = item_data.get('item_id') # Might be 'new' or a PK
                product_id = item_data.get('product_id')
                new_quantity = int(item_data.get('quantity', 0))
                price = Decimal(item_data.get('price')) # Price snapshot

                if not product_id or new_quantity <= 0: continue # Skip invalid data

                product = get_object_or_404(Product, pk=product_id) # Ensure product exists

                if item_id == "new":
                    # --- Handle NEW item ---
                    # Check stock before adding to create list
                    if product.stock_quantity < new_quantity:
                         raise ValueError(f"Insufficient stock for new item {product.name}. Available: {product.stock_quantity}")
                    items_to_create.append({
                        'order': order, 'product': product, 'price': price, 'quantity': new_quantity
                    })
                    updates_to_perform.append((None, 0, -new_quantity, product)) # Stock diff for new item
                    new_subtotal += price * new_quantity
                else:
                    # --- Handle EXISTING item ---
                    item_id = int(item_id) # Convert PK to int
                    submitted_item_ids.add(item_id)
                    if item_id in current_items_dict:
                        current_item = current_items_dict[item_id]
                        # Check if quantity changed
                        if current_item.quantity != new_quantity:
                            stock_diff = current_item.quantity - new_quantity # Positive if stock goes UP, negative if DOWN
                            # Check stock availability if quantity increased
                            if new_quantity > current_item.quantity and product.stock_quantity < (new_quantity - current_item.quantity):
                                raise ValueError(f"Insufficient stock for updated item {product.name}. Available: {product.stock_quantity}")
                            updates_to_perform.append((current_item, new_quantity, stock_diff, product))
                        # Price shouldn't change for existing item, use current_item.price for subtotal
                        new_subtotal += current_item.price * new_quantity
                    else:
                        # Item ID submitted but not found in current order? Error or ignore?
                        print(f"Warning: Submitted item ID {item_id} not found in current order {order.pk}")
                        # For now, ignore potential errors like this

            # --- Handle DELETED items ---
            # Items in DB but not submitted were deleted in the modal
            for item_id, current_item in current_items_dict.items():
                if item_id not in submitted_item_ids:
                    deletions_to_perform.append(current_item)
                    # Stock will be returned when item is deleted
                    updates_to_perform.append((None, 0, current_item.quantity, current_item.product)) # Stock diff for deleted

            # --- Apply DB Changes & Stock Updates ---
            # 1. Delete items marked for deletion
            for item_to_delete in deletions_to_perform:
                item_to_delete.delete()

            # 2. Update quantities for existing items
            for item_obj, new_qty, _, _ in updates_to_perform:
                 if item_obj and new_qty > 0: # Ensure it's an update, not just stock tracking
                     item_obj.quantity = new_qty
                     item_obj.save(update_fields=['quantity'])

            # 3. Create new items
            OrderItem.objects.bulk_create([OrderItem(**data) for data in items_to_create])

            # 4. Update Stock (after all DB changes are settled for items)
            product_stock_updates = {} # {product_pk: total_stock_diff}
            for _, _, stock_diff, product_obj in updates_to_perform:
                 if product_obj: # Make sure product exists
                     product_stock_updates[product_obj.pk] = product_stock_updates.get(product_obj.pk, 0) + stock_diff

            for product_pk, total_diff in product_stock_updates.items():
                 # Use F() expression for atomic update
                 Product.objects.filter(pk=product_pk).update(stock_quantity=F('stock_quantity') + total_diff)


            # --- Recalculate Order Totals ---
            # Ensure discount is Decimal
            discount = order.discount_amount # Use property or re-fetch if needed
            tax_amount = Decimal('0.00') # Placeholder
            new_total_amount = max((new_subtotal + tax_amount) - discount, Decimal('0.00'))

            # Update the Order itself
            order.subtotal = new_subtotal
            order.tax_amount = tax_amount
            order.total_amount = new_total_amount
            # Recalculate payment status based on new total
            if order.amount_paid >= new_total_amount:
                order.payment_status = Order.PAYMENT_STATUS_PAID
                # Optionally update order status again?
                # if order.status == Order.ORDER_STATUS_PROCESSING:
                #    order.status = Order.ORDER_STATUS_COMPLETED
            elif order.amount_paid > Decimal('0.00'):
                order.payment_status = Order.PAYMENT_STATUS_PARTIAL
            else:
                 order.payment_status = Order.PAYMENT_STATUS_PENDING

            order.save(update_fields=['subtotal', 'tax_amount', 'total_amount', 'payment_status', 'status']) # Add status if changed

        # --- End Transaction ---

        return JsonResponse({'success': True, 'message': 'Order items updated successfully.'})

    except ValueError as e: # Catch stock errors or bad quantity/price
         return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Product.DoesNotExist:
         return JsonResponse({'success': False, 'error': 'Invalid product ID found in items.'}, status=400)
    except Exception as e:
        print(f"Error updating order items for {pk}: {e}") # Log error
        return JsonResponse({'success': False, 'error': 'An unexpected error occurred while updating items.'}, status=500)
