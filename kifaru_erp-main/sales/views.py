# sales/views.py
import json
from decimal import Decimal

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render

from core.access import pos_required
from core.models import DocumentSequence
from inventory.models import Product, Warehouse, ProductCategory
from .models import Sale, SaleLine, Payment
from .services import complete_sale


@pos_required
def pos_dashboard(request):
    storefront = Warehouse.objects.filter(is_retail_storefront=True).first()
    products = Product.objects.filter(is_active=True)
    categories = ProductCategory.objects.all()

    for product in products:
        if storefront:
            product.storefront_stock = product.get_stock_in_warehouse(storefront)
        else:
            product.storefront_stock = Decimal('0.00')

    return render(request, 'sales/pos.html', {
        'storefront': storefront,
        'products': products,
        'categories': categories,
    })


@pos_required
def api_checkout(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cart_items = data.get('items', [])
            payment_method = data.get('payment_method', 'CASH')
            if payment_method not in {'CASH', 'MPESA', 'BANK'}:
                return JsonResponse({'status': 'error', 'message': 'Unsupported payment method'}, status=400)

            reference = data.get('reference', '')
            if not cart_items:
                return JsonResponse({'status': 'error', 'message': 'Cart is empty'}, status=400)

            storefront = Warehouse.objects.filter(is_retail_storefront=True).first()
            if not storefront:
                return JsonResponse(
                    {'status': 'error', 'message': 'Retail storefront is not configured.'},
                    status=400,
                )

            warehouse_id = str(data.get('warehouse_id') or '')
            if warehouse_id != str(storefront.id):
                return JsonResponse(
                    {'status': 'error', 'message': 'Sales must use the configured retail storefront.'},
                    status=400,
                )

            with transaction.atomic():
                receipt_no = DocumentSequence.get_next_number('SALE')
                sale = Sale.objects.create(
                    receipt_number=receipt_no,
                    warehouse=storefront,
                    status='DRAFT',
                    cashier=request.user,
                )

                total_amount = Decimal('0.00')
                for item in cart_items:
                    product = Product.objects.get(id=item['product_id'])
                    qty = Decimal(str(item['quantity']))
                    if qty <= 0:
                        raise ValueError(f"Quantity for {product.name} must be greater than zero.")

                    price = product.selling_price
                    if price <= 0:
                        raise ValueError(f"Selling price for {product.name} is not configured.")

                    SaleLine.objects.create(
                        sale=sale,
                        product=product,
                        quantity=qty,
                        unit_price=price,
                    )
                    total_amount += qty * price

                Payment.objects.create(
                    sale=sale,
                    amount=total_amount,
                    method=payment_method,
                    reference_code=reference,
                )
                complete_sale(sale.id, request.user)

            return JsonResponse({
                'status': 'success',
                'message': f'Sale {receipt_no} completed successfully!',
                'receipt_number': receipt_no,
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)
