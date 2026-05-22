from odoo import fields, models

class EzeeOptimusOutlet(models.Model):
    _name = 'ezee.optimus.outlet'
    _description = 'eZee Optimus F&B Outlet'
    _rec_name = 'name'

    ezee_outlet_id = fields.Char(
        string='eZee Outlet ID', required=True, index=True,
        help='The numeric ID returned by get_store_name API'
    )
    name = fields.Char(string='Outlet Name', required=True)
    active = fields.Boolean(default=True)

    # Journal for sales from this outlet
    sales_journal_id = fields.Many2one(
        'account.journal',
        string='Sales Journal',
        domain="[('type', 'in', ['sale', 'general'])]",
        help='Journal to use when posting POS sales from this outlet'
    )

    # Journal for purchases (GRNs) from this outlet
    purchase_journal_id = fields.Many2one(
        'account.journal',
        string='Purchase Journal',
        domain="[('type', '=', 'purchase')]",
        help='Journal to use for vendor bills from this outlet'
    )

    # Optional: analytic account for branch-level reporting
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        help='Optional: used for branch or outlet-level P&L reporting'
    )

    _sql_constraints = [
        ('unique_ezee_outlet_id', 'UNIQUE(ezee_outlet_id)',
         'Each eZee outlet ID must be unique.')
    ]
