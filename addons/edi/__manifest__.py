# pylint: disable=missing-docstring,pointless-statement
{
    "name": "EDI",
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
    "depends": ["project"],
    "external_dependencies": {"python": ["paramiko", "ply"]},
    "author": "Michael Brown <mbrown@fensystems.co.uk>",
    "category": "Extra Tools",
    "data": [
        "security/ir.model.access.csv",
        "data/project_issue_data.xml",
        "data/edi_document_data.xml",
        "data/edi_gateway_local_data.xml",
        "data/edi_gateway_mail_data.xml",
        "data/edi_gateway_xmlrpc_data.xml",
        "data/edi_partner_data.xml",
        "data/edi_raw_data.xml",
        "views/edi_menu_views.xml",
        "views/edi_document_views.xml",
        "views/edi_document_type_views.xml",
        "views/edi_gateway_views.xml",
        "views/edi_gateway_path_views.xml",
        "views/edi_partner_views.xml",
        "views/edi_partner_title_views.xml",
        "views/edi_raw_views.xml",
        "views/edi_record_type_views.xml",
        "views/edi_transfer_views.xml",
        "views/ir_attachment_views.xml",
        "views/ir_actions_views.xml",
        "views/ir_cron_views.xml",
        "views/mail_views.xml",
        "views/project_issue_views.xml",
        "wizard/edi_autocreate.xml",
    ],
    "qweb": ["static/src/xml/thread.xml"],
}
