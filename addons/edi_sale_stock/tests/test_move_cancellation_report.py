"""EDI stock transfer report tests"""

from odoo.addons.edi_stock.tests.test_move_cancellation_report import TestMoveCancellationReport
import datetime


class TestSaleStockMoveCancellationReport(TestMoveCancellationReport):
    """EDI sale_stock move cancellation report tests"""

    @classmethod
    def setUpClass(cls):
        """
        Inherit to create some sales & lines, and link them to
        the move lines created in the parent class. This is to ensure
        the sale values are showing up in the email template
        """
        super().setUpClass()

        SaleOrder = cls.env["sale.order"]
        SaleOrderLine = cls.env["sale.order.line"]
        # Swap the partners around (so pick1's partner is on sale2, pick2's partner is on sale1)
        # This is to ensure that partner differs from the pick partner on the email
        # and to ensure we display companies/individuals correctly
        sale = SaleOrder.create(
            {
                "partner_id": cls.company_partner.id,
                "client_order_ref": "SALE_REF1",
                "requested_date": datetime.datetime.now(),
            }
        )
        sale2 = SaleOrder.create(
            {
                "partner_id": cls.admin_partner.id,
                "client_order_ref": "SALE_REF2",
                "requested_date": datetime.datetime.now(),
            }
        )
        sale_line1 = SaleOrderLine.create(
            {
                "name": cls.apple.name,
                "order_id": sale.id,
                "product_id": cls.apple.id,
                "product_uom_qty": 5,
                "product_uom": cls.apple.uom_id.id,
            }
        )
        sale_line2 = SaleOrderLine.create(
            {
                "name": cls.banana.name,
                "order_id": sale.id,
                "product_id": cls.banana.id,
                "product_uom_qty": 7,
                "product_uom": cls.banana.uom_id.id,
            }
        )
        sale2_line1 = SaleOrderLine.create(
            {
                "name": cls.apple.name,
                "order_id": sale2.id,
                "product_id": cls.apple.id,
                "product_uom_qty": 9,
                "product_uom": cls.apple.uom_id.id,
            }
        )
        sale2_line2 = SaleOrderLine.create(
            {
                "name": cls.banana.name,
                "order_id": sale2.id,
                "product_id": cls.banana.id,
                "product_uom_qty": 4,
                "product_uom": cls.banana.uom_id.id,
            }
        )
        cls.pick_out.move_lines.filtered(
            lambda move: move.product_id == cls.apple
        ).sale_line_id = sale_line1
        cls.pick_out.move_lines.filtered(
            lambda move: move.product_id == cls.banana
        ).sale_line_id = sale_line2
        cls.pick_out2.move_lines.filtered(
            lambda move: move.product_id == cls.apple
        ).sale_line_id = sale2_line1
        cls.pick_out2.move_lines.filtered(
            lambda move: move.product_id == cls.banana
        ).sale_line_id = sale2_line2
        cls.email_subject = f"Cancellation For {sale.client_order_ref}"
        cls.email2_subject = f"Cancellation For {sale2.client_order_ref}"

    def _expected_mailbody_test02(self):
        return [
            '<p>Products have been cancelled from <span style="font-weight: bold;">SALE_REF1</span> for the following customer:</p>',
            '        <p>',
            '            My Company<br>Pork Futures Warehouse<br><br>Ankh-Morpork  <br></p>',
            '        <h3>The following product(s) have been cancelled:</h3>',
            '        <!-- Table is built in divs because Odoo WYSIWYG editor',
            '            butchers for loops in tables if you edit & save the template -->',
            '        <div style="display:table;">',
            '            <div style="display:table-header-group;">',
            '                <div style="display:table-row;">',
            '                    <div style="display:table-cell; padding: 0px 5px;">Part Number</div>',
            '                    <div style="display:table-cell; padding: 0px 5px;">Quantity Ordered</div>',
            '                    <div style="display:table-cell; padding: 0px 5px;">Cancelled By</div>',
            '                </div>',
            '            </div>',
            '            <div style="display:table-row-group;">',
            '                    <div style="display:table-row;">',
            '                        <div style="display:table-cell; padding: 0px 5px;">[BANANA] Banana</div>',
            '                        <div style="display:table-cell; padding: 0px 5px;">',
            '                                7.0',
            '                        </div>',
            '                        <div style="display:table-cell; padding: 0px 5px;">Administrator</div>',
            '                    </div>',
            '            </div>',
            '        </div>',
            '        ',
            '            '
        ]

    def _expected_mailbody_test03(self):
        return [
            '<p>Products have been cancelled from <span style="font-weight: bold;">SALE_REF1</span> for the following customer:</p>',
            '        <p>',
            '            My Company<br>Pork Futures Warehouse<br><br>Ankh-Morpork  <br></p>',
            '        <h3>The following product(s) have been cancelled:</h3>',
            '        <!-- Table is built in divs because Odoo WYSIWYG editor',
            '            butchers for loops in tables if you edit & save the template -->',
            '        <div style="display:table;">',
            '            <div style="display:table-header-group;">',
            '                <div style="display:table-row;">',
            '                    <div style="display:table-cell; padding: 0px 5px;">Part Number</div>',
            '                    <div style="display:table-cell; padding: 0px 5px;">Quantity Ordered</div>',
            '                    <div style="display:table-cell; padding: 0px 5px;">Cancelled By</div>',
            '                </div>',
            '            </div>',
            '            <div style="display:table-row-group;">',
            '                    <div style="display:table-row;">',
            '                        <div style="display:table-cell; padding: 0px 5px;">[APPLE] Apple</div>',
            '                        <div style="display:table-cell; padding: 0px 5px;">',
            '                                5.0',
            '                        </div>',
            '                        <div style="display:table-cell; padding: 0px 5px;">Administrator</div>',
            '                    </div>',
            '                    <div style="display:table-row;">',
            '                        <div style="display:table-cell; padding: 0px 5px;">[BANANA] Banana</div>',
            '                        <div style="display:table-cell; padding: 0px 5px;">',
            '                                7.0',
            '                        </div>',
            '                        <div style="display:table-cell; padding: 0px 5px;">Administrator</div>',
            '                    </div>',
            '            </div>',
            '        </div>',
            '        ',
            '            '
        ]

    def _expected_mailbody2_test03(self):
        return [
            '<p>Products have been cancelled from <span style="font-weight: bold;">SALE_REF2</span> for the following customer:</p>',
            '        <p>',
            '                Administrator<br>',
            '            The Tower of Art<br>Unseen University<br>Ankh-Morpork  <br></p>',
            '        <h3>The following product(s) have been cancelled:</h3>',
            '        <!-- Table is built in divs because Odoo WYSIWYG editor',
            '            butchers for loops in tables if you edit & save the template -->',
            '        <div style="display:table;">',
            '            <div style="display:table-header-group;">',
            '                <div style="display:table-row;">',
            '                    <div style="display:table-cell; padding: 0px 5px;">Part Number</div>',
            '                    <div style="display:table-cell; padding: 0px 5px;">Quantity Ordered</div>',
            '                    <div style="display:table-cell; padding: 0px 5px;">Cancelled By</div>',
            '                </div>',
            '            </div>',
            '            <div style="display:table-row-group;">',
            '                    <div style="display:table-row;">',
            '                        <div style="display:table-cell; padding: 0px 5px;">[APPLE] Apple</div>',
            '                        <div style="display:table-cell; padding: 0px 5px;">',
            '                                9.0',
            '                        </div>',
            '                        <div style="display:table-cell; padding: 0px 5px;">Administrator</div>',
            '                    </div>',
            '            </div>',
            '        </div>',
            '        ',
            '            '
        ]
