# customers/views.py

from django.shortcuts import render
from .models import Customer # Import the Customer model

# Create your views here.

def customer_list_view(request):
    """
    Fetches all customer objects from the database, orders them,
    and displays them using the customer_list.html template.
    """
    # Get all Customer objects from the database
    # Uses the default ordering defined in the model's Meta class ('last_name', 'first_name')
    customers = Customer.objects.all()

    # Create the context dictionary to pass data to the template
    context = {
        'customers': customers, # The key 'customers' will be used in the template loop
    }

    # Tell Django to render the template located at 'customers/customer_list.html'
    # and pass the 'context' dictionary to it.
    return render(request, 'customers/customer_list.html', context)