# core/models.py
from django.db import models
from django.db import transaction

class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True, help_text="e.g., KES, USD, EUR")
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=5)
    is_base_currency = models.BooleanField(default=False, help_text="Only ONE currency can be the base.")
    
    class Meta:
        verbose_name_plural = "Currencies"

    def __str__(self):
        return f"{self.code} - {self.name}"

class DocumentSequence(models.Model):
    """
    Guarantees gapless numbering for financial and legal documents.
    e.g., prefix='INV-2024-', current_number=5 -> Next is 'INV-2024-6'
    """
    document_type = models.CharField(max_length=50, unique=True, help_text="e.g., SALE, PO, RECEIPT, JOURNAL")
    prefix = models.CharField(max_length=20)
    current_number = models.BigIntegerField(default=0)

    @classmethod
    def get_next_number(cls, doc_type):
        """
        Self-healing sequence generator.
        Wrapped entirely in an atomic transaction to prevent race conditions.
        """
        with transaction.atomic():
            # 1. Ensure the rule exists
            sequence, created = cls.objects.get_or_create(
                document_type=doc_type,
                defaults={'prefix': f'{doc_type}-', 'current_number': 0}
            )
            
            # 2. Lock the exact row so no other process can grab the same number
            sequence = cls.objects.select_for_update().get(id=sequence.id)
            
            # 3. Increment the number
            sequence.current_number += 1
            sequence.save()
            
            # Formats to something like: SALE-00001
            return f"{sequence.prefix}{sequence.current_number:05d}"

    def __str__(self):
        return f"{self.document_type} Sequence ({self.prefix})"