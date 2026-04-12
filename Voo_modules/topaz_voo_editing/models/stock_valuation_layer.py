# -*- coding: utf-8 -*-
from odoo import fields, models


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    move_location_dest_id = fields.Many2one(
        comodel_name='stock.location',
        string="Destination Location",
        related="stock_move_id.location_dest_id",
        store=True,
        readonly=True,
    )
    move_origin = fields.Char(
        string="Source Document",
        related="stock_move_id.origin",
        store=True,
        readonly=True,
    )
