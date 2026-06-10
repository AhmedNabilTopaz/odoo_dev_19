from odoo import fields, models


class EzeeOptimusAccountMapping(models.Model):
    _name = 'ezee.optimus.account.mapping'
    _description = 'eZee Optimus Account Mapping'

    hotel_id = fields.Many2one(
        'ezee.optimus.fas.config',
        string='Hotel',
        required=True,
        ondelete='cascade',
    )
    header_id = fields.Integer(
        string='Reference ID(headerid)', required=True,
        help='Corresponds to headerid in the Financial Accounts API (1–32)'
    )
    header_name = fields.Char(string='Reference (header)')
    account_group_id = fields.Many2one(
        'account.group',
        string='Odoo Account Group',
    )
    account_id = fields.Many2one(
        'account.account',
        string='Odoo Account',
        help='Default Odoo GL account for this eZee header',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    line_ids = fields.One2many(
        'ezee.optimus.account.mapping.line',
        'mapping_id',
        string='Detailed Lines',
    )

    _sql_constraints = [
        ('unique_header_per_hotel', 'UNIQUE(header_id, hotel_id)',
         'Each eZee account header can only be mapped once per hotel.')
    ]


class EzeeOptimusAccountMappingLine(models.Model):
    _name = 'ezee.optimus.account.mapping.line'
    _description = 'eZee Optimus Account Mapping Line'

    mapping_id = fields.Many2one(
        'ezee.optimus.account.mapping',
        string='Account Mapping',
        required=True,
        ondelete='cascade',
    )
    hotel_id = fields.Many2one(
        'ezee.optimus.fas.config',
        string='Hotel',
        related='mapping_id.hotel_id',
        store=True,
        readonly=True,
    )
    desc_type_id = fields.Integer(
        string='Sub Reference ID (descriptiontypeunkid)',
        help='descriptiontypeunkid from API (1=Single Ledger, 2=sub-type...)'
    )
    desc_type_name = fields.Char(string='Sub Reference (descriptiontype)')
    ezee_desc_unk_id = fields.Char(
        string='Entity ID (descriptionunkid)',
        help='descriptionunkid — used as sub_ref2_value in transactions',
    )
    description = fields.Char(string='Entity (description)')
    account_id = fields.Many2one(
        'account.account',
        string='Odoo Account Override',
        help='Optional override account for this specific line item',
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='mapping_id.company_id',
        store=True,
        readonly=True,
    )

    _sql_constraints = [
        ('unique_desc_per_mapping', 'UNIQUE(mapping_id, ezee_desc_unk_id)',
         'Each description ID must be unique per account mapping.')
    ]
