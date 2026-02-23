# -*- coding: utf-8 -*-
{
    'name': 'Topaz Voo',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Purchase',
    'license': 'OPL-1',
    'summary': 'Topaz VOO customizations for stock, POS, accounting and vending machines',
    'description': """
        Topaz VOO module providing:
        - Stock picking and move customizations
        - Vending machine POS integration
        - Account move notifications via Discuss
        - Product status and tag enhancements
        - Stock valuation layer extensions
        - Vending machine REST API
    """,
    'author': 'Topaz Smart',
    'website': 'https://topaz-smart.odoo.com/',
    'depends': [
        'base',
        'account',
        'stock',
        'stock_account',
        'purchase',
        'mail',
        'point_of_sale',
        'auth_api_key',
        'account_accountant',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/discuss_channel.xml',
        'report/stock_report.xml',
        'report/purchase_reports.xml',
        'report/report_delivery_slip.xml',
        'views/purchase_views.xml',
        'views/res.config.settings_view.xml',
        'views/account_move_views.xml',
        'views/product_template.xml',
        'views/stock_picking.xml',
        'views/pos_order_form_view.xml',
        'views/vending_machine_views.xml',
        # 'views/stock_valuation_layer_tree.xml',
        'views/stock_picking_type.xml',
    ],
    'installable': True,
    'auto_install': False,
    'images': ['static/description/Banner.png'],
}