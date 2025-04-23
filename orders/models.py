# orders/models.py

from decimal import Decimal
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

    refunded_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        ordering = ('-created_at',) # Show newest orders first by default

    def __str__(self):
        # Show a user-friendly representation
        return f"Order {str(self.order_id)[:8]} - {self.customer.full_name if self.customer else 'Guest'}"

    @property
    def discount_amount(self):
        """ Calculates the total discount applied to the order. """
        # Ensure fields are not None before calculation
        sub = self.subtotal if self.subtotal is not None else Decimal('0.00')
        tax = self.tax_amount if self.tax_amount is not None else Decimal('0.00')
        total = self.total_amount if self.total_amount is not None else Decimal('0.00')
        # Discount is difference between pre-discount total and final total
        discount = (sub + tax) - total
        # Return non-negative discount
        return max(discount, Decimal('0.00'))

    # We'll add methods later to calculate totals based on items

    @property
    def net_amount_paid(self):
         return (self.amount_paid or Decimal('0.00')) - (self.refunded_amount or Decimal('0.00'))


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
    
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True, # Allow null if cost wasn't available/applicable? Or default to 0? Let's allow null for flexibility.
        blank=True,
        help_text="Cost price per unit at the time of order."
    )
    
    quantity = models.PositiveIntegerField(default=1)
    # Add discount fields later if needed (e.g., item_discount_amount)
    quantity_returned = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.pk: # Only set snapshots on initial creation
            if self.product:
                if not self.product_name:
                    self.product_name = self.product.name
                # --- ADD: Store cost_price snapshot ---
                if self.cost_price is None and self.product.cost_price is not None: # Check if not already set and product has cost
                    self.cost_price = self.product.cost_price
                # --- END ADD ---
        super().save(*args, **kwargs) # Call the "real" save() method.

    def get_cost(self): # This calculates selling price * quantity
        if self.price is not None and self.quantity is not None:
            return self.price * self.quantity
        return Decimal('0.00') # Return Decimal

    def get_total_cost_price(self):
        """ Calculates the total cost of goods for this line item """
        if self.cost_price is not None and self.quantity is not None:
            return self.cost_price * self.quantity
        return Decimal('0.00') # Return Decimal if cost is unknown

    def __str__(self):
        return f"{self.quantity} x {self.product_name or 'N/A'} in Order {str(self.order.order_id)[:8]}"

    class Meta:
        ordering = ('order', 'product_name') # Order items within an order

    @property
    def quantity_available_to_return(self):
        return self.quantity - self.quantity_returned
    
class OrderReturn(models.Model):
    RETURN_STATUS_REQUESTED = 'Requested'
    RETURN_STATUS_APPROVED = 'Approved'
    RETURN_STATUS_PROCESSING = 'Processing' # e.g., Stock returned, pending refund
    RETURN_STATUS_COMPLETED = 'Completed' # Refund issued
    RETURN_STATUS_REJECTED = 'Rejected'
    RETURN_STATUS_CHOICES = [
        (RETURN_STATUS_REQUESTED, 'Requested'),
        (RETURN_STATUS_APPROVED, 'Approved'),
        (RETURN_STATUS_PROCESSING, 'Processing'),
        (RETURN_STATUS_COMPLETED, 'Completed'),
        (RETURN_STATUS_REJECTED, 'Rejected'),
    ]

    order = models.ForeignKey(
        Order,
        related_name='returns',
        on_delete=models.CASCADE # If original order deleted, delete return record
    )
    reason = models.TextField(blank=True, null=True, help_text="Reason for the return.")
    status = models.CharField(
        max_length=20,
        choices=RETURN_STATUS_CHOICES,
        default=RETURN_STATUS_REQUESTED
    )
    requested_by = models.ForeignKey(
         settings.AUTH_USER_MODEL,
         related_name='requested_returns',
         on_delete=models.SET_NULL,
         null=True, blank=True
    )
    processed_by = models.ForeignKey(
         settings.AUTH_USER_MODEL,
         related_name='processed_returns',
         on_delete=models.SET_NULL,
         null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True) # Return request date
    updated_at = models.DateTimeField(auto_now=True)   # Last status update date
    total_refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = "Order Return Request"
        verbose_name_plural = "Order Return Requests"

    def __str__(self):
        return f"Return for Order {str(self.order.order_id)[:8]} ({self.get_status_display()})"

class ReturnItem(models.Model):
    order_return = models.ForeignKey(
        OrderReturn,
        related_name='items',
        on_delete=models.CASCADE # If return request deleted, delete its items
    )
    # Link directly to the original OrderItem to know which specific item line is returned
    order_item = models.ForeignKey(
        OrderItem,
        related_name='returned_items',
        on_delete=models.CASCADE # If original OrderItem deleted (unlikely), delete return line
                                  # Or use PROTECT if OrderItem should never be deleted if returned?
    )
    quantity_returned = models.PositiveIntegerField(default=1)
    # Optional: Store refund amount per item if needed for partial refunds
    # item_refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('order_return', 'order_item') # Prevent returning same order item twice on same return request

    def __str__(self):
        return f"{self.quantity_returned} x {self.order_item.product_name} returned for {str(self.order_return.order.order_id)[:8]}"

    # Optional: Add validation in save() to ensure quantity_returned <= order_item.quantity - already_returned_quantity

