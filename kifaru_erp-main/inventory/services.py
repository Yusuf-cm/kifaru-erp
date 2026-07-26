# inventory/services.py
from django.db import transaction
from django.core.exceptions import ValidationError
from inventory.models import StockMovement

@transaction.atomic
def execute_stock_transfer(product, source_warehouse, destination_warehouse, quantity, user, reference=""):
    """
    Safely moves stock between two locations. 
    It creates the double-entry inventory records simultaneously.
    If one fails, both fail. No ghost inventory.
    """
    if quantity <= 0:
        raise ValidationError("Transfer quantity must be greater than zero.")
        
    if source_warehouse == destination_warehouse:
        raise ValidationError("Source and destination warehouses cannot be the same.")

    # 1. Check if source has enough stock!
    current_source_stock = product.get_stock_in_warehouse(source_warehouse)
    if current_source_stock < quantity:
        raise ValidationError(f"Not enough stock in {source_warehouse.name}. You only have {current_source_stock}.")

    # 2. Create the OUT movement (Negative)
    StockMovement.objects.create(
        product=product,
        warehouse=source_warehouse,
        movement_type='TRANSFER',
        quantity=-quantity,  # Deduct from source
        unit_cost=0, # In a full system, you'd fetch the moving average cost here
        reference_document=reference,
        notes=f"Transferred OUT to {destination_warehouse.name}",
        created_by=user
    )

    # 3. Create the IN movement (Positive)
    StockMovement.objects.create(
        product=product,
        warehouse=destination_warehouse,
        movement_type='TRANSFER',
        quantity=quantity,   # Add to destination
        unit_cost=0, 
        reference_document=reference,
        notes=f"Transferred IN from {source_warehouse.name}",
        created_by=user
    )

    return True