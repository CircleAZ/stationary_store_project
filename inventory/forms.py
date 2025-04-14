from django import forms
from .models import Product, Category # Import your models

class ProductForm(forms.ModelForm):
    """
    Form for adding and editing Product objects.
    """
    # Optional: Customize field widgets if needed (e.g., for styling or input types)
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), required=False)
    # Optional: Limit category choices or customize its widget
    # category = forms.ModelChoiceField(queryset=Category.objects.all(), required=False, empty_label="-- Select Category --")

    class Meta:
        model = Product # Specify which model this form is for
        # List the fields from the Product model to include in the form
        fields = [
            'name',
            'category',
            'manufacturer',
            'description',
            'selling_price',
            'cost_price',
            'stock_quantity',
            'low_stock_threshold',
            # 'created_at', 'updated_at' are usually handled automatically
        ]
        # Optional: Add labels or help texts if different from model defaults
        labels = {
            'selling_price': 'Selling Price (₹)',
            'cost_price': 'Cost Price (₹)',
            'low_stock_threshold': 'Low Stock Alert Level',
        }
        # Optional: Add widgets for specific styling or input types
        widgets = {
             'selling_price': forms.NumberInput(attrs={'step': '0.01'}), # HTML5 number input
             'cost_price': forms.NumberInput(attrs={'step': '0.01'}),
             'stock_quantity': forms.NumberInput(attrs={'min': '0'}),
             'low_stock_threshold': forms.NumberInput(attrs={'min': '0'}),
        }
        # Optional: Add help texts
        # help_texts = {
        #     'name': 'Enter the full product name.',
        # }