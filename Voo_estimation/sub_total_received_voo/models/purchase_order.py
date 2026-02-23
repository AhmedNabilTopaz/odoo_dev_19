# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PurchaseOrder(models.Model):
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

    @api.depends(
        "order_line.qty_received",
        "order_line.price_unit",
        "order_line.discount",
        "order_line.tax_ids"
    )
    def _compute_amount_received_total(self):
        """
        Compute total received amounts by aggregating line amounts.
        This includes untaxed amount, tax amount, and total with taxes.
        """
        for order in self:
            total_untaxed = 0.0
            total_tax = 0.0
            total_with_tax = 0.0
            
            # Sum up amounts from all order lines
            for line in order.order_line:
                total_untaxed += line.sub_total_received
                total_tax += line.price_tax_received
                total_with_tax += line.price_total_received
            
            # Update the computed fields
            order.amount_received_untaxed = total_untaxed
            order.amount_received_tax = total_tax
            order.amount_received_total = total_with_tax
