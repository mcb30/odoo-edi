# pylint: disable=missing-docstring,pointless-statement
{
    "name": "EDI for Sale & Inventory Management",
    "description": """
Electronic Data Interchange for Sale Inventory Management
=========================================================

EDI capability for the Odoo ```sale_stock``` module.

Key Features
------------
* Extend move_cancellation_report_document to consider sales order information when preparing the report
    """,
    "version": "0.1",
    "depends": ["edi_stock", "sale_stock"],
    "author": "Peter Alabaster <peter.alabaster@unipart.io>",
    "category": "Extra Tools",
    "data": [],
}
