from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_round, float_is_zero, float_compare
from odoo.exceptions import UserError
class StockMove(models.Model):
    _inherit = 'stock.move'
    def _get_price_unit(self):
        """ Returns the unit price for the move"""
        self.ensure_one()
        if self._should_ignore_pol_price():
            return super(StockMove, self)._get_price_unit()
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        line = self.purchase_line_id
        order = line.order_id
        received_qty = line.qty_received
        if self.state == 'done':
            received_qty -= self.product_uom._compute_quantity(self.quantity_done, line.product_uom,
                                                               rounding_method='HALF-UP')
        if line.product_id.purchase_method == 'purchase' and float_compare(line.qty_invoiced, received_qty,
                                                                           precision_rounding=line.product_uom.rounding) > 0:
            move_layer = line.move_ids.sudo().stock_valuation_layer_ids
            invoiced_layer = line.sudo().invoice_lines.stock_valuation_layer_ids
            # value on valuation layer is in company's currency, while value on invoice line is in order's currency
            receipt_value = 0
            for layer in move_layer:
                if not layer._should_impact_price_unit_receipt_value():
                    continue
                receipt_value += layer.currency_id._convert(
                    layer.value, order.currency_id, order.company_id, layer.create_date, round=False)
            if invoiced_layer:
                receipt_value += sum(invoiced_layer.mapped(lambda l: l.currency_id._convert(
                    l.value, order.currency_id, order.company_id, l.create_date, round=False)))
            total_invoiced_value = 0
            invoiced_qty = 0
            for invoice_line in line.sudo().invoice_lines:
                if invoice_line.move_id.state != 'posted':
                    continue
                # Discount applied on bill prior to reception
                if invoice_line.discount and not move_layer:
                    price_unit = invoice_line.price_subtotal / invoice_line.quantity
                else:
                    price_unit = invoice_line.price_unit
                if invoice_line.tax_ids:
                    invoice_line_value = invoice_line.tax_ids.with_context(round=False).compute_all(
                        price_unit, currency=invoice_line.currency_id, quantity=invoice_line.quantity)['total_void']
                else:
                    invoice_line_value = price_unit * invoice_line.quantity
                total_invoiced_value += invoice_line.currency_id._convert(
                    invoice_line_value, order.currency_id, order.company_id, invoice_line.move_id.invoice_date,
                    round=False)
                invoiced_qty += invoice_line.product_uom_id._compute_quantity(invoice_line.quantity,
                                                                              line.product_id.uom_id)
            # TODO currency check
            remaining_value = total_invoiced_value - receipt_value
            # TODO qty_received in product uom
            remaining_qty = invoiced_qty - line.product_uom._compute_quantity(received_qty, line.product_id.uom_id)
            if order.currency_id != order.company_id.currency_id and remaining_value and remaining_qty:
                # will be rounded during currency conversion
                price_unit = remaining_value / remaining_qty
            elif remaining_value and remaining_qty:
                price_unit = float_round(remaining_value / remaining_qty, precision_digits=price_unit_prec)
            else:
                price_unit = line._get_gross_price_unit()
        else:
            price_unit = line._get_gross_price_unit()
        if order.currency_id != order.company_id.currency_id:
            # The date must be today, and not the date of the move since the move move is still
            # in assigned state. However, the move date is the scheduled date until move is
            # done, then date of actual move processing. See:
            # https://github.com/odoo/odoo/blob/2f789b6863407e63f90b3a2d4cc3be09815f7002/addons/stock/models/stock_move.py#L36
            invoice = order.invoice_ids.sorted('create_date')[0] if order.invoice_ids else None
            # if order.rate_date:
            if invoice:
                convert_date=invoice.invoice_date
                # convert_date = order.rate_date

            else:
               convert_date = fields.Date.context_today(self)

               # use currency rate at bill date when invoice before receipt
            if float_compare(line.qty_invoiced, received_qty, precision_rounding=line.product_uom.rounding) > 0:
                convert_date = max(
                    line.sudo().invoice_lines.move_id.filtered(lambda m: m.state == 'posted').mapped('invoice_date'),
                    default=convert_date)
            price_unit = order.currency_id._convert(
                price_unit, order.company_id.currency_id, order.company_id, convert_date, round=False)
        return price_unit

    # def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id,
    #                                cost):
    #     self.ensure_one()
    #     valuation_partner_id = self._get_partner_id_for_valuation_lines()
    #     move_ids = self._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id, svl_id, description)
    #     svl = self.env['stock.valuation.layer'].browse(svl_id)
    #     purchase_orders = self.picking_id.move_ids_without_package.mapped("purchase_line_id.order_id")
    #     if purchase_orders:
    #         date = purchase_orders[0].rate_date
    #     else:
    #         if self.env.context.get('force_period_date'):
    #             date = self.env.context.get('force_period_date')
    #         elif svl.account_move_line_id:
    #             date = svl.account_move_line_id.date
    #         else:
    #             date = fields.Date.context_today(self)
    #     return {
    #         'journal_id': journal_id,
    #         'line_ids': move_ids,
    #         'partner_id': valuation_partner_id,
    #         'date': date,
    #         'ref': description,
    #         'stock_move_id': self.id,
    #         'stock_valuation_layer_ids': [(6, None, [svl_id])],
    #         'move_type': 'entry',
    #         'is_storno': self.env.context.get('is_returned') and self.env.company.account_storno,
    #     }