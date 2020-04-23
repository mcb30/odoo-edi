# -*- coding: utf-8 -*-
{
    "name": "EDI for Sales JSON",
    "description": """Electronic Data Interchange for Sales via JSON""",
    "version": "0.1",
    "author": "Unipart Digital",
    "category": "Extra Tools",
    "version": "0.1",
    "depends": [
        "edi",
        "edi_sale",
    ],
    "external_dependencies": {"python": ["jsonschema"]},
    "data": [
        "data/edi_sale_forwarding_data.xml",
        "data/edi_gateway.xml",
        "data/ir_cron.xml",
        "views/edi_sale_forward_views.xml",
        "security/ir.model.access.csv",
    ],
}
