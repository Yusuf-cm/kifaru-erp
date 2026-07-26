# accounting/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum

from .models import Account, JournalEntry, JournalLine
from . import services


@login_required
def chart_of_accounts(request):
    accounts = Account.objects.all().order_by('code')
    rows = [{'account': a, 'balance': services.account_balance(a)} for a in accounts]
    return render(request, 'accounting/chart_of_accounts.html',
                  {'rows': rows, 'active': 'coa'})


@login_required
def trial_balance(request):
    return render(request, 'accounting/trial_balance.html',
                  {'tb': services.trial_balance(), 'active': 'trial'})


@login_required
def profit_loss(request):
    return render(request, 'accounting/profit_loss.html',
                  {'pnl': services.income_statement(), 'active': 'pnl'})


@login_required
def balance_sheet(request):
    return render(request, 'accounting/balance_sheet.html',
                  {'bs': services.balance_sheet(), 'active': 'balance'})


@login_required
def journal_list(request):
    entries = (JournalEntry.objects.all()
               .prefetch_related('lines__account')
               .order_by('-date', '-id')[:200])
    return render(request, 'accounting/journal_list.html',
                  {'entries': entries, 'active': 'journals'})


@login_required
def general_ledger(request, account_id):
    account = get_object_or_404(Account, id=account_id)
    lines = (JournalLine.objects.filter(account=account, journal_entry__status='POSTED')
             .select_related('journal_entry').order_by('journal_entry__date', 'id'))
    running = 0
    ledger = []
    debit_nature = account.account_type in services.DEBIT_NATURE
    for l in lines:
        delta = (l.debit - l.credit) if debit_nature else (l.credit - l.debit)
        running += delta
        ledger.append({'line': l, 'balance': running})
    return render(request, 'accounting/general_ledger.html',
                  {'account': account, 'ledger': ledger,
                   'balance': services.account_balance(account), 'active': 'coa'})
