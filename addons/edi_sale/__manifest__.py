# pylint: disable=missing-docstring,pointless-statement
{
    'name': "EDI for Sales",
    'description': """
Electronic Data Interchange for Sales
=====================================

EDI capability for the Odoo ```sale``` module.

Key Features
------------
* Create and update sales orders from external EDI sources
* Report completed sales order to external EDI sources
    """,
    'version': '0.1',
    'depends': ['edi', 'sale'],
    'author': "Michael Brown <mbrown@fensystems.co.uk>",
    'category': "Extra Tools",
    'data': [
        'security/ir.model.access.csv',
        'data/edi_sale_report_data.xml',
        'data/edi_sale_report_tutorial_data.xml',
        'data/edi_sale_request_data.xml',
        'data/edi_sale_request_tutorial_data.xml',
        'views/edi_sale_document_views.xml',
        'views/edi_sale_request_views.xml',
        'views/edi_sale_line_request_views.xml',
        'views/edi_sale_request_tutorial_views.xml',
        'views/edi_sale_line_report_views.xml',
        'views/edi_sale_report_views.xml',
    ],
}
