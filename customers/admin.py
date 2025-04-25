# customers/admin.py
from django.contrib import admin
from .models import Customer, CustomerGroup, Address, LocationTag

@admin.register(LocationTag)
class LocationTagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(CustomerGroup)
class CustomerGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

class AddressInline(admin.StackedInline): # Or TabularInline if preferred
    model = Address
    fields = ('address_line', 'landmark', 'postal_code', 'location_tags', 'is_primary')
    extra = 1

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', '__str__', 'postal_code', 'is_primary', 'display_location_tags')
    list_filter = ('is_primary', 'location_tags')
    search_fields = ('customer__first_name', 'customer__last_name', 'address_line', 'postal_code', 'location_tags__name')
    list_select_related = ('customer',)
    autocomplete_fields = ['customer']
    filter_horizontal = ('location_tags',)

    def display_location_tags(self, obj):
        return ", ".join([tag.name for tag in obj.location_tags.all()])
    display_location_tags.short_description = 'Location Tags'

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'full_phone_number', 'school_grade', 'display_groups', 'updated_at') # REMOVED address/city
    list_filter = ('groups', 'school_grade', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'phone_number', 'groups__name',
                     'addresses__address_line', 'addresses__postal_code', 'addresses__location_tags__name')
    ordering = ('first_name', 'last_name')
    # --- Add 'groups' to filter_horizontal for better selection ---
    filter_horizontal = ('groups',) # Makes ManyToMany selection nicer
    # --- End Add ---
    inlines = [AddressInline]
    # --- Method to display groups in list_display ---
    def display_groups(self, obj):
        return ", ".join([group.name for group in obj.groups.all()])
    display_groups.short_description = 'Groups'
    # --- End Method ---
    
    # fieldsets = ( ... ) # Add 'groups' to fieldsets if using them
