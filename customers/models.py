from django.db import models
from django.urls import reverse # For get_absolute_url later

# Create your models here.

class Customer(models.Model):
    # Basic Info
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True) # Optional
    last_name = models.CharField(max_length=100)

    # Contact Info
    phone_number = models.CharField(max_length=20, blank=True, null=True) # Optional, consider validation later
    email = models.EmailField(max_length=254, blank=True, null=True, unique=True) # Optional, but must be unique if provided

    # Stationery Store Specific
    school_grade = models.CharField(max_length=50, blank=True, null=True, verbose_name="Class (School Grade)") # Optional

   # --- Address Fields ---
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Address")
    address_hint = models.CharField(max_length=255, blank=True, null=True, verbose_name="Address Hint", help_text="E.g., Landmark, Floor, Apartment number")
    postal_code = models.CharField(max_length=20, blank=True, null=True) # Kept postal code
    # --- END Address Fields ---

    # Other Info
    notes = models.TextField(blank=True, null=True) # General notes/preferences

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('last_name', 'first_name') # Order customers by name
        # Ensure unique combination of first name, last name, and phone? Maybe too strict for now.
        # unique_together = [['first_name', 'last_name', 'phone_number']]

    @property
    def full_name(self):
        """Returns the customer's full name."""
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        """String representation of the customer."""
        return self.full_name

    def get_absolute_url(self):
        """Returns the URL to access a particular customer instance."""
        return reverse('customers:customer_detail', args=[str(self.id)])