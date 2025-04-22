# core/urls.py
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('settings/store/', views.store_settings_view, name='store_settings'),
    # Add other settings URLs later (users, tax, etc.)
]