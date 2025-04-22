"""
URL configuration for stationery_store_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include # Make sure 'include' is imported

from orders import views as order_views # Alias to avoid name clashes if needed
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    # Inventory URLs (existing)
    path('inventory/', include('inventory.urls')),

    # --- NEW: Include Customer URLs ---
    path('customers/', include('customers.urls')), 

    path('orders/', include('orders.urls')),

    path('api/customers/search/', order_views.customer_search_api, name='api_customer_search'), 
    path('api/products/search/', order_views.product_search_api, name='api_product_search'),

    # --- ADD Payment Method API URL ---
    path('api/payment-methods/add/', order_views.payment_method_add_modal_api, name='api_payment_method_add'), 
    # --- END API Endpoints ---

    # --- ADD Order Create API URL ---
    path('api/orders/create/', order_views.order_create_api, name='api_order_create'),

    path('dashboard/', include('dashboard.urls')),

    path('reports/', include('reports.urls')),
    # We'll add path for core app later

    path('', include('core.urls')),
]

if settings.DEBUG:
    # Add static files serving pattern (might already exist)
    # urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) # Usually handled automatically if using runserver with DEBUG=True

    # Add media files serving pattern
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# --- End Serving ---