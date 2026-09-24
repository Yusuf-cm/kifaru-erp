# sales/views.py
import json
from decimal import Decimal
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import Sale, SaleLine, Payment
from inventory.models import Product, Warehouse, ProductCategory
from core.models import DocumentSequence
from .services import complete_sale

@login_required(login_url='/admin/login/')
def pos_dashboard(request):
    """ Loads the POS Interface """
    storefront = Warehouse.objects.filter(is_retail_storefront=True).first()
    products = Product.objects.filter(is_active=True)
    categories = ProductCategory.objects.all()
    
    # Pre-calculate Storefront specific stock
    for product in products:
        if storefront:
            product.storefront_stock = product.get_stock_in_warehouse(storefront)
        else:
            product.storefront_stock = Decimal('0.00')

    context = {
        'storefront': storefront,
        'products': products,
        'categories': categories,
    }
    return render(request, 'sales/pos.html', context)

@login_required
def api_checkout(request):
    """ Receives the cart data and processes it """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cart_items = data.get('items', [])
            payment_method = data.get('payment_method', 'CASH')
            if payment_method not in {'CASH', 'MPESA', 'BANK'}:
                return JsonResponse({'status': 'error', 'message': 'Unsupported payment method'}, status=400)
            warehouse_id = data.get('warehouse_id')
            reference = data.get('reference', '') # Capture M-Pesa Ref
            
            if not cart_items:
                return JsonResponse({'status': 'error', 'message': 'Cart is empty'}, status=400)

            warehouse = Warehouse.objects.get(id=warehouse_id)

            with transaction.atomic():
                receipt_no = DocumentSequence.get_next_number('SALE')

                sale = Sale.objects.create(
                    receipt_number=receipt_no,
                    warehouse=warehouse,
                    status='DRAFT',
                    cashier=request.user
                )

                total_amount = Decimal('0.00')

                for item in cart_items:
                    product = Product.objects.get(id=item['product_id'])
                    # The browser may suggest a quantity, but it must never be
                    # allowed to set the authoritative selling price.
                    qty = Decimal(str(item['quantity']))
                    if qty <= 0:
                        raise ValueError(f"Quantity for {product.name} must be greater than zero.")

                    price = product.selling_price
                    if price <= 0:
                        raise ValueError(f"Selling price for {product.name} is not configured.")

                    SaleLine.objects.create(
                        sale=sale, product=product, quantity=qty, unit_price=price
                    )
                    total_amount += (qty * price)

                # Record Payment with Reference Code
                Payment.objects.create(
                    sale=sale, amount=total_amount, method=payment_method, reference_code=reference
                )

                complete_sale(sale.id, request.user)

            return JsonResponse({
                'status': 'success', 
                'message': f'Sale {receipt_no} completed successfully!',
                'receipt_number': receipt_no
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)