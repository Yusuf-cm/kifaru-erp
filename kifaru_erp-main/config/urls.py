# config/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),                  # Executive Dashboard
    path('', include('sales.urls')),                 # POS
    path('inventory/', include('inventory.urls')),   # Inventory
    path('purchasing/', include('purchasing.urls')), # Suppliers & Purchase Orders
    path('accounting/', include('accounting.urls')), # Reports & Ledger
]
