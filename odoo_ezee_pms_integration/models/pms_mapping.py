from odoo import models, fields

class PMSAccountMapping(models.Model):
    _name = 'pms.account.mapping'
    _description = 'PMS Account Mapping'

    hotel_id = fields.Many2one('pms.credentials', string='Hotel', required=True)
    # hotel_id_code=fields.Char(related='hotel_id.hotel_code', string='Hotel Code', readonly=True)
    # pms_account_id = fields.Char(string='Entity ID (descriptionunkid)', required=True)
    # pms_account_name = fields.Char(string='Entity (description)')
    pms_account_header_id=fields.Integer(string='Reference ID(headerid)')
    pms_account_header_name=fields.Char(string='Reference (header)')
    # pms_account_type_id = fields.Integer(string='Sub Reference ID(descriptiontypeunkid)')
    # pms_account_type_name = fields.Char(string='Sub Reference (descriptiontype)')
    account_group_id = fields.Many2one('account.group', string='Odoo Account Group')
    account_id = fields.Many2one('account.account', string='Odoo Account')
    company_id = fields.Many2one('res.company', string='Company')
    line_ids = fields.One2many(
        'pms.account.mapping.line',
        'mapping_id',
        string='Detailed Lines',
    )


class PMSAccountMappingLine(models.Model):
    _name = 'pms.account.mapping.line'
    _description = 'PMS Account Mapping Line'

    mapping_id = fields.Many2one(
        'pms.account.mapping',
        string='Account Mapping',
        required=True,
        ondelete='cascade',
    )
    hotel_id = fields.Many2one(
        'pms.credentials',
        string='Hotel',
        related='mapping_id.hotel_id',
        store=True,
        readonly=True,
    )
    pms_account_id = fields.Char(string='Entity ID (descriptionunkid)', required=True)
    pms_account_name = fields.Char(string='Entity (description)')
    pms_account_type_id = fields.Char(string='Sub Reference ID (descriptiontypeunkid)')
    pms_account_type_name = fields.Char(string='Sub Reference (descriptiontype)')
    account_group_id = fields.Many2one('account.group', string='Odoo Account Group')
    account_id = fields.Many2one('account.account', string='Odoo Account')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='mapping_id.company_id',
        store=True,
        readonly=True,
    )

    _sql_constraints = [
        (
            'pms_account_mapping_line_unique',
            'unique(mapping_id, pms_account_id)',
            'The PMS account line must be unique per account mapping.',
        ),
    ]


class PMSTaxMapping(models.Model):
    _name = 'pms.tax.mapping'
    _description = 'PMS Tax Mapping'

    hotel_id = fields.Many2one('pms.credentials', string='Hotel', required=True)
    pms_tax_id = fields.Char(string='PMS Tax ID', required=True)
    pms_tax_name = fields.Char(string='PMS Tax Name')
    tax_id = fields.Many2one('account.tax', string='Odoo Tax')
    company_id = fields.Many2one('res.company', string='Company')

class PMSPaymentMapping(models.Model):
    _name = 'pms.payment.mapping'
    _description = 'PMS Payment Method Mapping'

    hotel_id = fields.Many2one('pms.credentials', string='Hotel', required=True)
    pms_payment_id = fields.Char(string='PMS Payment ID')
    pms_payment_type = fields.Char(string='PMS Payment Type', required=True)
    journal_id = fields.Many2one('account.journal', string='Odoo Journal')
