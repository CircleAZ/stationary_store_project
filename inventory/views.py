from django.shortcuts import render, get_object_or_404, redirect # <-- Add redirect
from .models import Product, Category
from .forms import ProductForm # <-- Import the form
from django.db.models import F
from django.contrib import messages # <-- Import messages framework
from django.core.exceptions import PermissionDenied

def user_in_group(user, group_name):
     return user.groups.filter(name=group_name).exists()

# Modified product_list_view
def product_list_view(request, category_slug=None): # Add category_slug=None as optional argument
    """
    Fetches and displays products.
    If category_slug is provided, filters products by that category.
    Also fetches all categories for displaying navigation/filtering links.
    """
    categories = Category.objects.all() # Get all categories for navigation
    products = Product.objects.all() # Start with all products (add .filter(available=True) later)
    current_category = None # Initialize current_category

    if category_slug:
        # If a slug is provided, get the category object
        current_category = get_object_or_404(Category, slug=category_slug)
        # Filter the products to only include those in the current category
        products = products.filter(category=current_category)

    # Always order products by name after filtering (or not)
    products = products.order_by('name')

    context = {
        'products': products,           # The list of products (filtered or all)
        'categories': categories,       # All categories for navigation/display
        'current_category': current_category, # The specific category being viewed (or None)
    }
    return render(request, 'inventory/product_list.html', context)

# Existing product_detail_view function (no changes needed here)
def product_detail_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    context = {
        'product': product,
    }
    return render(request, 'inventory/product_detail.html', context)



# ... existing views ...

# --- NEW Low Stock View ---
def low_stock_list_view(request):
    """
    Fetches and displays products where stock quantity is less than or equal
    to their low_stock_threshold.
    """
    # Filter products using F expression to compare two fields
    low_stock_products = Product.objects.filter(
        stock_quantity__lte=F('low_stock_threshold') # stock_quantity <= low_stock_threshold
    ).order_by('stock_quantity') # Order by quantity, lowest first

    context = {
        'low_stock_products': low_stock_products,
    }
    return render(request, 'inventory/low_stock_list.html', context)

def product_add_view(request):
    """
    Handles displaying the form to add a new product (GET)
    and processing the submitted form data (POST).
    """

    if not (user_in_group(request.user, 'Manager') or request.user.is_superuser):
        raise PermissionDenied

    if request.method == 'POST':
        # If the form was submitted, process the data
        form = ProductForm(request.POST) # Bind data from the request to the form
        if form.is_valid():
            # If the form data is valid, save the new product to the database
            new_product = form.save()
            # Add a success message (optional)
            messages.success(request, f"Product '{new_product.name}' added successfully!")
            # Redirect to the new product's detail page
            return redirect('inventory:product_detail', pk=new_product.pk)
        else:
            # If the form is invalid, validation errors will be in form.errors
            # The form object (now containing errors) will be passed to the template below
             messages.error(request, "Please correct the errors below.") # Optional error message
    else:
        # If it's a GET request, display a blank form
        form = ProductForm()

    # Prepare the context for the template
    context = {
        'form': form,
        'form_title': 'Add New Product' # Pass a title for the template
    }
    # Render the template used for the form (we'll create product_form.html)
    return render(request, 'inventory/product_form.html', context)

def product_edit_view(request, pk):
    """
    Handles displaying the form pre-filled with an existing product's data (GET)
    and processing the submitted form data to update the product (POST).
    """
    if not (user_in_group(request.user, 'Manager') or request.user.is_superuser):
        raise PermissionDenied

    # Get the specific product object we want to edit, or return 404 if not found
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        # If the form was submitted, process the data, linking it to the existing product instance
        form = ProductForm(request.POST, instance=product) # *** Key difference: Pass instance=product ***
        if form.is_valid():
            # If the form data is valid, save the changes to the existing product
            updated_product = form.save()
            messages.success(request, f"Product '{updated_product.name}' updated successfully!")
            # Redirect to the product's detail page
            return redirect('inventory:product_detail', pk=updated_product.pk)
        else:
            # If the form is invalid, display errors
            messages.error(request, "Please correct the errors below.")
            # The form object (with errors and submitted data) will be passed to the template
    else:
        # If it's a GET request, create a form instance pre-populated with the existing product's data
        form = ProductForm(instance=product) # *** Key difference: Pass instance=product ***

    # Prepare the context for the template (reusing product_form.html)
    context = {
        'form': form,
        'form_title': f'Edit Product: {product.name}', # Dynamic title
        'product': product # Pass product object for potential use in template (e.g., delete button later)
    }
    # Render the *same* template used for adding
    return render(request, 'inventory/product_form.html', context)

def product_delete_view(request, pk):
    """
    Handles displaying the confirmation page for deleting a product (GET)
    and performing the actual deletion upon confirmation (POST).
    """
    if not (user_in_group(request.user, 'Manager') or request.user.is_superuser):
        raise PermissionDenied

    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        # Confirmation form submitted
        product_name = product.name # Get name for message before deleting
        product.delete()
        messages.success(request, f"Product '{product_name}' deleted successfully.")
        # Redirect back to the main product list
        return redirect('inventory:product_list')
    else:
        # Show confirmation page
        context = {
            'product': product, # Pass product to template
        }
        # Use a generic confirmation template name or a specific one
        return render(request, 'inventory/product_confirm_delete.html', context)