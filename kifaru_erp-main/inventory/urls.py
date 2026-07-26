# inventory/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.inventory_dashboard, name='inventory_dashboard'),
    path('products/new/', views.product_create, name='product_create'),
    path('stock/adjust/', views.stock_adjust, name='stock_adjust'),
    path('api/transfer/', views.api_transfer_stock, name='api_transfer_stock'),
]
