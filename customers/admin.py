# customers/admin.py
from django.contrib import admin
from .models import Customer, CustomerGroup, Address

@admin.register(CustomerGroup)
class CustomerGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

class AddressInline(admin.StackedInline): # Or TabularInline if preferred
    model = Address
    fields = ('address_line', 'landmark', 'city', 'state', 'postal_code', 'country', 'is_primary')
    extra = 1

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'full_phone_number', 'school_grade', 'display_groups', 'updated_at') # REMOVED address/city
    list_filter = ('groups', 'school_grade', 'created_at') # REMOVED city/state
    search_fields = ('first_name', 'last_name', 'email', 'phone_number', 'groups__name',
                 'addresses__address_line', 'addresses__city', 'addresses__postal_code') # UPDATED to search related address fields
    ordering = ('first_name', 'last_name')
    # --- Add 'groups' to filter_horizontal for better selection ---
    filter_horizontal = ('groups',) # Makes ManyToMany selection nicer
    # --- End Add ---

    # --- Method to display groups in list_display ---
    def display_groups(self, obj):
        return ", ".join([group.name for group in obj.groups.all()])
    display_groups.short_description = 'Groups'
    # --- End Method ---

    # fieldsets = ( ... ) # Add 'groups' to fieldsets if using them

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', '__str__', 'city', 'state', 'is_primary') # Show customer link and string rep
    list_filter = ('city', 'state', 'is_primary', 'country')
    search_fields = ('customer__first_name', 'customer__last_name', 'address_line', 'city', 'postal_code')
    list_select_related = ('customer',) # Optimize customer fetch
    autocomplete_fields = ['customer'] # Autocomplete for customer selection