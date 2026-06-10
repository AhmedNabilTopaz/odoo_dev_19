from odoo import models, fields


class AccountMoveEzeeExtend(models.Model):
    _inherit = 'account.move'

    ezee_balance = fields.Float(
        string='eZee Outstanding Balance',
        default=0.0,
        help='Outstanding balance as reported by eZee Optimus at sync time.',
    )
    ezee_payment_status = fields.Selection(
        selection=[
            ('paid', 'Paid'),
            ('unpaid', 'Unpaid'),
        ],
        string='eZee Payment Status',
        default=False,
        help='Payment status from eZee Optimus. Paid = balance is 0 at sync time.',
    )