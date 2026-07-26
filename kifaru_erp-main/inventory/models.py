# inventory/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.db.models import Sum
from decimal import Decimal

class ProductCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    # In a full ERP, this is where you link the category to the General Ledger:
    # e.g., inventory_account, cogs_account, revenue_account
    
    class Meta:
        verbose_name_plural = "Product Categories"

    def __str__(self):
        return self.name

class Product(models.Model):
    UNIT_CHOICES = [
        ('PCS', 'Pieces'),
        ('KG', 'Kilograms'),
        ('LTR', 'Liters'),
        ('BOX', 'Boxes'),
    ]
    sku = models.CharField(max_length=50, unique=True, help_text="Stock Keeping Unit (Barcode/ID)")
    name = models.CharField(max_length=255)
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT)
    unit_of_measure = models.CharField(max_length=5, choices=UNIT_CHOICES, default='PCS')

    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'),
                                     help_text="Default buying cost per unit (KES)")
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'),
                                        help_text="Default selling price per unit (KES)")
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'),
                                        help_text="Alert when total stock falls to or below this")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.sku}] {self.name}"

    def get_moving_average_cost(self):
        """
        Weighted-average cost of all stock that has EVER come IN (purchases/returns/positive
        adjustments). Used to value COGS when the item is sold. Falls back to the product's
        default cost_price if no priced inbound movements exist yet.
        """
        from django.db.models import F, Sum
        inbound = self.movements.filter(quantity__gt=0)
        agg = inbound.aggregate(
            qty=Sum('quantity'),
            value=Sum(F('quantity') * F('unit_cost')),
        )
        qty = agg['qty'] or Decimal('0.00')
        value = agg['value'] or Decimal('0.00')
        if qty > 0 and value > 0:
            return (value / qty).quantize(Decimal('0.01'))
        return self.cost_price or Decimal('0.00')
    
    def get_total_stock(self):
        """ Calculates stock across ALL locations """
        result = self.movements.aggregate(total=Sum('quantity'))
        return result['total'] or Decimal('0.00')

    def get_stock_in_warehouse(self, warehouse):
        """ Calculates stock in ONE specific location (e.g., the Storefront) """
        result = self.movements.filter(warehouse=warehouse).aggregate(total=Sum('quantity'))
        return result['total'] or Decimal('0.00')

class Warehouse(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="e.g., Main Store, Mombasa Branch, Retail Floor")
    location = models.CharField(max_length=255, blank=True, null=True)
    
    # ADD THIS LINE:
    is_retail_storefront = models.BooleanField(default=False, help_text="Can POS cashiers sell directly from here?")
    
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class StockMovement(models.Model):
    """
    THE SOURCE OF TRUTH FOR INVENTORY.
    Never update or delete these records. Only insert new ones.
    Positive quantity = Stock IN. Negative quantity = Stock OUT.
    """
    MOVEMENT_TYPES = [
        ('PURCHASE', 'Purchase (In)'),
        ('SALE', 'Sale (Out)'),
        ('TRANSFER', 'Transfer (In/Out)'),
        ('ADJUSTMENT', 'Adjustment (+/-)'),
        ('RETURN', 'Customer Return (In)'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='movements')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='movements')
    movement_type = models.CharField(max_length=15, choices=MOVEMENT_TYPES)
    
    # Quantity can be negative!
    quantity = models.DecimalField(max_digits=10, decimal_places=2) 
    
    # The cost of the item at the exact moment it moved (Crucial for accounting)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, help_text="Cost in KES")
    
    reference_document = models.CharField(max_length=100, help_text="e.g., PO-001, INV-2024-05")
    notes = models.TextField(blank=True, null=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)

    def __str__(self):
        direction = "IN" if self.quantity > 0 else "OUT"
        return f"{self.product.sku} | {self.warehouse.name} | {direction} {abs(self.quantity)} | {self.movement_type}"
    
    def clean(self):
        if self.quantity == 0:
            raise ValidationError("Stock movement quantity cannot be zero.")