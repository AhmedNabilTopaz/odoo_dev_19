# -*- coding: utf-8 -*-
from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    # FIX: was computing vendor_id (singular) but writing to vendor_ids (plural)
    # Corrected to a Many2many field matching the actual logic
    vendor_ids = fields.Many2many(
        comodel_name='res.partner',
        string="Vendors",
        compute="_compute_vendor_ids",
        store=True,
        readonly=True,
    )

    def _compute_vendor_ids(self):
        for line in self:
            sellers = line.product_id.seller_ids
            partners = sellers.mapped('partner_id')
            line.vendor_ids = [(6, 0, partners.ids)] if partners else [(5, 0, 0)]
