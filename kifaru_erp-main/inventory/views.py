# inventory/views.py
import json
from decimal import Decimal
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Product, Warehouse, ProductCategory, StockMovement
from .services import execute_stock_transfer


@login_required(login_url='/admin/login/')
def inventory_dashboard(request):
    products = Product.objects.filter(is_active=True).select_related('category').order_by('name')
    warehouses = Warehouse.objects.filter(is_active=True)
    rows = []
    for p in products:
        total = p.get_total_stock()
        rows.append({
            'product': p, 'stock': total,
            'low': total <= (p.reorder_level or 0),
            'value': total * p.get_moving_average_cost(),
        })
    total_value = sum((r['value'] for r in rows), Decimal('0.00'))
    return render(request, 'inventory/dashboard.html', {
        'rows': rows, 'products': products, 'warehouses': warehouses,
        'categories': ProductCategory.objects.all().order_by('name'),
        'total_value': total_value, 'active': 'inventory',
    })


@login_required
def product_create(request):
    if request.method != 'POST':
        return redirect('inventory_dashboard')
    try:
        cat_name = (request.POST.get('category') or 'General').strip()
        category, _ = ProductCategory.objects.get_or_create(name=cat_name)
        Product.objects.create(
            sku=request.POST['sku'].strip(),
            name=request.POST['name'].strip(),
            category=category,
            unit_of_measure=request.POST.get('unit_of_measure', 'PCS'),
            cost_price=Decimal(request.POST.get('cost_price') or '0'),
            selling_price=Decimal(request.POST.get('selling_price') or '0'),
            reorder_level=Decimal(request.POST.get('reorder_level') or '0'),
        )
        messages.success(request, f"Product '{request.POST['name']}' added.")
    except Exception as e:
        messages.error(request, f"Could not add product: {e}")
    return redirect('inventory_dashboard')


@login_required
def stock_adjust(request):
    """Opening stock / manual count adjustment — writes a StockMovement."""
    if request.method != 'POST':
        return redirect('inventory_dashboard')
    try:
        product = Product.objects.get(id=request.POST['product'])
        warehouse = Warehouse.objects.get(id=request.POST['warehouse'])
        qty = Decimal(request.POST['quantity'])
        StockMovement.objects.create(
            product=product, warehouse=warehouse, movement_type='ADJUSTMENT',
            quantity=qty, unit_cost=product.get_moving_average_cost() or product.cost_price,
            reference_document='OPENING/ADJUST', notes='Manual stock adjustment',
            created_by=request.user,
        )
        messages.success(request, f"Adjusted {product.name} by {qty} at {warehouse.name}.")
    except Exception as e:
        messages.error(request, f"Adjustment failed: {e}")
    return redirect('inventory_dashboard')


@login_required
def api_transfer_stock(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            execute_stock_transfer(
                product=Product.objects.get(id=data.get('product_id')),
                source_warehouse=Warehouse.objects.get(id=data.get('source_id')),
                destination_warehouse=Warehouse.objects.get(id=data.get('dest_id')),
                quantity=Decimal(str(data.get('quantity', 0))),
                user=request.user, reference="Manual Transfer (UI)",
            )
            return JsonResponse({'status': 'success', 'message': 'Stock transferred.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)
