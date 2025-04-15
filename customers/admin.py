from django.contrib import admin
from .models import Customer

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    # --- MODIFIED list_display ---
    list_display = ('full_name', 'email', 'phone_number', 'address', 'school_grade', 'updated_at') # Removed 'city', added 'address'
    # --- MODIFIED list_filter ---
    list_filter = ('school_grade', 'created_at') # Removed 'city', 'state'
    # --- MODIFIED search_fields ---
    search_fields = ('first_name', 'last_name', 'middle_name', 'email', 'phone_number', 'address', 'address_hint', 'postal_code') # Removed 'city', added 'address', 'address_hint'
    # --- Keep ordering ---
    ordering = ('first_name', 'last_name')
    # Optional: Update fieldsets if you were using them
    # fieldsets = (
    #     (None, {
    #         'fields': (('first_name', 'middle_name', 'last_name'), 'school_grade')
    #     }),
    #     ('Contact Information', {
    #         'fields': ('phone_number', 'email')
    #     }),
    #      ('Address', {
    #         # --- MODIFIED Address fieldset ---
    #         'fields': ('address', 'address_hint', 'postal_code'), # Use new field names
    #         'classes': ('collapse',)
    #     }),
    #     ('Notes', {
    #         'fields': ('notes',),
    #     }),
    # )