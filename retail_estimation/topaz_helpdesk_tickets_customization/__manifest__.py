{
    'name': "Topaz helpdesk Tickets",
    'summary': """Add product lines to ticket which make user can select more than one product on each ticket""",
    'description': """
        This module extends the helpdesk.ticket model to support multiple product lines.
        Each ticket can now have multiple products associated with it, with details like
        lot numbers, model information, problem descriptions, and status tracking.
    """,

    'author': "Tarek Ashry",
    'company': "Topaz",
    'website': "https://topazsmart.com",

    'category': 'Services',
    'version': '19.0.1.0.0',
    'depends': [
        'base',
        'helpdesk',
        'helpdesk_timesheet',
        'utm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/helpdesk_ticket_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}