# sales/services.py
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from sales.models import Sale
from inventory.models import StockMovement
from accounting.services import post_journal, get_open_period

ZERO = Decimal('0.00')


@transaction.atomic
def complete_sale(sale_id, user):
    """
    Full ERP sale engine:
      1. Lock the sale row.
      2. Verify stock exists at the storefront.
      3. Deduct inventory at moving-average cost (real COGS).
      4. Post revenue journal (Dr Cash/M-Pesa/Bank, Cr Sales Revenue).
      5. Post COGS journal (Dr COGS, Cr Inventory).
    """
    sale = Sale.objects.select_for_update().get(id=sale_id)

    if sale.status != 'DRAFT':
        raise ValidationError("Only draft sales can be completed.")
    if not sale.warehouse.is_retail_storefront:
        raise ValidationError("You can only sell directly from a Retail Storefront.")

    # 1. Pre-flight stock check
    for line in sale.lines.all():
        available = line.product.get_stock_in_warehouse(sale.warehouse)
        if available < line.quantity:
            raise ValidationError(
                f"Not enough stock for {line.product.name} at {sale.warehouse.name}. "
                f"Available: {available}, needed: {line.quantity}."
            )

    period = get_open_period(timezone.now().date())
    today = timezone.now().date()

    # 2. Deduct inventory at moving-average cost + accumulate COGS
    total_cogs = ZERO
    for line in sale.lines.all():
        unit_cost = line.product.get_moving_average_cost()
        total_cogs += unit_cost * line.quantity
        StockMovement.objects.create(
            product=line.product,
            warehouse=sale.warehouse,
            movement_type='SALE',
            quantity=-line.quantity,
            unit_cost=unit_cost,
            reference_document=sale.receipt_number,
            notes=f"Sold on Receipt {sale.receipt_number}",
            created_by=user,
        )

    # 3. Revenue journal — route asset account by payment method
    payment = sale.payments.first()
    method = payment.method if payment else 'CASH'
    asset_code = {'MPESA': '1010', 'BANK': '1020'}.get(method, '1000')
    total_amount = sum((l.get_total() for l in sale.lines.all()), ZERO)

    if total_amount > 0:
        post_journal(
            date=today,
            reference=f"Receipt: {sale.receipt_number}",
            description=f"Sales revenue ({method})",
            lines=[
                (asset_code, total_amount, 0),   # Dr asset
                ('4000', 0, total_amount),        # Cr revenue
            ],
            user=user, period=period,
        )

    # 4. COGS journal — only when we actually know the cost
    if total_cogs > 0:
        post_journal(
            date=today,
            reference=f"COGS: {sale.receipt_number}",
            description=f"Cost of goods sold for {sale.receipt_number}",
            lines=[
                ('5000', total_cogs, 0),   # Dr COGS
                ('1200', 0, total_cogs),   # Cr Inventory asset
            ],
            user=user, period=period,
        )

    sale.status = 'PAID'
    sale.save()
    return sale
