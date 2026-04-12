from odoo import fields, models

class SaleReport(models.Model):
    _inherit = "sale.report"
    _auto = False

    product_uom_qty = fields.Float("Ordered Quantity", readonly=True)
    qty_delivered = fields.Float("Delivered Quantity", readonly=True)
    qty_invoiced = fields.Float("Invoiced Quantity", readonly=True)
    pricelist_id = fields.Many2one("product.pricelist", string="Pricelist", readonly=True)
    invoice_status = fields.Selection([
        ('invoiced', 'Fully Invoiced'),
        ('to invoice', 'To Invoice'),
        ('no', 'Nothing to Invoice'),
    ], string="Invoice Status", readonly=True)

    def _select(self):
        return super()._select() + """,
            s.pricelist_id,
            s.categ_id,
            l.product_uom_qty,
            l.qty_delivered,
            l.qty_invoiced,
            l.invoice_status
        """

    def _group_by(self):
        return super()._group_by() + """,
            s.pricelist_id,
            s.categ_id,
            l.product_uom_qty,
            l.qty_delivered,
            l.qty_invoiced,
            l.invoice_status
        """
