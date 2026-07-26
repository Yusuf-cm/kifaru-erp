# accounting/services.py
"""
Central general-ledger helpers. Everything that touches the books goes through here
so double-entry stays honest and reports have a single source of truth.
"""
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import Account, AccountingPeriod, JournalEntry, JournalLine

ZERO = Decimal('0.00')

# Account types whose balance is naturally a DEBIT (assets, expenses)
DEBIT_NATURE = {'ASSET', 'EXPENSE'}
# Account types whose balance is naturally a CREDIT (liability, equity, revenue)
CREDIT_NATURE = {'LIABILITY', 'EQUITY', 'REVENUE'}


def get_open_period(for_date=None):
    """Return the open accounting period covering the date (defaults to today)."""
    d = for_date or timezone.now().date()
    period = AccountingPeriod.objects.filter(
        start_date__lte=d, end_date__gte=d, is_closed=False
    ).first()
    if not period:
        raise ValidationError(
            "No open accounting period for this date. Run 'python manage.py seed_erp' "
            "or open a period in the Admin."
        )
    return period


def get_account(code):
    try:
        return Account.objects.get(code=code)
    except Account.DoesNotExist:
        raise ValidationError(f"Account {code} is missing. Run 'python manage.py seed_erp'.")


@transaction.atomic
def post_journal(date, reference, description, lines, user, period=None):
    """
    Create and POST a balanced journal in one call.
    `lines` = list of (account_code, debit, credit) tuples.
    """
    period = period or get_open_period(date)
    entry = JournalEntry.objects.create(
        date=date, reference=reference, description=description,
        period=period, created_by=user,
    )
    for code, debit, credit in lines:
        JournalLine.objects.create(
            journal_entry=entry,
            account=get_account(code),
            debit=Decimal(str(debit or 0)),
            credit=Decimal(str(credit or 0)),
        )
    entry.post(user)
    return entry


# ── Reporting ────────────────────────────────────────────────────────────────

def _posted_lines():
    return JournalLine.objects.filter(journal_entry__status='POSTED')


def account_balance(account):
    """Signed natural balance: debit-nature => Dr-Cr, credit-nature => Cr-Dr."""
    agg = _posted_lines().filter(account=account).aggregate(
        d=Sum('debit'), c=Sum('credit'))
    debit = agg['d'] or ZERO
    credit = agg['c'] or ZERO
    if account.account_type in DEBIT_NATURE:
        return debit - credit
    return credit - debit


def trial_balance():
    """List of {account, debit, credit} plus totals — always balances if books are sane."""
    rows, total_d, total_c = [], ZERO, ZERO
    for acc in Account.objects.filter(is_active=True).order_by('code'):
        agg = _posted_lines().filter(account=acc).aggregate(d=Sum('debit'), c=Sum('credit'))
        debit = agg['d'] or ZERO
        credit = agg['c'] or ZERO
        net = debit - credit
        if net == 0 and debit == 0 and credit == 0:
            continue
        # Present each account on its natural side
        dr = net if net > 0 else ZERO
        cr = -net if net < 0 else ZERO
        rows.append({'account': acc, 'debit': dr, 'credit': cr})
        total_d += dr
        total_c += cr
    return {'rows': rows, 'total_debit': total_d, 'total_credit': total_c}


def _sum_by_type(acc_type):
    rows, total = [], ZERO
    for acc in Account.objects.filter(account_type=acc_type, is_active=True).order_by('code'):
        bal = account_balance(acc)
        if bal != 0:
            rows.append({'account': acc, 'amount': bal})
            total += bal
    return rows, total


def income_statement():
    revenue_rows, revenue = _sum_by_type('REVENUE')
    expense_rows, expenses = _sum_by_type('EXPENSE')
    # COGS (5xxx) is an expense; split it out for a gross-profit line if present
    cogs = ZERO
    cogs_rows = []
    other_expense_rows = []
    for r in expense_rows:
        if r['account'].code.startswith('5'):
            cogs += r['amount']
            cogs_rows.append(r)
        else:
            other_expense_rows.append(r)
    other_expenses = expenses - cogs
    gross_profit = revenue - cogs
    net_profit = gross_profit - other_expenses
    return {
        'revenue_rows': revenue_rows, 'revenue': revenue,
        'cogs_rows': cogs_rows, 'cogs': cogs, 'gross_profit': gross_profit,
        'expense_rows': other_expense_rows, 'expenses': other_expenses,
        'net_profit': net_profit,
    }


def balance_sheet():
    asset_rows, assets = _sum_by_type('ASSET')
    liab_rows, liabilities = _sum_by_type('LIABILITY')
    equity_rows, equity = _sum_by_type('EQUITY')
    # Retained earnings = net profit flows into equity
    net_profit = income_statement()['net_profit']
    equity_total = equity + net_profit
    return {
        'asset_rows': asset_rows, 'assets': assets,
        'liab_rows': liab_rows, 'liabilities': liabilities,
        'equity_rows': equity_rows, 'equity_base': equity,
        'retained_earnings': net_profit, 'equity_total': equity_total,
        'liabilities_and_equity': liabilities + equity_total,
        'balances': assets == (liabilities + equity_total),
    }
