from odoo import models, fields, api


class SubTotalReceived(models.Model):
    _inherit = "purchase.order"

    amount_received_total = fields.Monetary(
        string="Total Received (Incl. Taxes)",
        compute="_compute_amount_received_total",
        store=True,
        currency_field="currency_id",
    )
    amount_received_tax = fields.Monetary(
        string="Taxes Received",
        compute="_compute_amount_received_total",
        store=True,
        currency_field="currency_id",
    )
    amount_received_untaxed = fields.Monetary(
        string="Untaxed Received",
        compute="_compute_amount_received_total",
        store=True,
        currency_field="currency_id",
    )

    @api.depends("order_line.qty_received", "order_line.price_unit", "order_line.discount", "order_line.taxes_id")
    def _compute_amount_received_total(self):
        for order in self:
            total = 0.0
            untaxed = 0.0
            tax = 0.0
            # order.amount_received_total = 0.0

            # loop on each line
            for line in order.order_line:
                untaxed += line.sub_total_received
                tax += line.price_tax_received
                total += line.price_total_received
                order.amount_received_total = total

                # order.amount_received_total=line.price_total_received

            # for line in order.order_line:
            #     # Apply discount on unit price
            #     price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            #
            #     # Compute with taxes based on qty_received
            #     taxes_res = line.taxes_id._origin.compute_all(
            #         price_unit,
            #         currency=order.currency_id,
            #         quantity=line.qty_received,
            # F       product=line.product_id,
            #         partner=order.partner_id,
            #     )
            #
            #     # Add tax-included total
            #     total += taxes_res["total_included"]
            #
            # order.amount_received_total = total

            # New fields for received totals (untaxed & tax)
            order.amount_received_untaxed = untaxed
            order.amount_received_tax = tax
            order.amount_received_total = total
