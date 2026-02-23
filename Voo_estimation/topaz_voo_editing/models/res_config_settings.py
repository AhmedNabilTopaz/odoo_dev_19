# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vending_machine_id = fields.Many2one(
        comodel_name='vending.machine',
        string='Vending Machine',
        related='pos_config_id.vending_machine_id',
        readonly=False,
    )
