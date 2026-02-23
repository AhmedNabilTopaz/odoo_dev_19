# -*- coding: utf-8 -*-

from odoo import models, _, api
from odoo.exceptions import UserError, ValidationError


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    @api.constrains('default_location_dest_id')
    def _check_default_location(self):
        for record in self:
            if record.code == 'mrp_operation' and record.default_location_dest_id.scrap_location:
                print("MRP OPERATION")
                # raise ValidationError(_("You cannot set a scrap location as the destination location for a manufacturing type operation."))