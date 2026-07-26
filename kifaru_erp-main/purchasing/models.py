# purchasing/models.py
from django.db import models
from django.contrib.auth.models import User
from inventory.models import Product, Warehouse
from core.models import DocumentSequence

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('RECEIVED', 'Received (Stock Added)'),
        ('CANCELLED', 'Cancelled'),
    ]
    po_number = models.CharField(max_length=50, unique=True, blank=True, help_text="Auto-generated PO number")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, help_text="Where the stock goes")
    date_issued = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='DRAFT')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)

    def save(self, *args, **kwargs):
        if not self.po_number:
            self.po_number = DocumentSequence.get_next_number('PO')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.po_number} - {self.supplier.name} [{self.status}]"

class PurchaseLine(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, related_name='lines', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, help_text="Cost per item in KES")

    def get_total(self):
        return self.quantity * self.unit_cost

    def __str__(self):
        return f"{self.quantity} x {self.product.name} @ {self.unit_cost}"