from django.test import TestCase

from .models import DocumentSequence


class DocumentSequenceTests(TestCase):
    def test_get_next_number_is_gapless_and_formatted(self):
        first = DocumentSequence.get_next_number('SALE')
        second = DocumentSequence.get_next_number('SALE')
        self.assertEqual(first, 'SALE-00001')
        self.assertEqual(second, 'SALE-00002')

    def test_sequences_for_different_document_types_are_independent(self):
        sale_no = DocumentSequence.get_next_number('SALE')
        po_no = DocumentSequence.get_next_number('PO')
        self.assertEqual(sale_no, 'SALE-00001')
        self.assertEqual(po_no, 'PO-00001')
