# -*- coding: utf-8 -*-
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
        comodel_name='res.partner',
        string="Vendors",
        # compute='_compute_vendor_ids', 
        store=True,
    )

    @api.depends('product_id.product_tmpl_id.product_tag_ids')
    def _compute_product_tags(self):
        for record in self:
            if record.product_id and record.product_id.product_tmpl_id:
                record.product_tags = record.product_id.product_tmpl_id.product_tag_ids
            else:
                record.product_tags = [(5, 0, 0)]

    @api.depends('product_id.product_tmpl_id.barcode')
    def _compute_barcode(self):
        for record in self:
            record.barcode = record.product_id.product_tmpl_id.barcode or ''

    @api.depends('product_id.product_tmpl_id.status_topaz')
    def _compute_status_topaz(self):
        for record in self:
            record.status_topaz = record.product_id.status_topaz or 'enabled'

    @api.depends('product_id.product_tmpl_id.seller_ids.partner_id')
    def _compute_vendor_ids(self):
        for record in self:
            sellers = record.product_id.seller_ids
            partners = sellers.mapped('partner_id')
            record.vendor_ids = [(6, 0, partners.ids)] if partners else [(5, 0, 0)]
