# orders/admin.py

from django.contrib import admin
from .models import Order, OrderItem, PaymentMethod

class OrderItemInline(admin.TabularInline):
    """
    Allows editing OrderItems directly within the Order admin page.
    """
    model = OrderItem
    # fields = ['product', 'product_name', 'price', 'quantity'] # Specify fields if needed
    readonly_fields = ('product_name', 'price', 'get_cost') # Make snapshot fields read-only after creation? Maybe price too. Cost definitely.
    extra = 0 # Don't show extra blank rows by default
    can_delete = True # Allow deleting items from an order (use cautiously)

    # Display the calculated cost for the line item
    def get_cost(self, obj):
        return obj.get_cost()
    get_cost.short_description = 'Line Total'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Admin view configuration for Orders.
    """
    list_display = (
        'order_id_short', # Custom method for shorter ID display
        'customer_display', # Custom method for customer name or 'Guest'
        'created_at',
        'status',
        'payment_status',
        'total_amount',
        'created_by',
    )
    list_filter = ('status', 'payment_status', 'created_at')
    search_fields = ('order_id__iexact', 'customer__first_name', 'customer__last_name', 'customer__email', 'items__product__name') # Search by UUID, customer details, or product name within items
    readonly_fields = (
        'order_id', # Cannot edit UUID
        'created_at', 'updated_at',
        'created_by', # Usually set automatically
        'subtotal', 'tax_amount', 'total_amount', # Calculated fields (should be read-only here)
        'amount_paid', # Maybe editable depending on workflow? Or just payment status?
    )
    inlines = [OrderItemInline] # Include the OrderItem editor within the Order page
    ordering = ('-created_at',)
    list_per_page = 25

    # --- Custom display methods for list_display ---
    def order_id_short(self, obj):
        return str(obj.order_id)[:8] # Show first 8 chars of UUID
    order_id_short.short_description = 'Order ID'

    def customer_display(self, obj):
        if obj.customer:
            # Optional: Link to customer admin page
            # from django.urls import reverse
            # from django.utils.html import format_html
            # url = reverse('admin:customers_customer_change', args=[obj.customer.pk])
            # return format_html('<a href="{}">{}</a>', url, obj.customer.full_name)
            return obj.customer.full_name
        return "Guest"
    customer_display.short_description = 'Customer'
    # --- End custom methods ---

# --- NEW: Register PaymentMethod ---
@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
# --- END Register PaymentMethod ---
