# -*- coding: utf-8 -*-
{
    'name': 'Allegro Edit',
    'version': '19.0.1.0.0',
    'category': 'Tools',
    'summary': 'Allegro Edit Module',
    'description': """
        Allegro Edit Module
        ===================
        This module provides functionality & Solution for Allegro Company.
    """,
    'author': 'Topaz Team',
    'license': 'LGPL-3',
    'depends': [
        'base', 'stock'
    ],
    'data': [
        'views/stock_picing_view.xml',
		'reports/delivery_slip_report.xml'
],
    'installable': True,
    'application': False,
    'auto_install': False,
}
