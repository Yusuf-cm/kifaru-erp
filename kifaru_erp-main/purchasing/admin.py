# purchasing/admin.py
from django.contrib import admin
from .models import Supplier, PurchaseOrder, PurchaseLine

class PurchaseLineInline(admin.TabularInline):
    model = PurchaseLine
    extra = 1

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'is_active')

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'supplier', 'warehouse', 'status', 'date_issued')
    list_filter = ('status', 'warehouse')
    inlines = [PurchaseLineInline]