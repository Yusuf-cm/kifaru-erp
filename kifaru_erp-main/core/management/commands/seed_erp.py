# core/management/commands/seed_erp.py
"""
Idempotent bootstrap for Kifaru ERP. Safe to run repeatedly.
Creates the chart of accounts, an open accounting period, a base currency,
a retail storefront warehouse, and (optionally) demo products so the POS,
purchasing and accounting screens work out of the box.

    python manage.py seed_erp            # accounts + period + storefront
    python manage.py seed_erp --demo     # also add demo products/supplier
"""
import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Currency
from accounting.models import Account, AccountingPeriod
from inventory.models import ProductCategory, Product, Warehouse
from purchasing.models import Supplier

CHART_OF_ACCOUNTS = [
    ('1000', 'Main Till (Cash)', 'ASSET'),
    ('1010', 'M-Pesa Float', 'ASSET'),
    ('1020', 'Bank Account', 'ASSET'),
    ('1200', 'Inventory', 'ASSET'),
    ('1300', 'Accounts Receivable', 'ASSET'),
    ('2000', 'Accounts Payable', 'LIABILITY'),
    ('2100', 'Loans Payable', 'LIABILITY'),
    ('2200', 'Tax Payable (KRA)', 'LIABILITY'),
    ('3000', "Owner's Equity", 'EQUITY'),
    ('4000', 'Sales Revenue', 'REVENUE'),
    ('4100', 'Other Income', 'REVENUE'),
    ('5000', 'Cost of Goods Sold', 'EXPENSE'),
    ('6000', 'Rent', 'EXPENSE'),
    ('6010', 'Wages & Salaries', 'EXPENSE'),
    ('6020', 'Transport', 'EXPENSE'),
    ('6030', 'Utilities (Power/Water)', 'EXPENSE'),
    ('6040', 'Airtime & Data', 'EXPENSE'),
    ('6050', 'M-Pesa & Bank Charges', 'EXPENSE'),
    ('6900', 'Other Expenses', 'EXPENSE'),
]

DEMO_PRODUCTS = [
    # (sku, name, category, cost, price)
    ('SG-2KG', 'Sugar 2kg', 'Groceries', 240, 320),
    ('MZ-1KG', 'Maize Flour 1kg', 'Groceries', 120, 165),
    ('CK-500', 'Cooking Oil 500ml', 'Groceries', 130, 180),
    ('BR-400', 'Bread 400g', 'Bakery', 55, 75),
    ('ML-500', 'Milk 500ml', 'Dairy', 50, 65),
    ('SP-200', 'Soap Bar 200g', 'Household', 45, 70),
    ('SD-500', 'Soda 500ml', 'Drinks', 45, 70),
    ('WT-1L', 'Water 1L', 'Drinks', 25, 50),
]


class Command(BaseCommand):
    help = "Seed Kifaru ERP with a chart of accounts, open period, storefront and optional demo data."

    def add_arguments(self, parser):
        parser.add_argument('--demo', action='store_true', help='Also create demo products and a supplier.')

    @transaction.atomic
    def handle(self, *args, **opts):
        # Currency
        Currency.objects.get_or_create(
            code='KES', defaults={'name': 'Kenyan Shilling', 'symbol': 'KES', 'is_base_currency': True})

        # Chart of accounts
        created_accounts = 0
        for code, name, atype in CHART_OF_ACCOUNTS:
            _, made = Account.objects.get_or_create(
                code=code, defaults={'name': name, 'account_type': atype})
            created_accounts += int(made)
        self.stdout.write(self.style.SUCCESS(f"Chart of accounts ready ({created_accounts} new)."))

        # Open accounting period for the current month
        today = datetime.date.today()
        start = today.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1, day=1) - datetime.timedelta(days=1)
        else:
            end = start.replace(month=start.month + 1, day=1) - datetime.timedelta(days=1)
        period_name = start.strftime('%b-%Y')
        AccountingPeriod.objects.get_or_create(
            name=period_name,
            defaults={'start_date': start, 'end_date': end, 'is_closed': False})
        self.stdout.write(self.style.SUCCESS(f"Open accounting period: {period_name}."))

        # Retail storefront warehouse
        Warehouse.objects.get_or_create(
            name='Main Store',
            defaults={'location': 'Nairobi', 'is_retail_storefront': True, 'is_active': True})
        self.stdout.write(self.style.SUCCESS("Storefront 'Main Store' ready."))

        if opts['demo']:
            self._seed_demo()

        self.stdout.write(self.style.SUCCESS("\nKifaru ERP seeded. Login and go."))

    def _seed_demo(self):
        Supplier.objects.get_or_create(
            name='Mombasa Distributors Ltd',
            defaults={'phone': '0722000111', 'email': 'sales@mombasadist.co.ke'})
        cats = {}
        for _, _, cat, _, _ in DEMO_PRODUCTS:
            if cat not in cats:
                cats[cat], _ = ProductCategory.objects.get_or_create(name=cat)
        made = 0
        for sku, name, cat, cost, price in DEMO_PRODUCTS:
            _, created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    'name': name, 'category': cats[cat], 'unit_of_measure': 'PCS',
                    'cost_price': Decimal(cost), 'selling_price': Decimal(price),
                    'reorder_level': Decimal('5'),
                })
            made += int(created)
        self.stdout.write(self.style.SUCCESS(
            f"Demo data ready ({made} products). Tip: create & receive a PO to stock them."))
