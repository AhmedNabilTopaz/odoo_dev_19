# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    driver_name = fields.Char(
        string='Driver Name',
        help='Name of the driver responsible for this delivery'
    )

    car_number = fields.Char(
        string='Car Number',
        help='Vehicle registration/license plate number'
    )

    national_number = fields.Char(
        string='National Number',
        help='Driver national ID or license number'
    )