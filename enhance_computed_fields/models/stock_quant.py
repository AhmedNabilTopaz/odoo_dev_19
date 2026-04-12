from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    barcode = fields.Char(
                string='Barcode',

        compute='_compute_barcode',
        store=True,
    )

    product_tags = fields.Many2many(
        comodel_name='product.tag',
        string='Product Tags',
        # compute='_compute_product_tags',
        store=True,
    )

    status_topaz = fields.Selection(
        selection=[('enabled', 'Enabled'), ('disabled', 'Disabled')],
        string="Status",
        compute='_compute_status_topaz',
        store=True,
    )

    vendor_ids = fields.Many2many(
         string="Vendors",
        comodel_name='res.partner',
        # compute='_compute_vendor_ids',
        store=True,
    )

    # 🔥 Barcode (SQL)
    @api.depends('product_id')
    def _compute_barcode(self):
        if not self:
            return

        self.env.cr.execute("""
            SELECT sq.id, pt.barcode
            FROM stock_quant sq
            JOIN product_product pp ON sq.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            WHERE sq.id = ANY(%s)
        """, (self.ids,))

        result = dict(self.env.cr.fetchall())

        for rec in self:
            rec.barcode = result.get(rec.id, '') or ''

    # 🔥 Status (SQL)
    @api.depends('product_id')
    def _compute_status_topaz(self):
        self.env.cr.execute("""
            SELECT sq.id, pt.status_topaz
            FROM stock_quant sq
            JOIN product_product pp ON sq.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            WHERE sq.id = ANY(%s)
        """, (self.ids,))

        result = dict(self.env.cr.fetchall())

        for rec in self:
            rec.status_topaz = result.get(rec.id, 'enabled') or 'enabled'

    # 🔥 Vendor_ids (SQL)
    @api.depends('product_id')
    def _compute_vendor_ids(self):
        self.env.cr.execute("""
            SELECT sq.id, psi.partner_id
            FROM stock_quant sq
            JOIN product_product pp ON sq.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            JOIN product_supplierinfo psi ON psi.product_tmpl_id = pt.id
            WHERE sq.id = ANY(%s)
        """, (self.ids,))

        rows = self.env.cr.fetchall()

        vendor_map = {}
        for quant_id, partner_id in rows:
            vendor_map.setdefault(quant_id, []).append(partner_id)

        for rec in self:
            rec.vendor_ids = [(6, 0, vendor_map.get(rec.id, []))]

    # 🔥 Product Tags (SQL)
    @api.depends('product_id')
    def _compute_product_tags(self):
        self.env.cr.execute("""
            SELECT sq.id, rel.product_tag_id
            FROM stock_quant sq
            JOIN product_product pp ON sq.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            JOIN product_tag_product_template_rel rel
                ON rel.product_template_id = pt.id
            WHERE sq.id = ANY(%s)
        """, (self.ids,))

        rows = self.env.cr.fetchall()

        tag_map = {}
        for quant_id, tag_id in rows:
            tag_map.setdefault(quant_id, []).append(tag_id)

        for rec in self:
            rec.product_tags = [(6, 0, tag_map.get(rec.id, []))]