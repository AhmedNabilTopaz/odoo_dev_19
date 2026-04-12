# -*- coding: utf-8 -*-
{
    'name': "Retail Tech Editing module",
    'version': '19.0.0.0',
    'summary': """
        """,

    'description': """
    """,
    'price': 000,
    'currency': 'EUR',
    'author': "topaz team",
    'website': "https://www.topazsmart.com",
    'category': 'Sales',
    'license': 'OPL-1',

    # any module necessary for this one to work correctly
    'depends': ['stock', 'sale','purchase','stock_account'],

    # always loaded
    'data': [
        'security/groups.xml',
        'views/stock_move_line_inherit.xml',
        'views/stock_lot_tree_view.xml',
        'views/valuation_inherit.xml',
        # 'views/purchase_views.xml',


    ],
    'installable': True,
    'auto_install': False,
}
