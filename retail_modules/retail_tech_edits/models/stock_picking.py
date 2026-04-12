# -*- coding: utf-8 -*-

from odoo import models, _, api , fields
from odoo.exceptions import UserError, ValidationError


# Validate Purchase Order Quantity
class StockPicking(models.Model):
    _inherit = 'stock.picking'

    x_studio_customer = fields.Many2one('res.partner', string='Customer')

    def button_validate(self):
        if self.picking_type_id.code == 'incoming':  # Only apply to receipts
            for move in self.move_ids_without_package:
                if move.purchase_line_id:  # Check if it's related to a Purchase Order
                    purchase_order = move.purchase_line_id.order_id
                    # Check if the related bill is created and validated
                    bills = self.env['account.move'].search([
                        ('purchase_id', '=', purchase_order.id),
                        ('move_type', '=', 'in_invoice'),
                        ('state', '=', 'posted')
                    ])
                    if not bills:
                        raise UserError(
                            _('You cannot validate this transfer because the bill for the related Purchase Order is not created and validated.'))

        return super(StockPicking, self).button_validate()
    # @api.model
    # def _assign_rate_date_to_accounting_entries(self, stock_moves, rate_date):
    #     """Assign rate_date to valuation date and accounting date of journal entries."""
    #     account_moves = self.env["account.move"].search([("stock_move_id", "in", stock_moves.ids)])
    #     for move in account_moves:
    #         move.date = rate_date  # Accounting Date
    #         move.line_ids.write({"date": rate_date})  # Update line items
    #         move._compute_tax_totals()  # Recalculate taxes if needed
    #
    # def button_validate(self):
    #     """Override validation to assign rate_date."""
    #     res = super().button_validate()
    #
    #     for picking in self:
    #         purchase_orders  = picking.move_ids_without_package.mapped("purchase_line_id.order_id")
    #         if purchase_orders:
    #             rate_date = purchase_orders[0].rate_date
    #             if rate_date:
    #                 self._assign_rate_date_to_accounting_entries(picking.move_ids_without_package, rate_date)
    #
    #     return res

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    @api.constrains('default_location_dest_id')
    def _check_default_location(self):
        for record in self:
            if record.code == 'mrp_operation' and record.default_location_dest_id.scrap_location:
                print("MRP OPERATION")
                # raise ValidationError(_("You cannot set a scrap location as the destination location for a manufacturing type operation."))