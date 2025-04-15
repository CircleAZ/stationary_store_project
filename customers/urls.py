# customers/urls.py

from django.urls import path
from . import views # Import views from the current app directory

app_name = 'customers' # Namespace for these URLs

urlpatterns = [
    # When someone visits the base URL for customers (e.g., /customers/),
    # call the customer_list_view function from views.py
    path('', views.customer_list_view, name='customer_list'),

    # We will add URLs for customer detail, add, edit later
    # path('<int:pk>/', views.customer_detail_view, name='customer_detail'),
    # path('add/', views.customer_add_view, name='customer_add'),
    # path('<int:pk>/edit/', views.customer_edit_view, name='customer_edit'),
]