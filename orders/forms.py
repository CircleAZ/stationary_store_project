# orders/forms.py
from django import forms
from .models import Order # Import the Order model to get choices

class OrderStatusUpdateForm(forms.Form):
    """
    A simple form to update only the status of an Order.
    """
    # Create a ChoiceField populated with the status choices from the Order model
    status = forms.ChoiceField(
        choices=Order.ORDER_STATUS_CHOICES,
        # Add Bootstrap class for styling the dropdown
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )