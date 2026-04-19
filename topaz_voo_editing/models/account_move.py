# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from markupsafe import Markup

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    show_r_button = fields.Boolean(default=False, compute='calculate_r_button', store=False, )
    tax_14 = fields.Float(string="VAT", default=0.0, compute="taxes_compute", store=False, )
    table_rate = fields.Float(string="Table Tax", default=0.0, compute="taxes_compute", store=False, )
    withholding_tax = fields.Float(string="Withholding", default=0.0, compute="taxes_compute", store=False, )
    location_id = fields.Many2one(comodel_name="stock.location", string="Source Location",
        compute="_compute_source_location", readonly=True, store=False, )
    expense_location_id = fields.Many2one(comodel_name="stock.location", string="Expense Location",
        compute="_compute_source_location", readonly=True, store=False, )
    picking_source_doc = fields.Char(string="Source Document", compute="_compute_source_location", readonly=True,
        store=False, )
    notes = fields.Html(string="Note", compute="_compute_source_location", readonly=True, store=False, )

    @api.model_create_multi
    def create(self, vals_list):
        # FIX: Odoo 19 uses model_create_multi — accepts list of dicts
        moves = super().create(vals_list)
        for move in moves:
            if move.state == "posted":
                move._post_to_discuss_channel()
        return moves

    def action_post(self):
        res = super().action_post()
        for move in self:
            move._post_to_discuss_channel()
        return res

    def _post_to_discuss_channel(self):
        picking = False
        # stock_move_id only exists when stock_account is installed
        if 'stock_move_id' in self._fields and self.stock_move_id and self.stock_move_id.picking_id:
            picking = self.stock_move_id.picking_id

        # allowed_codes = ["500002", "500012", "500007", "500008"]
        #
        # move_accounts = self.line_ids.mapped("account_id.code")
        #
        # if not any(code in allowed_codes for code in move_accounts) and not (picking and "RTN" in picking.name):
        #     return

        journal_entries_channel = self.env.ref('topaz_voo_editing.channel_journal_notifications', False)
        if not journal_entries_channel:
            return

        journal_entry_link = Markup(f'<a href="#" data-oe-model="account.move" data-oe-id="{self.id}">{self.name}</a>')
        picking_link = Markup(
            f'<a href="#" data-oe-model="stock.picking" data-oe-id="{picking.id}">{picking.name}</a>') if picking else "N/A"
        po_link = Markup(
            f'<a href="#" data-oe-model="purchase.order" data-oe-id="{picking.purchase_id.id}">{picking.purchase_id.name}</a>') if picking and picking.purchase_id else "N/A"

        message = Markup(f"""
            <div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6;">
                <b>📢 New Journal Entry Notification</b><br><br>
                <b>🧾 Journal Entry:</b> {journal_entry_link}<br>
                <b>🚚 Stock Picking:</b> {picking_link}<br>
                <b>📦 Purchase Order:</b> {po_link}
            </div>
        """)

        journal_entries_channel.message_post(body=Markup(message), message_type='comment',
            subtype_xmlid='mail.mt_comment', )

    # FIX: stock_move_id only exists when stock_account is installed.
    # Using empty @api.depends() and checking field existence at runtime avoids
    # "Dependency field not found" errors when stock_account is not yet loaded.
    @api.depends()
    def _compute_source_location(self):
        has_stock_move = 'stock_move_id' in self._fields
        for move in self:
            move.location_id = False
            move.expense_location_id = False
            move.picking_source_doc = False
            move.notes = False
            if has_stock_move:
                stock_move = move.stock_move_id
                if stock_move:
                    move.location_id = stock_move.location_id
                    move.expense_location_id = stock_move.picking_id.expense_location_id
                    move.picking_source_doc = stock_move.picking_id.origin
                    move.notes = stock_move.picking_id.note

    # FIX: @api.onchange is wrong on a compute method — replaced with @api.depends
    @api.depends('show_reset_to_draft_button', 'move_type')
    def calculate_r_button(self):
        for move in self:
            move.show_r_button = bool(
                move.show_reset_to_draft_button and move.move_type in ('out_invoice', 'out_refund'))

    def taxes_compute(self):
        for move in self:
            move.tax_14 = 0.0
            move.table_rate = 0.0
            move.withholding_tax = 0.0
            for line in move.invoice_line_ids:
                for tax in line.tax_ids:
                    if 'T-VAT' in tax.name:
                        move.table_rate += line.price_subtotal * (tax.amount / 100)
                    elif 'VAT' in tax.name:
                        move.tax_14 += line.price_subtotal * (tax.amount / 100)
                    elif 'Withholding' in tax.name:
                        move.withholding_tax += line.price_subtotal * (tax.amount / 100)
                    # FIX: removed print() debug statements — use _logger instead
                    _logger.debug("Tax: %s, Applied Amount: %.2f", tax.name, line.price_subtotal * (tax.amount / 100), )

    def _fix_wrong_sales_accounts(self):
        """Fix wrong account assignments and preserve payment reconciliation."""
        self.ensure_one()

        SERVICE_ACCOUNT_CODE = '400011'
        CASH_SALES_ACCOUNT_CODE = '400000'

        _logger.info("---- START Move %s (%s) ----", self.id, self.name)

        reconciliation_data = {}
        for line in self.line_ids:
            if line.account_id.reconcile and (line.matched_debit_ids or line.matched_credit_ids):
                counterpart_lines = self.env['account.move.line']
                for partial in line.matched_debit_ids:
                    if partial.debit_move_id.id != line.id:
                        counterpart_lines |= partial.debit_move_id
                    if partial.credit_move_id.id != line.id:
                        counterpart_lines |= partial.credit_move_id
                for partial in line.matched_credit_ids:
                    if partial.debit_move_id.id != line.id:
                        counterpart_lines |= partial.debit_move_id
                    if partial.credit_move_id.id != line.id:
                        counterpart_lines |= partial.credit_move_id
                if counterpart_lines:
                    reconciliation_data[line.id] = {'counterpart_ids': counterpart_lines.ids,
                        'account_id': line.account_id.id, }

        if self.state == 'posted':
            self.button_draft()

        lines_to_fix = []
        for line in self.line_ids:
            if not line.product_id:
                continue
            product_type = line.product_id.type
            account_code = line.account_id.code
            if product_type == 'service' and account_code == SERVICE_ACCOUNT_CODE:
                continue
            if product_type in ('consu', 'product') and account_code == SERVICE_ACCOUNT_CODE:
                lines_to_fix.append(line)

        if not lines_to_fix:
            if self.state == 'draft':
                self.action_post()
        else:
            cash_sales_account = self.env['account.account'].search(
                [('code', '=', CASH_SALES_ACCOUNT_CODE), ('company_id', '=', self.company_id.id), ], limit=1)

            if not cash_sales_account:
                raise UserError(_("Cash Sales account (400000) not found."))

            for line in lines_to_fix:
                line.account_id = cash_sales_account

            self.message_post(
                body=_("🛠 Fixed %s line(s): changed from Service Sales (400011) to Cash Sales (400000).") % len(
                    lines_to_fix))
            self.action_post()

        if reconciliation_data:
            for line_id, rec_info in reconciliation_data.items():
                line = self.line_ids.filtered(lambda l: l.id == line_id)
                if not line:
                    continue
                counterpart_lines = self.env['account.move.line'].browse(rec_info['counterpart_ids']).exists()
                if not counterpart_lines:
                    continue
                lines_to_reconcile = line | counterpart_lines
                if len(lines_to_reconcile.mapped('account_id')) > 1:
                    continue
                if not line.account_id.reconcile:
                    continue
                try:
                    unreconciled = lines_to_reconcile.filtered(lambda l: not l.reconciled)
                    if len(unreconciled) > 1:
                        unreconciled.reconcile()
                except Exception as e:
                    _logger.error("Failed to reconcile line %s: %s", line_id, str(e))

        _logger.info("---- END Move %s ----", self.id)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    location_id = fields.Many2one(comodel_name="stock.location", string="Source Location",
        related="move_id.location_id", readonly=True, )
    expense_location_id = fields.Many2one(comodel_name="stock.location", string="Expense Location",
        related="move_id.expense_location_id", readonly=True, )

    # def test(self):  #     """Server action to fix account issues on selected journal entry lines."""  #     _logger.info("=== START Fix Account Issues Server Action ===")  #     moves = self.mapped('move_id')  #     fixed_count = 0  #     error_count = 0  #  #     for move in moves:  #         try:  #             move._fix_wrong_sales_accounts()  #             fixed_count += 1  #         except Exception as e:  #             _logger.error("ERROR processing move %s: %s", move.name, str(e))  #             error_count += 1  #  #     _logger.info("=== END: processed %s, errors %s ===", fixed_count, error_count)  #  #     message = (  #         f'Successfully fixed {fixed_count} journal entry(ies).'  #         if error_count == 0  #         else f'Processed {fixed_count} entry(ies), but {error_count} had errors. Check logs.'  #     )  #     return {  #         'type': 'ir.actions.client',  #         'tag': 'display_notification',  #         'params': {  #             'title': 'Account Fix Completed',  #             'message': message,  #             'type': 'success' if error_count == 0 else 'warning',  #             'sticky': False,  #         },  #     }
