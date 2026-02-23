# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    x_studio_customer = fields.Many2one(
        'res.partner',
        related='picking_id.x_studio_customer',
        store=True,
        string='Customer'
    )
