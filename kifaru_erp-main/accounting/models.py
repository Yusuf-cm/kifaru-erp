# accounting/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.db import transaction
from decimal import Decimal

class Account(models.Model):
    ACCOUNT_TYPES = [
        ('ASSET', 'Asset'),
        ('LIABILITY', 'Liability'),
        ('EQUITY', 'Equity'),
        ('REVENUE', 'Revenue'),
        ('EXPENSE', 'Expense'),
    ]
    code = models.CharField(max_length=20, unique=True, help_text="e.g., 1000 for Cash, 4000 for Sales")
    name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=15, choices=ACCOUNT_TYPES)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.name} ({self.account_type})"

class AccountingPeriod(models.Model):
    name = models.CharField(max_length=20, unique=True, help_text="e.g., Oct-2024")
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)

    def __str__(self):
        status = "CLOSED" if self.is_closed else "OPEN"
        return f"{self.name} [{status}]"

class JournalEntry(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('POSTED', 'Posted'),
        ('REVERSED', 'Reversed'),
    ]
    date = models.DateField()
    reference = models.CharField(max_length=255, help_text="e.g., Receipt No, Invoice No")
    description = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    period = models.ForeignKey(AccountingPeriod, on_delete=models.PROTECT)
    
    created_at = models.DateTimeField(auto_now_add=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, on_delete=models.PROTECT, related_name='journals_created')

    class Meta:
        verbose_name_plural = "Journal Entries"

    def __str__(self):
        return f"JE-{self.id} | {self.date} | {self.status}"

    @transaction.atomic
    def post(self, user):
        """
        Locks the period, enforces double-entry rules, and posts the journal atomically.
        """
        if self.status != 'DRAFT':
            raise ValidationError("Only DRAFT journals can be posted.")
        
        if self.period.is_closed:
            raise ValidationError(f"Cannot post to a closed period: {self.period.name}")

        total_debits = sum(line.debit for line in self.lines.all())
        total_credits = sum(line.credit for line in self.lines.all())

        if total_debits != total_credits:
            raise ValidationError(f"Debits ({total_debits}) must equal Credits ({total_credits}).")
        
        if total_debits == 0:
            raise ValidationError("Journal entry must have a non-zero value.")

        from django.utils import timezone
        self.status = 'POSTED'
        self.posted_at = timezone.now()
        self.save()

class JournalLine(models.Model):
    journal_entry = models.ForeignKey(JournalEntry, related_name='lines', on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"{self.account.name} | Dr: {self.debit} | Cr: {self.credit}"
    
    def clean(self):
        if self.debit > 0 and self.credit > 0:
            raise ValidationError("A single line cannot have both a debit and a credit.")
        if self.debit == 0 and self.credit == 0:
            raise ValidationError("Line must have either a debit or credit amount.")