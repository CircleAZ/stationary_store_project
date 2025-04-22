# core/forms.py
from django import forms
from .models import StoreDetail

class StoreDetailForm(forms.ModelForm):
    class Meta:
        model = StoreDetail
        # Include all editable fields
        fields = [
            'name',
            'address',
            'address_hint',
            'postal_code',
            'phone_number',
            'email',
            'logo', # Include the ImageField
        ]
        widgets = {
            # Optional: Add styling/attributes if needed
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'address_hint': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'type': 'tel'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}), # Provides "Clear" checkbox
        }