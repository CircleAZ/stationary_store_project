# stationery_store_project/urls.py
from django.contrib import admin
from django.urls import path, include # Ensure include is imported
from django.conf import settings
from django.conf.urls.static import static
from orders import views as order_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- Add Django's built-in auth URLs ---
    # Provides URLs like /accounts/login/, /accounts/logout/, /accounts/password_change/, etc.
    path('accounts/', include('django.contrib.auth.urls')),

    # Your App URLs
    path('inventory/', include('inventory.urls')),
    path('customers/', include('customers.urls')),
    path('orders/', include('orders.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('reports/', include('reports.urls')),
    path('', include('core.urls')), # Assuming core handles '/settings/store/' etc.

    # API Endpoints
    path('api/customers/search/', order_views.customer_search_api, name='api_customer_search'),
    path('api/products/search/', order_views.product_search_api, name='api_product_search'),
    path('api/payment-methods/add/', order_views.payment_method_add_modal_api, name='api_payment_method_add'),
    path('api/orders/create/', order_views.order_create_api, name='api_order_create'),
]

# --- Media/Static Serving (Keep this) ---
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
