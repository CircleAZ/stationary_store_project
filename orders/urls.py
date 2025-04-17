# orders/urls.py
from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # We'll add list/detail views later
    path('', views.order_list_view, name='order_list'),
    path('<uuid:pk>/', views.order_detail_view, name='order_detail'), # Using UUID

    path('create/', views.order_create_view, name='order_create'),
    path('<uuid:pk>/update_status/', views.order_update_status_view, name='order_update_status'),
]