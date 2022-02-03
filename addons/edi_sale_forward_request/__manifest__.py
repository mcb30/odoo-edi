{
    "name": "Edi Sale json forward request",
    "summary": """Adds support for json file to existing
    Edi functionality""",
    "author": "Unipart Digital Team",
    "license": "LGPL-3",
    "website": "https://unipart.io",
    "category": "Extra Tools",
    "version": "0.1",
    "depends": ["edi", "edi_sale", "sale_management"],
    "external_dependencies": {"python": ["jsonschema"]},
    "data": [
        "security/ir.model.access.csv",
        "data/edi_partner_record_data.xml",
        "data/edi_sale_forward_request_data.xml",
        "data/edi_gateway.xml",
        "data/ir_cron.xml",
        "views/edi_partner_views.xml",
        "views/edi_sale_forward_request_views.xml",
    ],
    "demo": [],
}
