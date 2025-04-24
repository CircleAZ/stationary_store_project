from django.db import models
from django.urls import reverse # For get_absolute_url later

# Create your models here.

class CustomerGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    # Add other fields later if needed, e.g., discount_percentage

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name
    
class Address(models.Model):
    # Link back to the Customer (One Customer -> Potentially Many Addresses, if using ForeignKey from Address)
    # OR (One Customer -> One Primary Address, if using OneToOneField from Customer)
    # Let's use ForeignKey from Address to Customer for flexibility later (One Customer -> Many Addresses)
    customer = models.ForeignKey(
        'Customer', # Use string 'Customer' to handle definition order
        related_name='addresses',
        on_delete=models.CASCADE # If Customer is deleted, delete their addresses
    )
    # Address Fields (moved from Customer)
    address_line = models.CharField(max_length=255, verbose_name="Address Line")
    landmark = models.CharField(max_length=255, blank=True, null=True, verbose_name="Landmark/Hint")
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True) # Adding City/State back here
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, default="India") # Default country

    is_primary = models.BooleanField(default=False, help_text="Mark as the primary address for this customer.")
    # Add coordinates later if needed: latitude = models.DecimalField(...) longitude = ...

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-is_primary', '-created_at') # Show primary first, then newest
        verbose_name_plural = "Addresses" # Correct pluralization for admin

    def __str__(self):
        # Provide a concise string representation
        parts = [self.address_line, self.city, self.state, self.postal_code, self.country]
        return ", ".join(filter(None, parts)) # Join non-empty parts

    # Optional: Add validation to ensure only one primary address per customer later


class Customer(models.Model):
    # Basic Info
    
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True) # Optional
    last_name = models.CharField(max_length=100)

    country_code = models.CharField(
        max_length=5, # e.g., "+91", "+44", "+1" - adjust length if needed
        blank=True,
        null=True,
        default='+91', # Default to India's code
        verbose_name="Country Code"
    )

    # Contact Info
    phone_number = models.CharField(
        max_length=20, # Max length for local part
        blank=True,
        null=True,
        verbose_name="Phone Number (Local Part)" # Keep verbose name descriptive
    )   
    
    email = models.EmailField(max_length=254, blank=True, null=True, unique=True) # Optional, but must be unique if provided

    # Stationery Store Specific
    school_grade = models.CharField(max_length=50, blank=True, null=True, verbose_name="Class") # Label changed earlier
   # --- Address Fields ---
    # address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Address")
    # address_hint = models.CharField(max_length=255, blank=True, null=True, verbose_name="Address Hint", help_text="E.g., Landmark, Floor, Apartment number")
    # postal_code = models.CharField(max_length=20, blank=True, null=True) # Kept postal code
    # --- END Address Fields ---

    groups = models.ManyToManyField(
        CustomerGroup,
        blank=True, # Customer doesn't have to belong to any group
        related_name="customers"
    )

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

    # --- ADD Property for Full Phone Number ---
    @property
    def full_phone_number(self):
        """Returns the combined country code and local phone number."""
        if self.country_code and self.phone_number:
            # Add a space for readability, adjust if needed
            return f"{self.country_code} {self.phone_number}"
        elif self.phone_number: # If only local part exists (e.g., older data or code missing)
            return self.phone_number
        else:
            return None # Or return an empty string "" if preferred
    # --- END Property ---

    # @property
    # def primary_address(self):
    #     """ Returns the primary address instance or None. """
    #     # .filter().first() is efficient, handles case of no addresses or no primary marked
    #     return self.addresses.filter(is_primary=True).first()

    def __str__(self):
        """String representation of the customer."""
        return self.full_name

    def get_absolute_url(self):
        """Returns the URL to access a particular customer instance."""
        return reverse('customers:customer_detail', args=[str(self.id)])