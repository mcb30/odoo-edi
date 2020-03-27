# pylint: disable=missing-docstring,pointless-statement
{
    "name": "EDI Tutorial",
    "summary": "Electronic Data Interchange",
    "description": """
Electronic Data Interchange
===========================

Manage the automated transfer of data between Odoo and external
systems.

Key Features
------------
* Handle EDI documents as standard Odoo attachments
* View and search full EDI document history
* Preview modifications made by EDI documents
* Audit trail including SHA-1 checksums of all files
* Manually execute EDI documents for testing and development
* Autodetect EDI document type based on input files
* Send and receive documents to/from remote EDI servers
* Schedule polling of remote EDI servers
* Process EDI documents via XML-RPC interface
* Handle errors via Odoo issue tracker
    """,
    "version": "0.1",
    "depends": ["edi"],
    "author": "Michael Brown <mbrown@fensystems.co.uk>",
    "category": "Extra Tools",
    "data": [
        "security/ir.model.access.csv",
        "data/edi_partner_tutorial_data.xml",
        "views/edi_partner_tutorial_views.xml",
    ],
    "qweb": [],
}
