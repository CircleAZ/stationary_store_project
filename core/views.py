# core/views.py
from django.http import Http404
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required # Protect view
from .models import StoreDetail
from .forms import StoreDetailForm
from django.core.exceptions import PermissionDenied

def user_in_group(user, group_name):
     return user.groups.filter(name=group_name).exists()

@staff_member_required # Only staff/superusers can access settings
def store_settings_view(request):
    """ Displays and handles updates for store details. """
    if not (user_in_group(request.user, 'Manager') or request.user.is_superuser):
        raise PermissionDenied
    
    page_title = "Store Settings"

    # Get the single instance, or create if it doesn't exist (should exist from admin setup)
    # Using get_object_or_404 is safer if you rely on it being created via admin first.
    # store_detail, created = StoreDetail.objects.get_or_create(pk=1) # Assumes pk=1 if using get_or_create

    # Let's assume it must exist (created via admin) - use get_object_or_404
    try:
        # There should only be one, but filter/get first just in case.
        store_detail = StoreDetail.objects.first()
        if not store_detail:
            # Handle case where it wasn't created - maybe redirect to admin or show error
            # For simplicity now, let's raise an error if setup wasn't done.
            messages.error(request, "Store details have not been configured in the admin yet.")
            # You might want to create one here if needed:
            # store_detail = StoreDetail.objects.create(name="Default Store Name")
            # return redirect('some_other_page') # Redirect if critical error
            # Let's proceed assuming it exists or handle appropriately elsewhere
            # For this example, we'll proceed assuming it should exist from Phase 92 Step 2
            raise Http404("StoreDetail configuration missing.") # Or handle creation

    except StoreDetail.DoesNotExist: # Should not happen if created via admin
         raise Http404("StoreDetail configuration missing.")


    if request.method == 'POST':
        # Handle form submission (including file upload)
        form = StoreDetailForm(request.POST, request.FILES, instance=store_detail)
        if form.is_valid():
            form.save()
            messages.success(request, "Store details updated successfully.")
            return redirect('core:store_settings') # Redirect back to the same page
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # Display the form pre-filled with current details
        form = StoreDetailForm(instance=store_detail)

    context = {
        'page_title': page_title,
        'form': form,
        'store_detail': store_detail # Pass instance for potential display (e.g., current logo)
    }
    return render(request, 'core/store_settings_form.html', context)