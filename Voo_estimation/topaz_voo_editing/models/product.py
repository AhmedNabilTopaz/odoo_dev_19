# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    barcode = fields.Char(
        string="Barcode",
        related='product_tmpl_id.barcode',
        readonly=True,
    )
    # FIX: taxes_id renamed to tax_ids in Odoo 19
    tax_ids = fields.Many2many(
        string="Tax",
        related='product_tmpl_id.taxes_id',
        readonly=True,
    )
    tax_name = fields.Char(
        string="VAT class",
        related='tax_ids.name',
        readonly=True,
    )


class Product(models.Model):
    _inherit = "product.template"

    status_topaz = fields.Selection(
        selection=[('enabled', 'Enabled'), ('disabled', 'Disabled')],
        default='enabled',
        string='Status',
        required=True,
    )

    def action_convert_variants_to_products(self):
        for template in self:
            variants = template.product_variant_ids
            if len(variants) <= 1:
                raise UserError(_("No variants to convert."))

            for variant in variants:
                variant_attributes = ", ".join(
                    variant.product_template_variant_value_ids.mapped('name')
                )
                new_barcode = f"{variant.barcode}-{variant.id}" if variant.barcode else None
                self.env['product.template'].create({
                    'name': f"{variant.name} - {variant_attributes}",
                    'type': template.type,
                    'uom_id': template.uom_id.id,
                    'uom_po_id': template.uom_po_id.id,
                    'categ_id': template.categ_id.id,
                    'list_price': variant.lst_price,
                    'standard_price': variant.standard_price,
                    'barcode': new_barcode,
                    'default_code': variant.default_code,
                })
                variant.write({'active': False})

            template.write({'active': True})
        return True

    # FIX: original methods set boolean True/False on a Selection field
    # Corrected to set the proper Selection string values
    def set_status_enabled(self):
        for product in self:
            product.status_topaz = 'enabled'

    def set_status_disabled(self):
        for product in self:
            product.status_topaz = 'disabled'
