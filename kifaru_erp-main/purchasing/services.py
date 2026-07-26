# purchasing/services.py
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from purchasing.models import PurchaseOrder
from inventory.models import StockMovement
from accounting.services import post_journal, get_open_period

ZERO = Decimal('0.00')


@transaction.atomic
def receive_purchase_order(po_id, user, payment_method='CASH'):
    """
    Receive a PO:
      1. Add each line's quantity into the warehouse at its unit cost (stock ledger).
      2. Post GL: Dr Inventory (1200), Cr the funding account.
         CASH->1000, MPESA->1010, BANK->1020, CREDIT->2000 (Accounts Payable).
    """
    po = PurchaseOrder.objects.select_for_update().get(id=po_id)

    if po.status != 'DRAFT':
        raise ValidationError("Only draft purchase orders can be received.")
    if not po.lines.exists():
        raise ValidationError("Cannot receive a Purchase Order with no lines.")

    today = timezone.now().date()
    period = get_open_period(today)

    total_cost = ZERO
    for line in po.lines.all():
        StockMovement.objects.create(
            product=line.product,
            warehouse=po.warehouse,
            movement_type='PURCHASE',
            quantity=line.quantity,               # positive = stock in
            unit_cost=line.unit_cost,
            reference_document=po.po_number,
            notes=f"Received from {po.supplier.name} via {po.po_number}",
            created_by=user,
        )
        total_cost += line.unit_cost * line.quantity

    if total_cost > 0:
        funding_code = {'CASH': '1000', 'MPESA': '1010', 'BANK': '1020',
                        'CREDIT': '2000'}.get(payment_method, '1000')
        post_journal(
            date=today,
            reference=f"PO: {po.po_number}",
            description=f"Stock purchase from {po.supplier.name} ({payment_method})",
            lines=[
                ('1200', total_cost, 0),        # Dr Inventory asset
                (funding_code, 0, total_cost),  # Cr cash / payable
            ],
            user=user, period=period,
        )

    po.status = 'RECEIVED'
    po.save()
    return po
