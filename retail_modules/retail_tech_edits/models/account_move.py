from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'

    # def _get_invoice_rate(self):
    #     for move in self:
    #         if move.move_type in ('in_invoice', 'in_refund'):
    #             # Check if linked to a PO
    #             purchase_lines = move.line_ids.purchase_line_id
    #             if purchase_lines:
    #                 order = purchase_lines[0].order_id
    #                 if order.rate_date:
    #                     date = order.rate_date
    #                     currency = move.currency_id
    #                     company = move.company_id
    #                     if currency != company.currency_id:
    #                         rate = currency._convert(
    #                             1,
    #                             company.currency_id,
    #                             company,
    #                             date,
    #                             round=False
    #                         )
    #                         move.currency_rate = 1 / rate
    #                         continue
    #         super(AccountMove, move)._get_invoice_rate()