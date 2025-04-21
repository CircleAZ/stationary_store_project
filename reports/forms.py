# reports/forms.py
from django import forms

class DateRangeForm(forms.Form):
    start_date = forms.DateField(
        required=False, # Allow empty fields to show all time
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'})
    )