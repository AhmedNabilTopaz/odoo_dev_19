from odoo import api, fields, models


class EzeeOptimusTaxMapping(models.Model):
    _name = 'ezee.optimus.tax.mapping'
    _description = 'eZee Optimus Tax Mapping'
    _rec_name = 'tax_name'

    hotel_id = fields.Many2one(
        'ezee.optimus.fas.config',
        string='Hotel',
        required=True,
        ondelete='cascade',
    )
    tax_id = fields.Char(string='Tax ID', required=True)
    tax_name = fields.Char(string='Tax Name', required=True)
    odoo_tax_id = fields.Many2one(
        'account.tax',
        string='Odoo Tax'
        # domain="[('company_id', 'in', [False/, company_id])]",
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        (
            'unique_tax_mapping_per_hotel_company',
            'UNIQUE(hotel_id, tax_id, company_id)',
            'Each Optimus tax can only be mapped once per hotel and company.',
        )
    ]

    @api.onchange('hotel_id')
    def _onchange_hotel_id(self):
        if self.hotel_id:
            self.company_id = self.hotel_id.company_id
