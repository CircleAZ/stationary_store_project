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

def customer_edit_view(request, pk):
    """
    Handles displaying the form pre-filled with an existing customer's data (GET)
    and processing the submitted form data to update that customer (POST).
    """
    # Get the specific customer object to edit, or return 404 if not found
    customer = get_object_or_404(Customer, pk=pk)
    form_title = f"Edit Customer: {customer.full_name}" # Dynamic title for the page

    if request.method == 'POST':
        # If data was submitted, bind it to the form AND the existing customer instance
        form = CustomerForm(request.POST, instance=customer) # Pass instance=customer
        if form.is_valid():
            # If data is valid, save changes to the existing customer object
            updated_customer = form.save()
            messages.success(request, f"Customer '{updated_customer.full_name}' updated successfully!")
            # Redirect back to the customer's detail page
            return redirect('customers:customer_detail', pk=updated_customer.pk)
        else:
            # If form is invalid, display errors
            messages.error(request, "Please correct the errors below.")
            # Fall through to render the form again (with errors)
    else:
        # If it's a GET request, create form instance pre-populated with the customer's data
        form = CustomerForm(instance=customer) # Pass instance=customer to pre-fill

    # Prepare context for the template (reusing customer_form.html)
    context = {
        'form': form,
        'form_title': form_title,
        'customer': customer, # Pass the customer object itself for the template's conditional logic
    }
    # Render the *same* template used for adding
    return render(request, 'customers/customer_form.html', context)

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
