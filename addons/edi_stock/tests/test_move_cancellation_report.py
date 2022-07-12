"""EDI stock transfer report tests"""

from .common import EdiPickCase


class TestMoveCancellationReport(EdiPickCase):
    """EDI stock move cancellation report tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.EdiDocument = cls.env["edi.document"]
        cls.EdiMoveCancellationReport = cls.env["edi.record.stock.cancellation"]
        cls.doc_type_move_cancellation_report = cls.env.ref(
            "edi_stock.edi_document_type_move_cancellation"
        )
        # Configure a pick type with the necessary config
        # to get picked up by the cancellation EDI
        cls.pick_type_out.x_enable_pick_cancellation_email_notifs = True
        cls.pick_type_out.x_pick_cancellation_email_notif_template_id = cls.env.ref(
            "edi_stock.move_cancellation_template"
        ).id
        cls.pick_out = cls.create_pick(cls.pick_type_out)
        # Moves with no sale require the pick partner to be set
        cls.admin_partner = cls.env.user.partner_id
        cls.company_partner = cls.env.ref("base.main_partner")
        cls.admin_partner.write({
            "street": "The Tower of Art",
            "street2": "Unseen University",
            "city": "Ankh-Morpork",
        })
        cls.company_partner.write({
            "street": "Pork Futures Warehouse",
            "city": "Ankh-Morpork",
        })

        cls.pick_out.partner_id = cls.admin_partner
        cls.pick_out.origin = "TEST"

        cls.create_move(cls.pick_out, None, cls.apple, 5)
        cls.create_move(cls.pick_out, None, cls.banana, 7)

        cls.pick_out2 = cls.create_pick(cls.pick_type_out)
        # This pick goes to a different partner
        cls.pick_out2.partner_id = cls.company_partner
        cls.pick_out2.origin = "TEST2"

        cls.create_move(cls.pick_out2, None, cls.apple, 9)
        cls.create_move(cls.pick_out2, None, cls.banana, 4)
        cls.email_subject = f"Cancellation For {cls.pick_out.origin}"
        cls.email2_subject = f"Cancellation For {cls.pick_out2.origin}"

    def create_and_execute_edi_doc(self, name):
        """Helper function to create and execute,
        then return an EDI move cancellation document
        with a given name"""
        doc = self.EdiDocument.create(
            {
                "name": name,
                "doc_type_id": self.doc_type_move_cancellation_report.id,
            }
        )
        self.assertTrue(doc.action_execute())
        return doc

    def test01_empty(self):
        """Test document with no move cancellations"""
        doc = self.create_and_execute_edi_doc("Empty Move cancellation report test")
        move_cancellation_reports = self.EdiMoveCancellationReport.search([("doc_id", "=", doc.id)])
        self.assertFalse(move_cancellation_reports)

    def _expected_mailbody_test02(self):
        """Expected mail body for test02
        Split into function to allow ease of test extension in edi_sale_stock"""
        return [
            '<p>Products have been cancelled from <span style="font-weight: bold;">TEST</span> for the following customer:</p>',
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
            '                    <div style="display:table-cell; padding: 0px 5px;">Quantity Cancelled</div>',
            '                    <div style="display:table-cell; padding: 0px 5px;">Cancelled By</div>',
            '                </div>',
            '            </div>',
            '            <div style="display:table-row-group;">',
            '                    <div style="display:table-row;">',
            '                        <div style="display:table-cell; padding: 0px 5px;">[BANANA] Banana</div>',
            '                        <div style="display:table-cell; padding: 0px 5px;">',
            '                            7.0',
            '                        </div>',
            '                        <div style="display:table-cell; padding: 0px 5px;">Administrator</div>',
            '                    </div>',
            '            </div>',
            '        </div>',
            '        ',
            '            '
        ]

    def test02_cancelled_line(self):
        """Test document with a single cancelled move"""
        moves_to_cancel = self.pick_out.move_lines.filtered(
            lambda move: move.product_id == self.banana
        )
        moves_to_cancel._action_cancel()
        doc = self.create_and_execute_edi_doc("Move cancellation report test Banana")
        move_cancellation_reports = self.EdiMoveCancellationReport.search([("doc_id", "=", doc.id)])
        self.assertTrue(len(move_cancellation_reports), 1)
        self.assertTrue(len(move_cancellation_reports.move_ids), 1)
        self.assertTrue(move_cancellation_reports.sent_email_id.subject == self.email_subject)
        cancellation_email_body_lines = move_cancellation_reports.sent_email_id.body_html.splitlines()
        self.assertEqual(cancellation_email_body_lines, self._expected_mailbody_test02())
        # Also assert that the move does not show in the next report
        doc2 = self.create_and_execute_edi_doc("Empty Move cancellation report test")
        move_cancellation_reports2 = self.EdiMoveCancellationReport.search(
            [("doc_id", "=", doc2.id)]
        )
        self.assertFalse(move_cancellation_reports2)

    def _expected_mailbody_test03(self):
        """Expected mail body for first email in test03
        Split into function to allow ease of test extension in edi_sale_stock"""
        return [
            '<p>Products have been cancelled from <span style="font-weight: bold;">TEST</span> for the following customer:</p>',
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
            '                    <div style="display:table-cell; padding: 0px 5px;">Quantity Cancelled</div>',
            '                    <div style="display:table-cell; padding: 0px 5px;">Cancelled By</div>',
            '                </div>',
            '            </div>',
            '            <div style="display:table-row-group;">',
            '                    <div style="display:table-row;">',
            '                        <div style="display:table-cell; padding: 0px 5px;">[APPLE] Apple</div>',
            '                        <div style="display:table-cell; padding: 0px 5px;">',
            '                            5.0',
            '                        </div>',
            '                        <div style="display:table-cell; padding: 0px 5px;">Administrator</div>',
            '                    </div>',
            '                    <div style="display:table-row;">',
            '                        <div style="display:table-cell; padding: 0px 5px;">[BANANA] Banana</div>',
            '                        <div style="display:table-cell; padding: 0px 5px;">',
            '                            7.0',
            '                        </div>',
            '                        <div style="display:table-cell; padding: 0px 5px;">Administrator</div>',
            '                    </div>',
            '            </div>',
            '        </div>',
            '        ',
            '            '
        ]
    
    def _expected_mailbody2_test03(self):
        """Expected mail body for second email in test03
        Split into function to allow ease of test extension in edi_sale_stock"""
        return [
            '<p>Products have been cancelled from <span style="font-weight: bold;">TEST2</span> for the following customer:</p>',
            '        <p>',
            '            My Company<br>Pork Futures Warehouse<br><br>Ankh-Morpork  <br></p>',
            '        <h3>The following product(s) have been cancelled:</h3>',
            '        <!-- Table is built in divs because Odoo WYSIWYG editor',
            '            butchers for loops in tables if you edit & save the template -->',
            '        <div style="display:table;">',
            '            <div style="display:table-header-group;">',
            '                <div style="display:table-row;">',
            '                    <div style="display:table-cell; padding: 0px 5px;">Part Number</div>',
            '                    <div style="display:table-cell; padding: 0px 5px;">Quantity Cancelled</div>',
            '                    <div style="display:table-cell; padding: 0px 5px;">Cancelled By</div>',
            '                </div>',
            '            </div>',
            '            <div style="display:table-row-group;">',
            '                    <div style="display:table-row;">',
            '                        <div style="display:table-cell; padding: 0px 5px;">[APPLE] Apple</div>',
            '                        <div style="display:table-cell; padding: 0px 5px;">',
            '                            9.0',
            '                        </div>',
            '                        <div style="display:table-cell; padding: 0px 5px;">Administrator</div>',
            '                    </div>',
            '            </div>',
            '        </div>',
            '        ',
            '            '
        ]

    def test03_multi_cancellation(self):
        """Test document with a full pick cancellation,
        and part pick cancellation for another partner"""
        moves_to_cancel = self.pick_out.move_lines | self.pick_out2.move_lines.filtered(
            lambda move: move.product_id == self.apple
        )
        moves_to_cancel._action_cancel()
        doc = self.create_and_execute_edi_doc("Move cancellation report test Apples and Bananas")
        move_cancellation_reports = self.EdiMoveCancellationReport.search([("doc_id", "=", doc.id)])
        self.assertTrue(len(move_cancellation_reports), 2)
        self.assertTrue(len(move_cancellation_reports.mapped("move_ids")), 3)
        move_cancellation_report = move_cancellation_reports.filtered(
            lambda report: report.sent_email_id.subject == self.email_subject
        )
        move_cancellation_report2 = move_cancellation_reports - move_cancellation_report
        self.assertTrue(move_cancellation_report.sent_email_id.subject == self.email_subject)
        self.assertTrue(move_cancellation_report2.sent_email_id.subject == self.email2_subject)

        cancellation_email_body_lines = move_cancellation_report.sent_email_id.body_html.splitlines()
        cancellation_email2_body_lines = move_cancellation_report2.sent_email_id.body_html.splitlines()
        self.assertEqual(cancellation_email_body_lines, self._expected_mailbody_test03())
        self.assertEqual(cancellation_email2_body_lines, self._expected_mailbody2_test03())

        # Also assert that the moves do not show in the next report
        doc2 = self.create_and_execute_edi_doc("Empty Move cancellation report test")
        move_cancellation_reports2 = self.EdiMoveCancellationReport.search(
            [("doc_id", "=", doc2.id)]
        )
        self.assertFalse(move_cancellation_reports2)

    def _expected_mailbody_test04(self):
        """Expected mail body for second email in test04
        Split into function to allow ease of test extension in edi_sale_stock"""
        return [
            '<p>Products have been cancelled from <span style="font-weight: bold;">TEST</span> for the following customer:</p>',
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
            '                    <div style="display:table-cell; padding: 0px 5px;">Quantity Cancelled</div>',
            '                    <div style="display:table-cell; padding: 0px 5px;">Cancelled By</div>',
            '                </div>',
            '            </div>',
            '            <div style="display:table-row-group;">',
            '                    <div style="display:table-row;">',
            '                        <div style="display:table-cell; padding: 0px 5px;">[APPLE] Apple</div>',
            '                        <div style="display:table-cell; padding: 0px 5px;">',
            '                            5.0',
            '                        </div>',
            '                        <div style="display:table-cell; padding: 0px 5px;">Administrator</div>',
            '                    </div>',
            '            </div>',
            '        </div>',
            '        ',
            '            '
        ]
    
    def _expected_mailbody2_test04(self):
        """Expected mail body for second email in test04
        Split into function to allow ease of test extension in edi_sale_stock"""
        return [
            '<p>Products have been cancelled from <span style="font-weight: bold;">TEST</span> for the following customer:</p>',
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
            '                    <div style="display:table-cell; padding: 0px 5px;">Quantity Cancelled</div>',
            '                    <div style="display:table-cell; padding: 0px 5px;">Cancelled By</div>',
            '                </div>',
            '            </div>',
            '            <div style="display:table-row-group;">',
            '                    <div style="display:table-row;">',
            '                        <div style="display:table-cell; padding: 0px 5px;">[BANANA] Banana</div>',
            '                        <div style="display:table-cell; padding: 0px 5px;">',
            '                            7.0',
            '                        </div>',
            '                        <div style="display:table-cell; padding: 0px 5px;">Administrator</div>',
            '                    </div>',
            '            </div>',
            '        </div>',
            '        ',
            '            '
        ]

    def test04_partial_then_full_move_cancellation(self):
        """Test document brings in newly cancelled moves off the same pick
        when a report is run after each individual move cancellation"""
        # Cancel apples off pick1
        moves_to_cancel = self.pick_out.move_lines.filtered(
            lambda move: move.product_id == self.apple
        )
        moves_to_cancel._action_cancel()
        doc = self.create_and_execute_edi_doc("Move cancellation report test Apple")
        move_cancellation_reports = self.EdiMoveCancellationReport.search([("doc_id", "=", doc.id)])
        cancellation_email_body_lines = move_cancellation_reports.sent_email_id.body_html.splitlines()
        self.assertTrue(len(move_cancellation_reports), 1)
        self.assertTrue(len(move_cancellation_reports.mapped("move_ids")), 1)
        self.assertEqual(cancellation_email_body_lines, self._expected_mailbody_test04())

        # Cancel bananas off pick1
        moves_to_cancel2 = self.pick_out.move_lines.filtered(
            lambda move: move.product_id == self.banana
        )
        moves_to_cancel2._action_cancel()
        doc2 = self.create_and_execute_edi_doc("Move cancellation report test Banana")
        move_cancellation_reports2 = self.EdiMoveCancellationReport.search([("doc_id", "=", doc2.id)])
        cancellation_email_body_lines = move_cancellation_reports2.sent_email_id.body_html.splitlines()
        self.assertTrue(len(move_cancellation_reports2), 1)
        self.assertTrue(len(move_cancellation_reports2.mapped("move_ids")), 1)
        self.assertEqual(cancellation_email_body_lines, self._expected_mailbody2_test04())
