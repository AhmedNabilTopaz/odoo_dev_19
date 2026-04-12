# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # FIX: removed states={'done': [('readonly', True)]} — deprecated in Odoo 17+
    # readonly is now handled in view XML via attrs/invisible
    expense_location_id = fields.Many2one(
        comodel_name='stock.location',
        string="Expense Location",
        readonly=False,
        check_company=True,
    )
    is_expense = fields.Boolean(related="picking_type_id.is_expense")

    purchase_order_id = fields.Many2one(
        comodel_name='purchase.order',
        string="Purchase Order",
        compute="_compute_purchase_order",
        store=False,
    )
    show_po_field = fields.Boolean(
        compute="_compute_show_po_field",
        store=False,
    )

    @api.depends('move_ids.purchase_line_id.order_id')
    def _compute_purchase_order(self):
        for rec in self:
            po = rec.move_ids.mapped('purchase_line_id.order_id')
            rec.purchase_order_id = po[0] if po else False

    @api.depends('name', 'purchase_order_id')
    def _compute_show_po_field(self):
        for rec in self:
            is_return = rec.name and "RTN" in rec.name.upper()
            rec.show_po_field = bool(is_return and rec.purchase_order_id)

    def button_validate(self):
        res = super().button_validate()
        for picking in self:
            account_moves = self.env['account.move'].sudo().search([
                ('stock_move_id', 'in', picking.move_ids.ids),
                ('state', '=', 'posted'),
            ])
            for move in account_moves:
                move.sudo()._post_to_discuss_channel()
        return res

    def delete_to_deleteline(self):
        lines_to_delete = self.move_ids_without_package.filtered(lambda l: l.to_delete)
        lines_to_delete.unlink()

    def select_all_todelete(self):
        for line in self.move_ids_without_package:
            line.to_delete = True
