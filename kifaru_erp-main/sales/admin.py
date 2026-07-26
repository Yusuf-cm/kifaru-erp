# sales/admin.py
from django.contrib import admin, messages
from .models import Customer, Sale, SaleLine, Payment
from .services import complete_sale # <-- IMPORT OUR ENGINE

class SaleLineInline(admin.TabularInline):
    model = SaleLine
    extra = 1

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 1

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone')
    search_fields = ('name', 'phone')

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('receipt_number', 'customer', 'warehouse', 'status', 'created_at', 'cashier')
    list_filter = ('status', 'warehouse')
    inlines = [SaleLineInline, PaymentInline]
    
    # --- THIS ADDS THE BUTTON TO THE ADMIN PANEL ---
    actions = ['action_complete_sale']

    @admin.action(description="🔥 Complete Sale (Deduct Stock & Post to Ledger)")
    def action_complete_sale(self, request, queryset):
        for sale in queryset:
            try:
                complete_sale(sale.id, request.user)
                self.message_user(request, f"Sale {sale.receipt_number} completed successfully!", messages.SUCCESS)
            except Exception as e:
                self.message_user(request, f"Error on {sale.receipt_number}: {str(e)}", level=messages.ERROR)