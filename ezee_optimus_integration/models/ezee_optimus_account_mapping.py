from odoo import fields, models

class EzeeOptimusAccountMapping(models.Model):
    _name = 'ezee.optimus.account.mapping'
    _description = 'eZee Optimus → Odoo Account Mapping'

    header_id = fields.Integer(
        string='eZee Header ID', required=True,
        help='Corresponds to headerid in the Financial Accounts API (1–32)'
    )
    header_name = fields.Char(string='Header Name')  # e.g. POS REVENUE
    desc_type_id = fields.Integer(
        string='Description Type ID',
        help='descriptiontypeunkid from API (1=Single Ledger, 2=sub-type...)'
    )
    desc_type_name = fields.Char(string='Description Type')  # e.g. Tax
    ezee_desc_unk_id = fields.Char(
        string='eZee Description ID',
        help='descriptionunkid — used as sub_ref2_value in transactions'
    )
    description = fields.Char(string='eZee Description')  # e.g. VAT 15%
    odoo_account_id = fields.Many2one(
        'account.account',
        string='Odoo Account',
        help='The Odoo GL account to debit/credit for this eZee head'
    )

    _sql_constraints = [
        ('unique_mapping', 'UNIQUE(header_id, desc_type_id, ezee_desc_unk_id)',
         'Each eZee account head must be mapped once only.')
    ]
