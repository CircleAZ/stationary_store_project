# orders/models.py

from django.db import models
from django.conf import settings # To link to the User model
from inventory.models import Product # Import Product from inventory app
from customers.models import Customer # Import Customer from customers app
import uuid # For unique order ID

class PaymentMethod(models.Model):
    name = models.CharField(max_length=50, unique=True, help_text="e.g., Cash, UPI, Credit Card, Store Credit")
    is_active = models.BooleanField(
        default=True,
        help_text="Uncheck to hide this method from selection without deleting it."
    )

    class Meta:
         ordering = ('name',) # Order alphabetically by name
         verbose_name = "Payment Method"
         verbose_name_plural = "Payment Methods"

    def __str__(self):
        return self.name


class Order(models.Model):
    # Define order status choices
    ORDER_STATUS_PENDING = 'Pending'
    ORDER_STATUS_PROCESSING = 'Processing'
    ORDER_STATUS_COMPLETED = 'Completed'
    ORDER_STATUS_CANCELLED = 'Cancelled'
    ORDER_STATUS_CHOICES = [
        (ORDER_STATUS_PENDING, 'Pending'),
        (ORDER_STATUS_PROCESSING, 'Processing'),
        (ORDER_STATUS_COMPLETED, 'Completed'),
        (ORDER_STATUS_CANCELLED, 'Cancelled'),
    ]

    # Define payment status choices
    PAYMENT_STATUS_PENDING = 'Pending'
    PAYMENT_STATUS_PAID = 'Paid'
    PAYMENT_STATUS_PARTIAL = 'Partial'
    PAYMENT_STATUS_REFUNDED = 'Refunded'
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_STATUS_PENDING, 'Pending'),
        (PAYMENT_STATUS_PAID, 'Paid'),
        (PAYMENT_STATUS_PARTIAL, 'Partial'),
        (PAYMENT_STATUS_REFUNDED, 'Refunded'),
    ]

    # Fields for the Order model
    order_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True) # Unique ID for the order
    customer = models.ForeignKey(
        Customer,
        related_name='orders',
        on_delete=models.SET_NULL, # Keep order even if customer is deleted
        null=True,                 # Allow orders without a registered customer (guest checkout)
        blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, # Link to the user who created the order (staff/owner)
        related_name='created_orders',
        on_delete=models.SET_NULL, # Keep order if user is deleted
        null=True,
        blank=True # Optional, but good to know who took the order
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default=ORDER_STATUS_PENDING
    )
    # Financials (Calculated based on OrderItems) - use DecimalField for money
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # Store calculated tax
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    # Add discount fields later if needed (e.g., order_discount_amount)

    # Payment Details
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_STATUS_PENDING
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL, # Keep order record if method deleted, just clear the link
        null=True,
        blank=True,
        related_name='orders'
    )   
    payment_reference = models.CharField(max_length=100, blank=True, null=True) # e.g., UPI transaction ID
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        ordering = ('-created_at',) # Show newest orders first by default

    def __str__(self):
        # Show a user-friendly representation
        return f"Order {str(self.order_id)[:8]} - {self.customer.full_name if self.customer else 'Guest'}"

    # We'll add methods later to calculate totals based on items



class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE) # If Order deleted, delete items
    product = models.ForeignKey(
        Product,
        related_name='order_items',
        on_delete=models.SET_NULL, # Keep item record even if product deleted? Or PROTECT? SET_NULL is safer for history.
        null=True # Allow if product deleted
    )
    # Store product name/details *at the time of order* in case product details change later
    product_name = models.CharField(max_length=255, blank=True) # Snapshot of product name
    price = models.DecimalField(max_digits=10, decimal_places=2) # Price PER UNIT at time of order
    quantity = models.PositiveIntegerField(default=1)
    # Add discount fields later if needed (e.g., item_discount_amount)

    def save(self, *args, **kwargs):
        # Store product name when saving if not already set
        if not self.product_name and self.product:
            self.product_name = self.product.name
        super().save(*args, **kwargs)

    def get_cost(self):
        # Calculate the total cost for this item line
        # --- ADD CHECK FOR None ---
        if self.price is not None and self.quantity is not None:
            return self.price * self.quantity
        return 0 # Or return None, or Decimal('0.00') if you prefer
        # --- END CHECK ---

    def __str__(self):
        return f"{self.quantity} x {self.product_name or 'N/A'} in Order {str(self.order.order_id)[:8]}"

    class Meta:
        ordering = ('order', 'product_name') # Order items within an order