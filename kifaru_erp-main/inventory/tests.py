from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Product, ProductCategory, StockMovement, Warehouse
from .services import execute_stock_transfer


class StockTransferTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('cashier', password='pass')
        self.category = ProductCategory.objects.create(name='Groceries')
        self.product = Product.objects.create(
            sku='SG-2KG', name='Sugar 2kg', category=self.category,
            cost_price=Decimal('240'), selling_price=Decimal('320'),
        )
        self.main_store = Warehouse.objects.create(name='Main Store')
        self.branch = Warehouse.objects.create(name='Branch')
        StockMovement.objects.create(
            product=self.product, warehouse=self.main_store, movement_type='ADJUSTMENT',
            quantity=Decimal('10'), unit_cost=Decimal('240'),
            reference_document='OPENING', created_by=self.user,
        )

    def test_transfer_moves_stock_between_warehouses(self):
        execute_stock_transfer(
            self.product, self.main_store, self.branch, Decimal('4'), self.user,
        )
        self.assertEqual(self.product.get_stock_in_warehouse(self.main_store), Decimal('6'))
        self.assertEqual(self.product.get_stock_in_warehouse(self.branch), Decimal('4'))

    def test_transfer_fails_when_insufficient_stock(self):
        with self.assertRaises(ValidationError):
            execute_stock_transfer(
                self.product, self.main_store, self.branch, Decimal('999'), self.user,
            )

    def test_transfer_fails_for_same_warehouse(self):
        with self.assertRaises(ValidationError):
            execute_stock_transfer(
                self.product, self.main_store, self.main_store, Decimal('1'), self.user,
            )
