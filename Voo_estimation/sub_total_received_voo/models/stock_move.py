# -*- coding: utf-8 -*-
from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    vendor_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        related="purchase_line_id.order_id.partner_id",
        store=False,
        index=True,
        readonly=True,
    )


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    vendor_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        related="move_id.vendor_id",
        store=False,
        index=True,
        readonly=True,
    )
