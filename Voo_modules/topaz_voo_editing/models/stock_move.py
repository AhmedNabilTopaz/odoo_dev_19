# -*- coding: utf-8 -*-
from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    po_uom = fields.Char(
        string="PO UOM",
        related='purchase_line_id.product_uom_id.name',
        readonly=True,
    )

    to_delete = fields.Boolean(string='To Delete')
