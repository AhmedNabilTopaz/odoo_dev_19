# -*- coding: utf-8 -*-
from odoo import fields, models


class VendingMachine(models.Model):
    _name = 'vending.machine'
    _description = 'Vending Machine'
    _order = "name"

    name = fields.Char(string="Machine Name", required=True)
    location = fields.Char(string="Location")
    active = fields.Boolean(string="Active", default=True)
