# purchasing/views.py
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404

from core.access import manager_required
from .models import Supplier, PurchaseOrder, PurchaseLine
from .services import receive_purchase_order
from inventory.models import Product, Warehouse


@manager_required
def supplier_list(request):
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        if name:
            Supplier.objects.create(
                name=name,
                phone=request.POST.get('phone', ''),
                email=request.POST.get('email') or None,
            )
            messages.success(request, f"Supplier '{name}' added.")
        return redirect('supplier_list')
    return render(request, 'purchasing/supplier_list.html', {
        'suppliers': Supplier.objects.all().order_by('name'),
        'active': 'suppliers',
    })


@manager_required
def po_list(request):
    pos = (
        PurchaseOrder.objects.select_related('supplier', 'warehouse')
        .prefetch_related('lines')
        .order_by('-id')
    )
    data = []
    for po in pos:
        total = sum((l.get_total() for l in po.lines.all()), Decimal('0.00'))
        data.append({'po': po, 'total': total, 'count': po.lines.count()})
    return render(request, 'purchasing/po_list.html', {'rows': data, 'active': 'purchasing'})


@manager_required
def po_create(request):
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        warehouse_id = request.POST.get('warehouse')
        product_ids = request.POST.getlist('product')
        quantities = request.POST.getlist('quantity')
        costs = request.POST.getlist('unit_cost')

        if not supplier_id or not warehouse_id:
            messages.error(request, "Supplier and warehouse are required.")
            return redirect('po_create')

        with transaction.atomic():
            po = PurchaseOrder.objects.create(
                supplier_id=supplier_id,
                warehouse_id=warehouse_id,
                status='DRAFT',
                created_by=request.user,
            )
            added = 0
            for pid, qty, cost in zip(product_ids, quantities, costs):
                if not pid or not qty:
                    continue
                quantity = Decimal(qty)
                unit_cost = Decimal(cost or '0')
                if quantity <= 0 or unit_cost <= 0:
                    raise ValueError("Purchase quantities and unit costs must be greater than zero.")
                PurchaseLine.objects.create(
                    purchase_order=po,
                    product_id=pid,
                    quantity=quantity,
                    unit_cost=unit_cost,
                )
                added += 1
            if added == 0:
                po.delete()
                messages.error(request, "Add at least one product line.")
                return redirect('po_create')
        messages.success(request, f"Purchase Order {po.po_number} created as DRAFT. Receive it to add stock.")
        return redirect('po_list')

    return render(request, 'purchasing/po_form.html', {
        'suppliers': Supplier.objects.filter(is_active=True).order_by('name'),
        'warehouses': Warehouse.objects.filter(is_active=True).order_by('name'),
        'products': Product.objects.filter(is_active=True).order_by('name'),
        'active': 'purchasing',
    })


@manager_required
def po_receive(request, po_id):
    po = get_object_or_404(PurchaseOrder, id=po_id)
    method = request.POST.get('payment_method', 'CASH') if request.method == 'POST' else 'CASH'
    try:
        receive_purchase_order(po.id, request.user, payment_method=method)
        messages.success(request, f"{po.po_number} received. Stock added and books updated.")
    except Exception as e:
        messages.error(request, f"Could not receive {po.po_number}: {e}")
    return redirect('po_list')
