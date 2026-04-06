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

    @api.depends('order_line.sub_total_received', 'order_line.price_tax_received')
    def _compute_amount_received_total(self):
        if not self:
            return

        self.env.cr.execute("""
            SELECT
                po.id,
                COALESCE(SUM(pol.sub_total_received), 0),
                COALESCE(SUM(pol.price_tax_received), 0),
                COALESCE(SUM(pol.price_total_received), 0)
            FROM purchase_order po
            LEFT JOIN purchase_order_line pol
                ON pol.order_id = po.id
            WHERE po.id = ANY(%s)
            GROUP BY po.id
        """, (self.ids,))

        result = {row[0]: row[1:] for row in self.env.cr.fetchall()}

        for order in self:
            untaxed, tax, total = result.get(order.id, (0, 0, 0))
            order.amount_received_untaxed = untaxed
            order.amount_received_tax = tax
            order.amount_received_total = total