# core/views.py
import json
from datetime import timedelta
from decimal import Decimal
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone

from accounting.models import Account, JournalLine
from accounting import services as acc
from sales.models import Sale
from inventory.models import Product


@login_required(login_url='/admin/login/')
def admin_dashboard(request):
    today = timezone.now().date()

    # Real figures straight from the general ledger
    pnl = acc.income_statement()

    def bal(code):
        a = Account.objects.filter(code=code).first()
        return acc.account_balance(a) if a else Decimal('0.00')

    cash_balance = bal('1000')
    mpesa_balance = bal('1010')
    bank_balance = bal('1020')
    inventory_value = bal('1200')

    # Real 7-day revenue from posted revenue journal lines (account 4000)
    rev_acc = Account.objects.filter(code='4000').first()
    chart_labels, chart_data = [], []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        chart_labels.append(day.strftime('%a'))
        amount = Decimal('0.00')
        if rev_acc:
            agg = (JournalLine.objects
                   .filter(account=rev_acc, journal_entry__status='POSTED',
                           journal_entry__date=day)
                   .aggregate(c=Sum('credit'), d=Sum('debit')))
            amount = (agg['c'] or Decimal('0.00')) - (agg['d'] or Decimal('0.00'))
        chart_data.append(float(amount))

    sales_today = Sale.objects.filter(created_at__date=today, status='PAID').count()
    recent_sales = Sale.objects.filter(status='PAID').select_related(
        'warehouse', 'cashier').order_by('-created_at')[:7]

    # Low-stock alerts
    low_stock = []
    for p in Product.objects.filter(is_active=True):
        total = p.get_total_stock()
        if total <= (p.reorder_level or 0):
            low_stock.append({'product': p, 'stock': total})
    low_stock = low_stock[:6]

    context = {
        'active': 'dashboard',
        'revenue': pnl['revenue'],
        'gross_profit': pnl['gross_profit'],
        'net_profit': pnl['net_profit'],
        'cogs': pnl['cogs'],
        'expenses': pnl['expenses'],
        'cash_balance': cash_balance,
        'mpesa_balance': mpesa_balance,
        'bank_balance': bank_balance,
        'inventory_value': inventory_value,
        'sales_today': sales_today,
        'recent_sales': recent_sales,
        'low_stock': low_stock,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
    }
    return render(request, 'core/dashboard.html', context)
