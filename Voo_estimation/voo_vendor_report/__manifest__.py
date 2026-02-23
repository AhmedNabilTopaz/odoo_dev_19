# -*- coding: utf-8 -*-
{
    'name': 'Topaz Vendor reports',
    'version': '1.0',
    'author': "topaz",
    "description": """
    print excel file contains sales orders amount by users
    """,
    'depends': [
        'base',
        'report_xlsx',
        'stock',
        'sale',
        'hr'
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        # 'views/res_partner_view.xml',
        # 'views/sale_order_view.xml',
        'report/reports.xml',
        'wizard/sale_order_user_wizard.xml',

    ],

    'installable': True,
}
