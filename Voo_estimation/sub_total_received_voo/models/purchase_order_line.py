# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    sub_total_received = fields.Monetary(
        string="Subtotal Received",
        compute="_compute_amount_received",
        store=True,
        currency_field="currency_id",
    )

    product_barcode = fields.Char(
        string="Barcode",
        related="product_id.barcode",
        store=True,
        readonly=True,
    )

    price_tax_received = fields.Monetary(
        string="Tax Received",
        compute="_compute_amount_received",
        store=True,
        currency_field="currency_id",
    )

    price_total_received = fields.Monetary(
        string="Total Received",
        compute="_compute_amount_received",
        store=True,
        currency_field="currency_id",
    )

    @api.depends('qty_received', 'price_unit', 'tax_ids', 'discount')
    def _compute_amount_received(self):
        """
        Compute received amounts using qty_received instead of product_qty.

        Uses the Odoo 19 tax API:
          1. _prepare_base_line_for_taxes_computation()  — build the base-line dict
          2. AccountTax._add_tax_details_in_base_lines() — attach tax breakdown
          3. AccountTax._round_base_lines_tax_details()  — apply rounding
        Then read tax_details_per_record for the final amounts.
        """
        AccountTax = self.env['account.tax']

        for line in self:
            # Step 1 – build a base-line dict but override qty with qty_received
            base_line = line._prepare_base_line_for_taxes_computation()
            base_line['quantity'] = line.qty_received

            # Step 2 & 3 – compute and round tax details (mutates base_line in-place)
            AccountTax._add_tax_details_in_base_lines([base_line], line.company_id)
            AccountTax._round_base_lines_tax_details([base_line], line.company_id)

            # Step 4 – read results
            tax_details = base_line.get('tax_details_per_record', {})
            # tax_details is a dict keyed by the record; grab the first (and only) entry
            record_totals = next(iter(tax_details.values()), {}) if tax_details else {}

            amount_untaxed = record_totals.get('base_amount_currency', 0.0)
            amount_tax     = record_totals.get('tax_amount_currency',  0.0)

            line.sub_total_received  = amount_untaxed
            line.price_tax_received  = amount_tax
            line.price_total_received = amount_untaxed + amount_tax