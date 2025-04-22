# core/models.py
from django.db import models

class StoreDetail(models.Model):
    # Basic Info
    name = models.CharField(max_length=200, default="My Stationery Store")
    # Address (using fields similar to Customer for consistency)
    address = models.CharField(max_length=255, blank=True, null=True)
    address_hint = models.CharField(max_length=255, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    # Contact
    phone_number = models.CharField(max_length=50, blank=True, null=True) # Allow multiple numbers or formatted
    email = models.EmailField(max_length=254, blank=True, null=True)
    # Logo - ImageField requires Pillow library (pip install Pillow)
    logo = models.ImageField(
        upload_to='store_logos/', # Subdirectory within MEDIA_ROOT
        blank=True,
        null=True,
        help_text="Upload the store logo (optional)."
        )
    # Add Tax ID, Website, etc. later if needed

    # --- Singleton Enforcement (Simple approach) ---
    # We want only one instance. We can enforce this somewhat in save() or admin.
    def save(self, *args, **kwargs):
        # Check if any StoreDetail object already exists (excluding self if updating)
        if not self.pk and StoreDetail.objects.exists():
             # Optional: Raise error or just prevent saving
             # raise ValidationError("Only one StoreDetail entry allowed.")
             print("WARNING: Attempted to create more than one StoreDetail. Operation cancelled.")
             return # Don't save if trying to create a second one
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or "Store Details"

    class Meta:
        verbose_name = "Store Detail"
        verbose_name_plural = "Store Details" # Usually only one, but admin uses plural