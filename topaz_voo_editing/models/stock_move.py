# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    po_uom = fields.Char(
        string="PO UOM",
        related='purchase_line_id.product_uom_id.name',
        readonly=True,
    )

    to_delete = fields.Boolean(string='To Delete')

    @api.depends('product_id', 'picking_type_id', 'description_picking_manual')
    def _compute_description_picking(self):
        super()._compute_description_picking()
        for move in self:
            if not move.description_picking_manual and move.product_id:
                # Set description to product's display_name to hide internal note in UI
                move.description_picking = move.product_id.display_name

    # def _search_picking_for_assignation(self):
    #     """Override to prevent merging internal transfer moves into existing open pickings.
    #     Each internal transfer order should always get its own picking."""
    #     self.ensure_one()
    #     if self.picking_type_id and self.picking_type_id.code == 'internal':
    #         return self.env['stock.picking']
    #     return super()._search_picking_for_assignation()
