from django.urls import path
from . import views

app_name = 'inventory'

# ... other imports ...
urlpatterns = [
    path('', views.product_list_view, name='product_list'),
    path('category/<slug:category_slug>/', views.product_list_view, name='product_list_by_category'),
    path('product/<int:pk>/', views.product_detail_view, name='product_detail'),

    # --- NEW path for low stock items ---
    path('low-stock/', views.low_stock_list_view, name='low_stock_list'), # <-- ADD THIS LINE
    path('product/add/', views.product_add_view, name='product_add'), 
    path('product/<int:pk>/edit/', views.product_edit_view, name='product_edit'),
    path('product/<int:pk>/delete/', views.product_delete_view, name='product_delete'), 
]