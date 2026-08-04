import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from accounting.models import Account, AccountingPeriod
from accounting.services import account_balance
from inventory.models import Product, ProductCategory, Warehouse
from .models import PurchaseLine, PurchaseOrder, Supplier
from .services import receive_purchase_order


class ReceivePurchaseOrderTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('buyer', password='pass')
        today = datetime.date.today()
        AccountingPeriod.objects.create(
            name='Test-Period', start_date=today.replace(day=1), end_date=today.replace(day=28),
        )
        for code, name, atype in [
            ('1000', 'Cash', 'ASSET'), ('1200', 'Inventory', 'ASSET'),
            ('2000', 'Accounts Payable', 'LIABILITY'),
        ]:
            Account.objects.get_or_create(code=code, defaults={'name': name, 'account_type': atype})

        self.supplier = Supplier.objects.create(name='Test Supplier')
        self.warehouse = Warehouse.objects.create(name='Main Store')
        self.category = ProductCategory.objects.create(name='Groceries')
        self.product = Product.objects.create(
            sku='SG-2KG', name='Sugar 2kg', category=self.category,
            cost_price=Decimal('240'), selling_price=Decimal('320'),
        )
        self.po = PurchaseOrder.objects.create(
            supplier=self.supplier, warehouse=self.warehouse, created_by=self.user,
        )
        PurchaseLine.objects.create(
            purchase_order=self.po, product=self.product,
            quantity=Decimal('10'), unit_cost=Decimal('240'),
        )

    def test_po_number_is_auto_generated(self):
        self.assertTrue(self.po.po_number.startswith('PO-'))

    def test_receive_adds_stock_and_posts_ledger(self):
        receive_purchase_order(self.po.id, self.user, payment_method='CREDIT')
        self.po.refresh_from_db()
        self.assertEqual(self.po.status, 'RECEIVED')
        self.assertEqual(self.product.get_stock_in_warehouse(self.warehouse), Decimal('10'))

        inventory = Account.objects.get(code='1200')
        payable = Account.objects.get(code='2000')
        self.assertEqual(account_balance(inventory), Decimal('2400.00'))
        self.assertEqual(account_balance(payable), Decimal('2400.00'))

    def test_cannot_receive_a_po_twice(self):
        receive_purchase_order(self.po.id, self.user)
        with self.assertRaises(ValidationError):
            receive_purchase_order(self.po.id, self.user)

    def test_cannot_receive_po_without_lines(self):
        empty_po = PurchaseOrder.objects.create(
            supplier=self.supplier, warehouse=self.warehouse, created_by=self.user,
        )
        with self.assertRaises(ValidationError):
            receive_purchase_order(empty_po.id, self.user)
