from odoo import models, fields


class HelpdeskTicketLine(models.Model):
    _name = 'helpdesk.ticket.line'
    _description = 'Helpdesk Ticket Line'
    _order = 'id'

    ticket_id = fields.Many2one(
        'helpdesk.ticket',
        string='Ticket',
        ondelete='cascade',
        required=True,
        help='The helpdesk ticket this line belongs to'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        ondelete='set null',
        help='Product associated with this ticket line'
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lot/Serial Number',
        ondelete='set null',
        help='Lot or serial number of the product'
    )
    model = fields.Char(
        string='Model',
        help='Model identifier of the product'
    )
    problem_description = fields.Char(
        string='Problem Description',
        help='Description of the problem with this product'
    )
    status = fields.Char(
        string='Status',
        help='Current status of this product line'
    )