# customers/views.py

from django.shortcuts import render, get_object_or_404, redirect # Add redirect
from django.contrib import messages # Import messages
from .models import Customer
from .forms import CustomerForm # <-- Import the new form

# Existing customer_list_view function...
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


def customer_add_view(request):
    """
    Handles displaying the form to add a new customer (GET request)
    and processing the submitted form data (POST request).
    """
    form_title = "Add New Customer" # Title for the template

    if request.method == 'POST':
        form = CustomerForm(request.POST) # Or CustomerForm(request.POST, instance=customer) for edit
        if form.is_valid():
            # form.save() now correctly saves both country_code and phone_number
            new_or_updated_customer = form.save()
            messages.success(...)
            return redirect(...) # Redirect works as before
        else:
            messages.error(request, "Please correct the errors below.")
    else:
         form = CustomerForm() # Or CustomerForm(instance=customer) for edit
    
    # Prepare the context data for the template
    context = {
        'form': form,          # The form instance (blank or with errors)
        'form_title': form_title, # The title for the page/card
    }
    # Render the form template (we'll reuse this for editing later)
    return render(request, 'customers/customer_form.html', context)