# -*- coding: utf-8 -*-
{
    'name': 'Enhance Computed Fields',
    'version': '1.0',
    'summary': 'Brief description of the module',
    'description': '''
        Detailed description of the module
    ''',
    'depends': ['base', 'mail', 'stock','purchase','mail'],
    'data': [
        'views/stock_search.xml',
        'views/purchase_order_view.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}