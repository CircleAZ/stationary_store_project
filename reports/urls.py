# reports/urls.py
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Path for the main sales summary report
    path('sales/', views.sales_summary_report_view, name='sales_summary'),
    # Add more report URLs later (e.g., sales_by_product, profit_loss)
    path('sales/by_product/', views.sales_by_product_report_view, name='sales_by_product'),
    path('sales/by_customer/', views.sales_by_customer_report_view, name='sales_by_customer'),
    path('profit_loss/', views.profit_loss_report_view, name='profit_loss'),
    

]