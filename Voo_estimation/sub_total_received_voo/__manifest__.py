# -*- coding: utf-8 -*-
{
    'name': "Subtotal Received PO",
    'version': '19.0.1.0.0',
    'summary': """
        Calculate and display received amounts with taxes for Purchase Orders
        """,

    'description': """
        This module adds functionality to track received quantities with taxes:
        - Subtotal received amounts on purchase order lines
        - Tax calculations on received quantities
        - Total received amounts on purchase orders
        - Vendor information on stock moves
    """,
    'price': 000,
    'currency': 'EUR',
    'author': "Topaz Team",
    'website': "https://www.topazsmart.com",
    'category': 'Inventory/Purchase',
    'license': 'OPL-1',

    # Dependencies
    'depends': ['stock', 'sale', 'purchase'],

    # Data files
    'data': [
        'views/sub_total_received_views.xml',
        'views/stock_search_view.xml',
        'views/barcode_edits.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': False,
}
