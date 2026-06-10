import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class EzeeOptimusFASConfig(models.Model):
    _name = 'ezee.optimus.fas.config'
    _description = 'eZee Optimus FAS Configuration'
    _rec_name = 'name'

    name = fields.Char(string='Hotel Name', required=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    optimus_company_id = fields.Char(string='Company ID', required=True)
    auth_code = fields.Char(string='Auth Code', required=True)
    base_url = fields.Char(
        string='API URL',
        default='https://app.ipos247.com/app/cloudPOS/sl/interfaceapi/index.php/xeroaccountinterface/eoaccounts',
        required=True,
    )
    username = fields.Char(string='Username')
    password = fields.Char(string='Password', password=True)
    working_date = fields.Date(string='Working Date', readonly=True)
    currency_code = fields.Char(string='Default Currency', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Fallback Journal')
    debt_transfer_journal_id = fields.Many2one('account.journal', string='Debt Transfer Journal')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    active = fields.Boolean(default=True)

    def action_test_connection(self):
        self.ensure_one()
        try:
            sync = self.env['ezee.optimus.sync'].with_context(
                fas_config_id=self.id,
                sync_log_type='outlets',
            ).sudo().create({})
            sync.test_connection()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Successful!',
                    'message': 'Successfully connected to eZee Optimus for %s.' % self.name,
                    'type': 'success',
                    'sticky': False,
                },
            }
        except Exception as e:
            _logger.error('Connection test failed for %s: %s', self.name, e)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Failed',
                    'message': 'Connection test failed for %s. Please verify your credentials and try again.' % self.name,
                    'type': 'danger',
                    'sticky': True,
                },
            }

    def action_get_pull_master(self):
        self.ensure_one()
        try:
            sync = self.env['ezee.optimus.sync'].with_context(
                fas_config_id=self.id,
            ).sudo().create({})

            outlets = sync.fetch_outlets()
            _logger.info('eZee Optimus: %d outlets fetched', len(outlets))

            sync.action_import_config()
            _logger.info('eZee Optimus: config/account mapping imported')

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Pull Master Complete',
                    'message': 'Outlets, account mapping, tax mapping, and available FAS environment data pulled successfully.',
                    'type': 'success',
                    'sticky': False,
                },
            }
        except Exception as e:
            _logger.error('eZee Optimus pull master failed: %s', e)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Pull Master Failed',
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                },
            }
