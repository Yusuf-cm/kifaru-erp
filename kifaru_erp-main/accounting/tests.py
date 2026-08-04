import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Account, AccountingPeriod
from .services import account_balance, get_open_period, post_journal, trial_balance


class JournalPostingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('bookkeeper', password='pass')
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET')
        self.revenue = Account.objects.create(code='4000', name='Sales Revenue', account_type='REVENUE')
        today = datetime.date.today()
        self.period = AccountingPeriod.objects.create(
            name='Test-Period', start_date=today.replace(day=1),
            end_date=today.replace(day=28),
        )

    def test_get_open_period_raises_when_none_open(self):
        self.period.is_closed = True
        self.period.save()
        with self.assertRaises(ValidationError):
            get_open_period(datetime.date.today())

    def test_post_journal_keeps_books_balanced(self):
        post_journal(
            date=datetime.date.today(), reference='TEST-1', description='Cash sale',
            lines=[('1000', 100, 0), ('4000', 0, 100)],
            user=self.user, period=self.period,
        )
        self.assertEqual(account_balance(self.cash), Decimal('100.00'))
        self.assertEqual(account_balance(self.revenue), Decimal('100.00'))
        tb = trial_balance()
        self.assertEqual(tb['total_debit'], tb['total_credit'])

    def test_post_journal_rejects_closed_period(self):
        self.period.is_closed = True
        self.period.save()
        with self.assertRaises(ValidationError):
            post_journal(
                date=datetime.date.today(), reference='TEST-2', description='Should fail',
                lines=[('1000', 50, 0), ('4000', 0, 50)],
                user=self.user, period=self.period,
            )
