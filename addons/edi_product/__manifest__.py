# pylint: disable=missing-docstring,pointless-statement
{
    "name": "EDI for Products & Pricelists",
    "description": """
Electronic Data Interchange for Products & Pricelists
=====================================================

EDI capability for the Odoo ```product``` module.

Key Features
------------
* Quickly import product lists from external EDI sources
* Automatic deduplication of unmodified product records
* Easily customisable to handle new or custom document formats
    """,
    "version": "0.1",
    "depends": ["edi", "product"],
    "author": "Michael Brown <mbrown@fensystems.co.uk>",
    "category": "Extra Tools",
    "data": [
        "security/ir.model.access.csv",
        "views/edi_product_views.xml",
        "views/edi_product_sap_views.xml",
        "data/edi_product_data.xml",
        "data/edi_product_sap_data.xml",
    ],
}
