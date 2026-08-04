import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from accounting.models import Account, AccountingPeriod
from accounting.services import account_balance
from inventory.models import Product, ProductCategory, StockMovement, Warehouse
from .models import Payment, Sale, SaleLine
from .services import complete_sale


class CompleteSaleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('cashier', password='pass')
        today = datetime.date.today()
        AccountingPeriod.objects.create(
            name='Test-Period', start_date=today.replace(day=1), end_date=today.replace(day=28),
        )
        for code, name, atype in [
            ('1000', 'Cash', 'ASSET'), ('1200', 'Inventory', 'ASSET'),
            ('4000', 'Sales Revenue', 'REVENUE'), ('5000', 'Cost of Goods Sold', 'EXPENSE'),
        ]:
            Account.objects.get_or_create(code=code, defaults={'name': name, 'account_type': atype})

        self.category = ProductCategory.objects.create(name='Groceries')
        self.product = Product.objects.create(
            sku='SG-2KG', name='Sugar 2kg', category=self.category,
            cost_price=Decimal('240'), selling_price=Decimal('320'),
        )
        self.storefront = Warehouse.objects.create(name='Main Store', is_retail_storefront=True)
        StockMovement.objects.create(
            product=self.product, warehouse=self.storefront, movement_type='PURCHASE',
            quantity=Decimal('10'), unit_cost=Decimal('240'),
            reference_document='OPENING', created_by=self.user,
        )
        self.sale = Sale.objects.create(
            receipt_number='SALE-00001', warehouse=self.storefront,
            status='DRAFT', cashier=self.user,
        )
        SaleLine.objects.create(sale=self.sale, product=self.product, quantity=Decimal('2'), unit_price=Decimal('320'))
        Payment.objects.create(sale=self.sale, amount=Decimal('640'), method='CASH')

    def test_complete_sale_deducts_stock_and_posts_ledger(self):
        complete_sale(self.sale.id, self.user)
        self.sale.refresh_from_db()
        self.assertEqual(self.sale.status, 'PAID')
        self.assertEqual(self.product.get_stock_in_warehouse(self.storefront), Decimal('8'))

        cash = Account.objects.get(code='1000')
        revenue = Account.objects.get(code='4000')
        cogs = Account.objects.get(code='5000')
        inventory = Account.objects.get(code='1200')

        self.assertEqual(account_balance(cash), Decimal('640.00'))
        self.assertEqual(account_balance(revenue), Decimal('640.00'))
        self.assertEqual(account_balance(cogs), Decimal('480.00'))  # 2 x 240 moving-average cost
        self.assertEqual(account_balance(inventory), Decimal('-480.00'))

    def test_complete_sale_fails_when_not_enough_stock(self):
        self.sale.lines.all().update(quantity=Decimal('999'))
        with self.assertRaises(ValidationError):
            complete_sale(self.sale.id, self.user)

    def test_complete_sale_fails_outside_retail_storefront(self):
        warehouse = Warehouse.objects.create(name='Warehouse (non-retail)')
        self.sale.warehouse = warehouse
        self.sale.save()
        with self.assertRaises(ValidationError):
            complete_sale(self.sale.id, self.user)
