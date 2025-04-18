# customers/urls.py

from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    path('', views.customer_list_view, name='customer_list'),
    path('<int:pk>/', views.customer_detail_view, name='customer_detail'),
    path('add/', views.customer_add_view, name='customer_add'),

    # --- NEW path for editing a customer ---
    # Captures the customer's primary key (pk) from the URL
    path('<int:pk>/edit/', views.customer_edit_view, name='customer_edit'), 
    path('<int:pk>/delete/', views.customer_delete_view, name='customer_delete'),

    # --- NEW URLs for modal form ---
    path('add/form/', views.customer_add_form_htmx, name='customer_add_form_htmx'), # <-- Get form HTML
    path('add/modal_api/', views.customer_add_modal_api, name='customer_add_modal_api'), # <-- Post form data

]