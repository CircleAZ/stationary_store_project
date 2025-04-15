# customers/forms.py

import re
from django import forms
from .models import Customer # Import the Customer model

class CustomerForm(forms.ModelForm):
    """
    Form for creating and editing Customer objects.
    """
    notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), required=False)
    email = forms.EmailField(required=False)

     # --- ADD Country Code Field ---
    # Define choices - add more or adjust as needed
    COUNTRY_CODE_CHOICES = [
        ('+91', '+91 (India)'),
        ('+1', '+1 (USA/Canada)'),
        ('+44', '+44 (UK)'),
        # Add other relevant codes here
    ]
    country_code = forms.ChoiceField(
        choices=COUNTRY_CODE_CHOICES,
        initial='+91',
        required=False, # Match model's blank=True, null=True
        label="Country Code",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    # --- END Country Code Field ---

     # --- MODIFY Phone Number Field ---
    phone_number = forms.CharField(
        label="Phone Number (local part)",
        max_length=20, # Match model max_length
        required=False, # Match model's blank=True, null=True
        widget=forms.TextInput(attrs={
            'type': 'tel',
            'pattern': r'[\d\s\-()]*',
            'title': 'Enter the main phone number digits only (no country code).',
            'placeholder': '9876543210'
        })
    )
    # --- END MODIFY Phone Number Field ---

    class Meta:
        model = Customer # Link this form to the Customer model
        # Specify the fields from the model to include in the form
        fields = [
            'first_name',
            'middle_name',
            'last_name',
            'country_code',
            'phone_number',
            'email',
            'school_grade',
            'address',
            'address_hint',
            'postal_code',
            'notes',
            # created_at and updated_at are handled automatically by Django
        ]
        # Optional: Customize labels shown next to fields
        labels = {
            'school_grade': 'Class',
            'address_hint': 'Address Hint (Landmark, etc.)',
        }
     # --- ADJUST Phone Validation Method (if desired) ---
    def clean_phone_number(self):
        phone_local_part = self.cleaned_data.get('phone_number')
        if phone_local_part:
            if not re.fullmatch(r'[\d\s\-()]*', phone_local_part):
                raise forms.ValidationError("Local phone number contains invalid characters.")
        return phone_local_part
    # --- END clean_phone_number ---

    # --- Optional: Add clean() method for combined validation ---
    # customers/forms.py
# Inside CustomerForm:

    # --- Optional: Add clean() method for combined validation ---
    def clean(self): # <--- ADD 'self' HERE
        cleaned_data = super().clean() # No change needed here
        country_code = cleaned_data.get("country_code")
        phone_local_part = cleaned_data.get("phone_number")

        # Example: Require local part if country code is entered, and vice-versa
        if country_code and not phone_local_part:
            # Use self.add_error
            self.add_error('phone_number', "Phone number (local part) is required when country code is selected.") # <--- Use self.add_error
        elif phone_local_part and not country_code:
             # Use self.add_error
             self.add_error('country_code', "Country code is required when phone number (local part) is entered.") # <--- Use self.add_error

        # Add more complex validation across fields if needed

        return cleaned_data # Always return the full collection
    # --- END clean() method ---