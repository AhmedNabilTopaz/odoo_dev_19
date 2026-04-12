# -*- coding: utf-8 -*-
from odoo import fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    purchase_date = fields.Datetime(string='Purchase Time')


class PosConfig(models.Model):
    _inherit = 'pos.config'

    vending_machine_id = fields.Many2one(
        comodel_name='vending.machine',
        string='Vending Machine',
        help='Vending machine linked to this Point of Sale.',
    )
