from odoo import models, fields


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    branch = fields.Char(
        string='Branch',
        help='Branch identifier for this ticket'
    )
    source_id = fields.Many2one(
        'utm.source',
        string='Source',
        ondelete='set null',
        help='UTM source tracking for ticket origin'
    )
    line_ids = fields.One2many(
        'helpdesk.ticket.line',
        'ticket_id',
        string='Product Lines',
        help='Products associated with this helpdesk ticket'
    )