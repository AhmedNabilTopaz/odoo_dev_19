# -*- coding: utf-8 -*-
##########################################################################
#
#    Copyright (c) 2017-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
##########################################################################
from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    wk_extra_price = fields.Float('Price Extra', default=0.0)
    
    attr_price_extra = fields.Float(
        compute='_compute_product_price_extra',
        string='Variant Extra Price', 
        digits='Product Price',
        store=False
    )
    
    price_extra = fields.Float(
        'Variant Price Extra', 
        compute='_compute_product_price_extra',
        digits='Product Price',
        store=False,
        help="This is the sum of the extra price of all attributes"
    )

    @api.depends('product_template_attribute_value_ids.price_extra', 'wk_extra_price')
    def _compute_product_price_extra(self):
        for product in self:
            # Calculate the sum of attribute price extras
            price_extra = sum(product.product_template_attribute_value_ids.mapped('price_extra'))
            product.attr_price_extra = price_extra
            product.price_extra = price_extra + product.wk_extra_price