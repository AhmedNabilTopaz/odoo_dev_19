from odoo import api, fields, models

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    sub_total_received = fields.Monetary(
        string="SubTotal Received",
        compute="_compute_amount_received",
        store=True,
        currency_field="currency_id",
    )
    product_barcode = fields.Char(
        string="Barcode",
        related="product_id.barcode",
        store=True,  # optional: makes it stored in the database
        readonly=True
    )
    price_tax_received=fields.Monetary(string="Price Tax Received",readonly=1)
    price_total_received = fields.Monetary(string="Price total Received", readonly=1)

    @api.depends('qty_received', 'price_unit', 'discount')
    def _compute_amount_received(self):
        if not self:
            return

        self.env.cr.execute("""
            SELECT
                pol.id,
                pol.qty_received,
                pol.price_unit,
                COALESCE(pol.discount, 0)
            FROM purchase_order_line pol
            WHERE pol.id = ANY(%s)
        """, (self.ids,))

        for line_id, qty, price, discount in self.env.cr.fetchall():
            subtotal = qty * price * (1 - discount / 100.0)

            line = self.browse(line_id)

            # ⚠️ taxes still ORM (can't fully SQL easily)
            taxes = line.taxes_id.compute_all(
                price,
                quantity=qty,
                currency=line.currency_id,
                product=line.product_id,
                partner=line.order_id.partner_id,
            )

            line.sub_total_received = subtotal
            line.price_tax_received = taxes['total_included'] - taxes['total_excluded']
            line.price_total_received = taxes['total_included']

    def _convert_to_tax_base_line_dict_received(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method. """
        self.ensure_one()
        # subtotal = self.price_unit * self.qty_received * (1 - (self.discount or 0.0) / 100.0)
        vals= self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.order_id.partner_id,
            currency=self.order_id.currency_id,
            product=self.product_id,
            taxes=self.taxes_id,
            price_unit=self.price_unit,
            quantity=self.qty_received,  # 🔑 use qty_received instead of product_qty
            price_subtotal=self.price_unit * self.qty_received,  # 🔑 base subtotal on qty_received
            # discount=self.discount
        )
        vals.update({"discount": self.discount})
        return vals
