# -*- coding: utf-8 -*-
{
    'name': "Import Serial Lots",
    'version': '19.0.1.0.0',
    'summary': "Import Lots/Serials from Excel to Stock Move",
    'author': "topaz team",
    'website': "https://www.topazsmart.com",
    'category': 'Inventory',
    'license': 'OPL-1',

    'depends': ['stock', 'sale', 'purchase'],

    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_view.xml',
        'wizards/lot_import_wizard.xml',
    ],

    'installable': True,
    'application': False,
}
