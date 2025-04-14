from django.contrib import admin
from .models import Product, Category # Import Category

# Register Category model
@admin.register(Category) # Use decorator for cleaner registration
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)} # Auto-fills slug based on name (optional but nice)

# Customize Product admin
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # Add 'low_stock_threshold' here
    list_display = ('name', 'category', 'manufacturer', 'selling_price', 'cost_price', 'stock_quantity', 'low_stock_threshold', 'updated_at') # <-- Added threshold
    list_filter = ('category', 'manufacturer', 'created_at')
    search_fields = ('name', 'description', 'manufacturer')
    # Add 'low_stock_threshold' here too if you want quick edits
    list_editable = ('selling_price', 'stock_quantity', 'low_stock_threshold') # <-- Added threshold
    prepopulated_fields = {}
    ordering = ('-updated_at',)