# sales/models.py
from django.db import models
from django.contrib.auth.models import User
from inventory.models import Product, Warehouse

class Customer(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, unique=True, help_text="Crucial for M-Pesa tracking")
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"

class Sale(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft (Scanning items)'),
        ('PAID', 'Paid & Completed'),
        ('REFUNDED', 'Refunded'),
    ]
    receipt_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, help_text="Where stock is sold from")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='DRAFT')
    
    created_at = models.DateTimeField(auto_now_add=True)
    cashier = models.ForeignKey(User, on_delete=models.PROTECT)

    def __str__(self):
        return f"Receipt: {self.receipt_number} [{self.status}]"

class SaleLine(models.Model):
    sale = models.ForeignKey(Sale, related_name='lines', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Selling price in KES")

    def get_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.quantity} x {self.product.name} @ {self.unit_price}"

class Payment(models.Model):
    METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('MPESA', 'M-Pesa Till/Paybill'),
        ('BANK', 'Bank Transfer'),
    ]
    sale = models.ForeignKey(Sale, related_name='payments', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    reference_code = models.CharField(max_length=50, blank=True, null=True, help_text="e.g., M-Pesa Transaction ID")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.method}: {self.amount} KES for {self.sale.receipt_number}"