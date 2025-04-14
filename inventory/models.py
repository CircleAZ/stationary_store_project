from django.db import models
from django.urls import reverse # Import reverse for later use (optional but good practice)

# NEW Category Model
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True) # Category name must be unique
    slug = models.SlugField(max_length=110, unique=True, blank=True) # URL-friendly version of name (auto-populated later)

    class Meta:
        ordering = ('name',) # Default order categories alphabetically by name
        verbose_name = 'category' # How it appears in admin (singular)
        verbose_name_plural = 'categories' # How it appears in admin (plural)

    def __str__(self):
        return self.name

    # Optional: Add a method to get the URL for a category later
    # def get_absolute_url(self):
    #    return reverse('inventory:product_list_by_category', args=[self.slug])

    # We'll add a way to auto-generate the slug later if needed,
    # for now, we can set it manually in the admin.

# Existing Product Model (Needs modification)
# Existing Product Model
class Product(models.Model):
    category = models.ForeignKey(Category, related_name='products', on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    manufacturer = models.CharField(max_length=100, blank=True, null=True)
    stock_quantity = models.IntegerField(default=0)
    # --- NEW FIELD ---
    low_stock_threshold = models.PositiveIntegerField(default=5, help_text="Notify when stock reaches this level or lower.") # <-- ADD THIS LINE
    # --- Existing Fields ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- ADD A HELPER PROPERTY (Optional but useful) ---
    @property
    def is_low_stock(self):
        """Returns True if stock quantity is at or below the threshold."""
        if self.low_stock_threshold is None: # Handle case if threshold wasn't set (though default helps)
            return False
        return self.stock_quantity <= self.low_stock_threshold
    # --- END HELPER PROPERTY ---

    def __str__(self):
        return self.name