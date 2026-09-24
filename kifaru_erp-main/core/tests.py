from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .access import can_use_pos, is_manager
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


class RoleAccessTests(TestCase):
    def setUp(self):
        self.manager_group, _ = Group.objects.get_or_create(name='Manager')
        self.cashier_group, _ = Group.objects.get_or_create(name='Cashier')

        self.manager = User.objects.create_user('manager', password='test-pass')
        self.manager.groups.add(self.manager_group)

        self.cashier = User.objects.create_user('cashier', password='test-pass')
        self.cashier.groups.add(self.cashier_group)

        self.unassigned = User.objects.create_user('unassigned', password='test-pass')

    def test_role_helpers(self):
        self.assertTrue(is_manager(self.manager))
        self.assertFalse(is_manager(self.cashier))
        self.assertTrue(can_use_pos(self.manager))
        self.assertTrue(can_use_pos(self.cashier))
        self.assertFalse(can_use_pos(self.unassigned))

    def test_cashier_is_sent_to_pos_from_home(self):
        self.client.force_login(self.cashier)
        response = self.client.get(reverse('home'))
        self.assertRedirects(response, reverse('pos_dashboard'))

    def test_cashier_cannot_open_manager_dashboard(self):
        self.client.force_login(self.cashier)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_unassigned_user_cannot_open_pos(self):
        self.client.force_login(self.unassigned)
        response = self.client.get(reverse('pos_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_to_app_login(self):
        response = self.client.get(reverse('pos_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
