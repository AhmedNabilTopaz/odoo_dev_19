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

    @api.depends('qty_received', 'price_unit', 'taxes_id','discount')
    def _compute_amount_received(self):
        for line in self:
            tax_results = self.env['account.tax']._compute_taxes([line._convert_to_tax_base_line_dict_received()])
            totals = list(tax_results['totals'].values())[0]
            amount_untaxed = totals['amount_untaxed']
            amount_tax = totals['amount_tax']

            line.update({
                'sub_total_received': amount_untaxed,
                'price_tax_received': amount_tax,
                'price_total_received': amount_untaxed +amount_tax,
            })

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
