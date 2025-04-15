# customers/urls.py

from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    path('', views.customer_list_view, name='customer_list'),
    path('<int:pk>/', views.customer_detail_view, name='customer_detail'),

    # --- NEW path for adding a customer ---
    path('add/', views.customer_add_view, name='customer_add'), # <-- ADD THIS LINE

    # path('<int:pk>/edit/', views.customer_edit_view, name='customer_edit'), # For later
]