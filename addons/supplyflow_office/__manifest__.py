{
    "name": "SupplyFlow Office",
    "summary": "Purchase requests and supplier receipt resolution for office distributors",
    "version": "19.0.1.0.0",
    "category": "Inventory/Purchase",
    "author": "Muhammad Rafik",
    "website": "https://github.com/zalamanga/supplyflow-odoo",
    "license": "LGPL-3",
    "depends": ["purchase_stock", "sale_stock", "mail"],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "security/company_rules.xml",
        "data/sequences.xml",
        "views/purchase_request_views.xml",
        "views/supplier_issue_views.xml",
        "reports/purchase_request_report.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "supplyflow_office/static/src/workspace.js",
            "supplyflow_office/static/src/workspace.xml",
            "supplyflow_office/static/src/workspace.scss",
        ],
    },
    "application": True,
    "installable": True,
}
