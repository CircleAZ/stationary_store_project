# orders/admin.py

from django.contrib import admin
from .models import Order, OrderItem, PaymentMethod, OrderReturn, ReturnItem

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

class ReturnItemInline(admin.TabularInline):
    model = ReturnItem
    # Fields to display in the inline table
    fields = ('order_item_display', 'quantity_returned')
    readonly_fields = ('order_item_display',) # Make original item read-only here
    extra = 1 # Show one blank row for adding items to return
    autocomplete_fields = ['order_item'] # Use autocomplete for selecting OrderItem (optional but nice)

    def order_item_display(self, obj):
        # Show details of the original item being returned
        if obj.order_item:
            return f"{obj.order_item.product_name} (Qty: {obj.order_item.quantity}, Price: ₹{obj.order_item.price})"
        return "---"
    order_item_display.short_description = 'Original Order Item'

    # Optional: Add validation to the formset used by this inline
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Add custom validation, e.g., ensure quantity_returned <= available
        return formset

# --- NEW Admin for Order Returns ---
@admin.register(OrderReturn)
class OrderReturnAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'status', 'total_refund_amount', 'created_at', 'processed_by')
    list_filter = ('status', 'created_at')
    search_fields = ('order__order_id__iexact', 'order__customer__first_name', 'order__customer__last_name')
    readonly_fields = ('created_at', 'updated_at', 'requested_by', 'processed_by', 'total_refund_amount') # Make some fields read-only
    inlines = [ReturnItemInline] # Embed ReturnItem editor
    list_per_page = 25
    ordering = ('-created_at',)

    # Optional: Add actions like 'Mark as Approved', 'Mark as Completed'
    # actions = ['mark_approved', 'mark_completed']

    # def mark_approved(self, request, queryset): ...
    # def mark_completed(self, request, queryset): ...

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product_name', 'quantity', 'price', 'cost_price', 'get_cost')
    list_select_related = ('order', 'product', 'order__customer') # Optimize list view
    search_fields = ('product_name', 'product__name', 'order__order_id__iexact', 'order__customer__first_name', 'order__customer__last_name') # Define search fields
    autocomplete_fields = ['order', 'product'] # Optional: Autocomplete for product/order here too
    list_filter = ('order__created_at', 'product')
    # Make fields generally read-only if primarily managed via Order/Return inlines
    readonly_fields = ('product_name', 'price', 'cost_price') # Make snapshots read-only

    def get_cost(self, obj): # Need the display method here too if used in list_display
        return obj.get_cost()
    get_cost.short_description = 'Line Total (Selling)'