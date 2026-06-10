from odoo import fields, models


class EzeeOptimusSyncLog(models.Model):
    _name = 'ezee.optimus.sync.log'
    _description = 'eZee Optimus Sync Log'
    _order = 'create_date desc'

    hotel_id = fields.Many2one('ezee.optimus.fas.config', string='Hotel', ondelete='set null')
    sync_type = fields.Selection(
        [
            ('outlets', 'Outlets'),
            ('account_mapping', 'Account Mapping'),
            ('sales', 'Sales'),
            ('purchase', 'Purchase'),
            ('config', 'Configuration'),
            ('other', 'Other'),
        ],
        string='Sync Type',
        default='other',
        index=True,
    )
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    status = fields.Selection(
        [
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('partial', 'Partial'),
        ],
        string='Status',
        required=True,
        default='success',
        index=True,
    )
    request_url = fields.Char(string='Request URL')
    request_headers = fields.Text(string='Headers')
    request_payload = fields.Text(string='Payload/Body')
    response_status_code = fields.Integer(string='Response Status Code')
    response_body = fields.Text(string='Response Body')
    error_message = fields.Text(string='Error Messages')
