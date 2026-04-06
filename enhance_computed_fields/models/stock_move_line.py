from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    vendor_ids = fields.Many2many(
        'res.partner',
        string="Vendor",
        compute="_compute_vendor_id",
        store=True,
        readonly=True,
    )

    @api.depends('product_id')
    def _compute_vendor_ids(self):
        if not self:
            return

        # 1️⃣ Get all move line IDs
        move_line_ids = self.ids

        # 2️⃣ Run ONE SQL query for all records (batch)
        self.env.cr.execute("""
            SELECT
                sml.id AS move_line_id,
                psi.partner_id
            FROM stock_move_line sml
            JOIN product_product pp ON sml.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            JOIN product_supplierinfo psi ON psi.product_tmpl_id = pt.id
            WHERE sml.id = ANY(%s)
        """, (move_line_ids,))

        results = self.env.cr.fetchall()

        # 3️⃣ Group النتائج
        vendor_map = {}
        for move_line_id, partner_id in results:
            vendor_map.setdefault(move_line_id, []).append(partner_id)

        # 4️⃣ Assign النتائج
        for line in self:
            partner_ids = vendor_map.get(line.id, [])
            if partner_ids:
                line.vendor_ids = [(6, 0, partner_ids)]
            else:
                line.vendor_ids = [(5, 0, 0)]