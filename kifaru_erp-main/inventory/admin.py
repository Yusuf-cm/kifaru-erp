# inventory/admin.py
from django.contrib import admin
from .models import ProductCategory, Product, Warehouse, StockMovement

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # We added 'live_stock' to the list_display
    list_display = ('sku', 'name', 'category', 'unit_of_measure', 'live_stock', 'is_active')
    search_fields = ('sku', 'name')
    list_filter = ('category', 'is_active')

    def live_stock(self, obj):
        """ This calls the method we just wrote and displays it in the column """
        stock = obj.get_total_stock()
        # Let's make it look nice. If stock is 0 or negative, flag it.
        if stock <= 0:
            return f"⚠️ {stock}"
        return f"{stock}"
    
    live_stock.short_description = "Total Stock"

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    # Update this line:
    list_display = ('name', 'location', 'is_retail_storefront', 'is_active')

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'movement_type', 'quantity', 'unit_cost', 'timestamp')
    list_filter = ('movement_type', 'warehouse', 'product')
    search_fields = ('reference_document', 'product__sku')
    # Prevent editing/deleting of stock movements in the admin panel!
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False