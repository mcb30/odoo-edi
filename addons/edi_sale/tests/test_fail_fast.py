"""Tests for Order Import hardening."""

from unittest import mock

from odoo import tools
from odoo.exceptions import ValidationError

from .common import EdiSaleCase


class TestFailFast(EdiSaleCase):
    """EDI sale fail fast tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.MailMessage = cls.env['mail.message']
        cls.sale_request_tutorial_record_type = cls.env.ref("edi_sale.sale_request_tutorial_record_type")
        cls.sale_line_request_tutorial_record_type = cls.env.ref("edi_sale.sale_line_request_tutorial_record_type")
        cls.doc_type_tutorial = cls.env.ref("edi_sale.sale_request_tutorial_document_type")
        cls.doc_type_tutorial.active = True
        cls.sale_request_tutorial_record_type.active = True
        cls.sale_line_request_tutorial_record_type.active = True

    @classmethod
    def create_tutorial(cls, *filenames, fail_fast=True):
        """Create sale order request tutorial document"""
        cls.doc_type_tutorial.fail_fast = fail_fast
        doc = cls.create_input_document(cls.doc_type_tutorial, *filenames)
        return doc

    def assert_sales_in_state(self, sales, state='sale'):
        for sale in sales:
            with self.subTest(sale=sale):
                self.assertEqual(sale.state, state)

    def test01_basic(self):
        """Fails immediately on missing product."""
        doc = self.create_tutorial('order02.csv')
        with tools.mute_logger('odoo.addons.edi.models.edi_issues'):
            self.assertFalse(doc.action_execute())

    def test02_removes_line_with_unknown_product(self):
        """Skips lines for unknown products"""
        doc = self.create_tutorial('order02.csv', fail_fast=False)
        self.assertTrue(doc.action_execute())
        customers = doc.mapped('partner_ids.partner_id')
        self.assertEqual(len(customers), 1)
        self.assertEqual(customers.mapped('name'), ['Alice'])
        sales = doc.mapped('sale_request_tutorial_ids.sale_id')
        self.assertEqual(len(sales), 1)
        self.assertEqual(doc.sale_ids, sales)
        self.assert_sales_in_state(sales)
        sales_by_name = {x.origin: x for x in sales}
        self.assertEqual(sales_by_name['ORD01'].partner_id.name, 'Alice')
        self.assertEqual(len(sales_by_name['ORD01'].order_line), 1)

    def test03_removes_orders_if_all_lines_removed(self):
        """Deletes orders if no lines exist."""
        doc = self.create_tutorial('order03.csv', fail_fast=False)
        self.assertTrue(doc.action_execute())
        sales = doc.mapped('sale_request_tutorial_ids.sale_id')
        self.assertEqual(len(sales), 2)
        self.assertEqual(doc.sale_ids, sales)
        self.assert_sales_in_state(sales)
        sales_by_name = {x.origin: x for x in sales}
        self.assertEqual(sales_by_name['ORD01'].partner_id.name, 'Alice')
        self.assertEqual(len(sales_by_name['ORD01'].order_line), 2)
        self.assertEqual(sales_by_name['ORD03'].partner_id.name, 'Carol')
        self.assertEqual(len(sales_by_name['ORD03'].order_line), 1)
        self.assertEqual(sales_by_name['ORD03'].order_line.product_id,
                         self.apple)
        self.assertEqual(sales_by_name['ORD03'].order_line.product_uom_qty, 2)

    def test04_removes_new_partners_with_no_orders(self):
        """Deletes partners if no lines exist."""
        doc = self.create_tutorial('order03.csv', fail_fast=False)
        self.assertTrue(doc.action_execute())
        customers = doc.mapped('partner_ids.partner_id')
        self.assertEqual(len(customers), 2)
        self.assertEqual(set(customers.mapped('name')), set(['Alice', 'Carol']))
        sales = doc.mapped('sale_request_tutorial_ids.sale_id')
        self.assertEqual(len(sales), 2)
        self.assertEqual(doc.sale_ids, sales)
        self.assert_sales_in_state(sales)
        sales_by_name = {x.origin: x for x in sales}
        self.assertEqual(sales_by_name['ORD01'].partner_id.name, 'Alice')
        self.assertEqual(len(sales_by_name['ORD01'].order_line), 2)
        self.assertEqual(sales_by_name['ORD03'].partner_id.name, 'Carol')
        self.assertEqual(len(sales_by_name['ORD03'].order_line), 1)
        self.assertEqual(sales_by_name['ORD03'].order_line.product_id,
                         self.apple)
        self.assertEqual(sales_by_name['ORD03'].order_line.product_uom_qty, 2)

    def test05_does_not_remove_existing_partners_with_no_orders(self):
        """Only deletes partners if no existing orders."""
        doc1 = self.create_tutorial('order03.csv', fail_fast=False)
        self.assertTrue(doc1.action_execute())
        customers = doc1.mapped('partner_ids.partner_id')
        self.assertEqual(len(customers), 2)
        self.assertEqual(set(customers.mapped('name')), set(['Alice', 'Carol']))

        doc2 = self.create_tutorial('order04.csv', fail_fast=False)
        self.assertTrue(doc2.action_execute())
        customers = doc2.mapped('partner_ids.partner_id')
        self.assertEqual(len(customers), 1)
        self.assertEqual(customers.mapped('name'), ['Bob'])
        sales = doc2.mapped('sale_request_tutorial_ids.sale_id')
        self.assertEqual(len(sales), 1)
        self.assertEqual(doc2.sale_ids, sales)
        self.assert_sales_in_state(sales)
        sales_by_name = {x.origin: x for x in sales}
        self.assertEqual(sales_by_name['ORD05'].partner_id.name, 'Bob')
        self.assertEqual(len(sales_by_name['ORD05'].order_line), 1)
        self.assertEqual(sales_by_name['ORD05'].order_line.product_id,
                         self.apple)
        self.assertEqual(sales_by_name['ORD05'].order_line.product_uom_qty, 1)
        Partner = self.env['res.partner']
        self.assertEqual(Partner.search_count([('name', '=', 'Alice')]), 1)

    # Not Working because the hack for create_sale is not raising an exception, is returning it
    # which is not getting picked up by the edi_synchronizer execute() method in the try and catch for the
    # creation of target model records
    #
    # def test06_removes_order_if_creation_fails(self):
    #     """Handle the case where an error occurs during order creation."""
    #     Sale = self.env['sale.order']
    #     create_method = Sale.create
    #
    #     # This is a bit hacky
    #     def create_sale(*args, **kwargs):
    #         cls, vals = args
    #         if vals['origin'] == 'ORD02':
    #             return ValidationError('Test Error')
    #         return create_method(vals)
    #
    #     doc = self.create_tutorial('order05.csv', fail_fast=False)
    #     with mock.patch.object(Sale.__class__, 'create', create=True, autospec=True, side_effect=create_sale):
    #         self.assertTrue(doc.action_execute())
    #     sales = doc.mapped('sale_request_tutorial_ids.sale_id')
    #     self.assertEqual(len(sales), 2)
    #     self.assertEqual(doc.sale_ids, sales)
    #     self.assert_sales_in_state(sales)
    #     sales_by_name = {x.origin: x for x in sales}
    #     self.assertNotIn('ORD02', sales_by_name)
    #     self.assertEqual(sales_by_name['ORD01'].partner_id.name, 'Alice')
    #     self.assertEqual(len(sales_by_name['ORD01'].order_line), 1)
    #     self.assertEqual(sales_by_name['ORD03'].partner_id.name, 'Carol')
    #     self.assertEqual(len(sales_by_name['ORD03'].order_line), 1)
    #     self.assertEqual(sales_by_name['ORD03'].order_line.product_id,
    #                      self.cherry)
    #     self.assertEqual(sales_by_name['ORD03'].order_line.product_uom_qty, 3)

    def test07_reports_missing_order_line(self):
        """Test reports missing lines from otherwise valid orders."""
        SaleRequestDocument = self.env['edi.sale.request.document']

        expected_message = '<p>Missing order lines\nORD01\tDURIAN\t2\tCannot identify Product "DURIAN"</p>'
        doc = self.create_tutorial('order02.csv', fail_fast=False)
        self.assertTrue(doc.action_execute())
        SaleLineRequestRecord = SaleRequestDocument.browse().sale_line_request_record_model(doc)
        error_domain = [('doc_id', '=', doc.id), ('error', '!=', False)]

        messages = self.MailMessage.search([('body', 'like', 'Missing order lines%')])
        self.assertEqual(len(messages), 1)
        self.assertEqual(expected_message, messages[0].body)
        self.assertEqual(SaleLineRequestRecord.search_count(error_domain), 0)

    # Pretty sure the issue here is the same as referenced above with the hacky method
    #
    # def test08_reports_lines_from_missing_order(self):
    #     """Test reports lines from completely invalid order."""
    #     Sale = self.env['sale.order']
    #     SaleRequestDocument = self.env['edi.sale.request.document']
    #
    #     expected_message = '<p>Missing order lines<br>ORD02\tBANANA\t2\tCannot identify Quotation "ORD02"</p>'
    #     create_method = Sale.create
    #
    #     # This is a bit hacky
    #     def create_sale(*args, **kw):
    #         cls, vals = args
    #         if vals['origin'] == 'ORD02':
    #             return ValidationError('Test Error')
    #         return create_method(vals)
    #
    #     doc = self.create_tutorial('order05.csv', fail_fast=False)
    #     with mock.patch.object(Sale.__class__, 'create', create=True, autospec=True, side_effect=create_sale):
    #         self.assertTrue(doc.action_execute())
    #     SaleLineRequestRecord = SaleRequestDocument.browse().sale_line_request_record_model(doc)
    #     error_domain = [('doc_id', '=', doc.id), ('error', '!=', False)]
    #
    #     messages = self.MailMessage.search([('body', 'like', 'Missing order lines%')])
    #     self.assertEqual(len(messages), 1)
    #     self.assertEqual(messages[0].body, expected_message)
    #     self.assertEqual(SaleLineRequestRecord.search_count(error_domain), 0)
