# -*- coding: utf-8 -*-
{
    'name': 'Watan Journal Summary Print',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Print account totals (Debit/Credit/Balance) filtered by company, date range, and eZee accounts',
    'depends': ['account','odoo_ezee_pms_integration'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/journal_print_wizard_views.xml',
        'wizard/journal_summary_wizard_views.xml',
        'report/journal_print_report.xml',
        'report/journal_summary_report.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
