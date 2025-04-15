# customers/admin.py
from django.contrib import admin
from .models import Customer

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    # --- ADD country_code ---
    list_display = ('full_name', 'email', 'full_phone_number', 'address', 'school_grade', 'updated_at') # Display combined number
    # --- ADD country_code ---
    list_filter = ('country_code', 'school_grade', 'created_at') # Allow filtering by code
    # --- ADD country_code ---
    search_fields = ('first_name', 'last_name', 'email', 'phone_number', 'country_code', 'address', 'postal_code') # Search by code or local part
    ordering = ('first_name', 'last_name')
    # fieldsets = (
    #     # ... other groups ...
    #     ('Contact Information', {
    #         # --- ADD country_code ---
    #         'fields': (('country_code', 'phone_number'), 'email') # Group code and local part
    #     }),
    #     # ... other groups ...
    # )
    # Optionally define a method to display full number if not using property directly in list_display
    # def display_full_phone(self, obj):
    #    return obj.full_phone_number
    # display_full_phone.short_description = 'Full Phone'