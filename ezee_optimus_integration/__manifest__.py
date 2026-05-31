{
    'name': 'eZee Optimus POS Integration',
    'version': '19.0.1.0.0',
    'summary': 'One-way sync from eZee Optimus POS to Odoo 19',
    'author': 'Dubaiincario',
    'category': 'Accounting',
    'depends': ['account', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/ezee_optimus_outlet_views.xml',
        'views/ezee_optimus_mapping_views.xml',
        'views/ezee_optimus_sync_views.xml',
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
