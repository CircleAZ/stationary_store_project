# customers/views.py
from django import forms
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Customer, Address
from .forms import CustomerForm
from django.template.loader import render_to_string # Import render_to_string
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse # Import response types
from django.contrib.auth.decorators import login_required # Keep using login_required
from orders.models import Order
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.forms import inlineformset_factory
from django.db import transaction


AddressFormSet = inlineformset_factory(
    Customer,       # Parent model
    Address,        # Inline model
    fields=('address_line', 'landmark', 'city', 'state', 'postal_code', 'country', 'is_primary'), # Fields on Address form
    extra=1,        # How many extra blank forms to display
    can_delete=True, # Allow deleting existing addresses via the formset
    widgets={       # Optional: Apply widgets/styling
        'address_line': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        'landmark': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        'postal_code': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        'city': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        'state': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        'country': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    }
)


def customer_list_view(request):
    customers = Customer.objects.all()
    context = {
        'customers': customers,
    }
    return render(request, 'customers/customer_list.html', context)


# --- NEW Customer Detail View function ---
def customer_detail_view(request, pk):
    """
    Fetches a single customer by their primary key (pk) and displays their details
    using the customer_detail.html template.
    Returns a 404 error if the customer is not found.
    """
    # Use the shortcut to get the Customer object or raise a 404 error if not found
    customer = get_object_or_404(Customer, pk=pk)

    # Prepare the context dictionary to pass the single customer object to the template
    context = {
        'customer': customer, # The key 'customer' will be used in the template
    }

    # Render the detail template (we'll create this next)
    return render(request, 'customers/customer_detail.html', context)


@login_required # Or other permission check
def customer_add_view(request):
    form_title = "Add New Customer"
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        # Instantiate formset with POST data, prefix is important if multiple formsets on page
        address_formset = AddressFormSet(request.POST, prefix='addresses')

        if form.is_valid() and address_formset.is_valid():
            try:
                with transaction.atomic(): # Use transaction for multi-model save
                    new_customer = form.save() # Save Customer first to get PK
                    # Link address formset to the newly created customer instance
                    address_formset.instance = new_customer
                    address_formset.save() # Save related Address objects
                    messages.success(request, f"Customer '{new_customer.full_name}' added successfully!")
                    return redirect('customers:customer_detail', pk=new_customer.pk)
            except Exception as e: # Catch potential errors during save
                 messages.error(request, f"Error saving customer: {e}")
                 # Fall through to render form with errors
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomerForm()
        # Instantiate blank formset for GET request
        address_formset = AddressFormSet(prefix='addresses')

    context = {
        'form': form,
        'address_formset': address_formset, # <-- Pass formset to context
        'form_title': form_title,
    }
    return render(request, 'customers/customer_form.html', context) # Use same template


@login_required # Or other permission check
def customer_edit_view(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form_title = f"Edit Customer: {customer.full_name}"

    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        # Instantiate formset with POST data AND existing customer instance
        address_formset = AddressFormSet(request.POST, instance=customer, prefix='addresses')

        if form.is_valid() and address_formset.is_valid():
            try:
                with transaction.atomic():
                    updated_customer = form.save()
                    # address_formset already linked to instance
                    address_formset.save() # Save changes to addresses (adds/updates/deletes)
                    messages.success(request, f"Customer '{updated_customer.full_name}' updated successfully!")
                    return redirect('customers:customer_detail', pk=updated_customer.pk)
            except Exception as e:
                 messages.error(request, f"Error saving customer: {e}")
                 # Fall through to render form with errors
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomerForm(instance=customer)
        # Instantiate formset pre-filled with existing addresses for this customer
        address_formset = AddressFormSet(instance=customer, prefix='addresses')

    context = {
        'form': form,
        'address_formset': address_formset, # <-- Pass formset to context
        'form_title': form_title,
        'customer': customer,
    }
    return render(request, 'customers/customer_form.html', context) # Use same template

def customer_delete_view(request, pk):
    """
    Handles displaying the confirmation page for deleting a customer (GET)
    and performing the actual deletion upon confirmation (POST).
    """
    # Get the customer object to delete, or 404 if not found
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == 'POST':
        # If the confirmation form was submitted (user clicked "Confirm Delete")
        customer_name = customer.full_name # Store name before deleting for the message
        customer.delete() # Delete the customer object from the database
        messages.success(request, f"Customer '{customer_name}' deleted successfully.")
        # Redirect to the customer list page
        return redirect('customers:customer_list')
    else:
        # If it's a GET request, display the confirmation page
        context = {
            'customer': customer, # Pass the customer object to the template for display
        }
        # Render the confirmation template (we'll create this next)
        return render(request, 'customers/customer_confirm_delete.html', context)


# --- NEW View to render only the customer form HTML ---
@login_required
def customer_add_form_htmx(request): # Renamed slightly to indicate purpose/potential HTMX use
    """ Renders the CustomerForm as an HTML fragment. """
    form = CustomerForm()
    # Render form using a minimal template (or just the form itself)
    # Option 1: Use render_to_string with the existing form template
    # html = render_to_string('customers/customer_form_fields_partial.html', {'form': form}, request=request)
    # return HttpResponse(html)

    # Option 2: (Simpler for now) Render the form directly using Django's built-in methods
    context = {'form': form, 'is_modal': True} # Pass a flag if template needs to know it's in modal
    # Use the existing template but maybe add logic inside it based on 'is_modal' if needed
    # Or create a specific smaller template just for the fields
    return render(request, 'customers/partials/customer_form_fields.html', context)


# --- NEW View to handle modal form submission ---
@login_required
def customer_add_modal_api(request):
    """ Handles POST submission from the Add Customer modal. """
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            try:
                new_customer = form.save()
                # Return success response with new customer details
                return JsonResponse({
                    'success': True,
                    'customer_id': new_customer.pk,
                    'customer_text': f"{new_customer.full_name} ({new_customer.full_phone_number or new_customer.email or 'No contact'})"
                })
            except Exception as e:
                # Catch potential database errors during save
                 return JsonResponse({'success': False, 'errors': {'__all__': f'Error saving customer: {str(e)}'}}, status=500)
        else:
            # Form is invalid, return errors as JSON
            # Convert form.errors dictionary to a JSON-friendly format if needed
            # For simplicity, just send the errors dict directly for now
            return JsonResponse({'success': False, 'errors': form.errors}, status=400) # Bad Request status
    else:
        # Method not allowed
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
def customer_detail_view(request, pk): # Assuming no @login_required needed for public view? Add if needed.
    """
    Fetches a single customer by pk and their associated orders,
    displays details using the customer_detail.html template.
    """
    customer = get_object_or_404(Customer, pk=pk)

    # --- Fetch related orders ---
    # Use the related_name 'orders' from the ForeignKey in the Order model
    # Order them by newest first
    customer_orders = customer.orders.all().order_by('-created_at') # Use .all() here
    # You could add select_related for order fields if needed:
    # customer_orders = customer.orders.select_related('payment_method').all().order_by('-created_at')

    # --- Pagination for Orders (Optional but good if many orders) ---
    paginator = Paginator(customer_orders, 10) # Show 10 orders per page
    page_number = request.GET.get('page') # Check for 'page' GET parameter
    try:
        orders_page = paginator.page(page_number)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)
    # --- End Pagination ---


    context = {
        'customer': customer,
        'orders_page': orders_page, # Pass the paginated orders object
        # 'customer_orders': customer_orders, # Pass this instead if not paginating
        'page_title': f"Customer: {customer.full_name}"
    }
    return render(request, 'customers/customer_detail.html', context)