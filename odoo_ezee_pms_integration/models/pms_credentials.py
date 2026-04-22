from odoo import models, fields, api

class PMSCredentials(models.Model):
    _name = 'pms.credentials'
    _description = 'PMS Credentials'

    name = fields.Char(string='Hotel Name', required=True)
    hotel_code = fields.Char(string='Hotel Code', required=True)
    username = fields.Char(string='Username', required=True)
    password = fields.Char(string='Password', required=True, password=True)
    auth_code = fields.Char(string='Auth Code', readonly=True)
    working_date = fields.Date(string='Working Date', readonly=True)
    currency_code = fields.Char(string='Default Currency', readonly=True)
    
    journal_id = fields.Many2one('account.journal', string='Fallback Journal')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    debt_transfer_journal_id = fields.Many2one('account.journal', string='Debt Transfer Journal')
    active = fields.Boolean(default=True)

    def action_test_connection(self):
        """Test connection to eZee PMS API and return user notification"""
        from ..services.ezee_api_service import eZeeAPIService
        from odoo.exceptions import UserError
        
        service = eZeeAPIService(self)
        success, message = service.login()

        if success:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Successful!',
                    'message': f'Successfully connected to eZee PMS for {self.name}.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Failed',
                    'message': f'Error: {message}',
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_scheduled_sync(self):
        """Called by cron to sync all active hotels for the previous day"""
        from odoo.fields import Date
        from datetime import timedelta
        yesterday = Date.today() - timedelta(days=1)
        
        for hotel in self:
            env = self.env(context={
                **self.env.context,
                'allowed_company_ids': [hotel.company_id.id],
                'force_company': hotel.company_id.id,
            })
            wizard = env['pms.sync.wizard'].create({
                'hotel_ids': [(4, hotel.id)],
                'from_date': yesterday,
                'to_date': yesterday,
            })
            wizard.action_sync()

    def action_pull_config(self):
        """Fetch master data/configuration values from eZee PMS"""
        from ..services.ezee_api_service import eZeeAPIService
        service = eZeeAPIService(self)
        
        # Ensure logged in
        if not self.auth_code:
            service.login()
        
        data = service.fetch_data('config')
        
        if data:
            self._process_config_data(data)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Configuration Pulled',
                    'message': 'Master data successfully pulled and mapping tables updated.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Failed to Pull Configuration',
                    'message': 'Check Sync Logs for details.',
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def _process_config_data(self, data):
        """Parse configuration data and populate mapping models"""
        if not data:
            return

        records = []
        if isinstance(data, dict):
            records = data.get('data', [])
        elif isinstance(data, list):
            records = data

        if not isinstance(records, list):
            return

        for rec in records:
            desc_type = str(rec.get('descriptiontype', '')).upper()
            desc_type_unk_id = rec.get('descriptiontypeunkid')
            desc_unk_id = str(rec.get('descriptionunkid') or '')
            desc_name = rec.get('description')
            header_id=int(rec.get('headerid'))
            header_name=rec.get('header')

            if not header_id:
                continue

            if str.upper(desc_type) == 'TAX' or str.upper(desc_type)=='TAXES':
                mapping = self.env['pms.tax.mapping'].search([
                ('pms_tax_id', '=', str(desc_unk_id)),('hotel_id','=',self.id)], limit=1)

                vals = {
                    'pms_tax_name': desc_name,
                    'hotel_id': self.id,
                    'pms_tax_id': str(desc_unk_id),
                    'company_id': self.company_id.id,
                }
                
                if mapping:
                    mapping.write({'pms_tax_name': desc_name})
                else:
                    self.env['pms.tax.mapping'].create(vals)
            else:
                mapping = self.env['pms.account.mapping'].search([
                    ('pms_account_header_id', '=', header_id),
                    ('hotel_id','=',self.id)
                ], limit=1)

                if not mapping:
                    mapping = self.env['pms.account.mapping'].create({
                        'pms_account_header_id': header_id,
                        'pms_account_header_name': header_name,
                        'hotel_id': self.id,
                        'company_id': self.company_id.id,
                    })

                if not desc_unk_id:
                    continue

                mapping_line = self.env['pms.account.mapping.line'].search([
                    ('mapping_id', '=', mapping.id),
                    ('pms_account_id', '=', desc_unk_id),('hotel_id','=',self.id)
                ], limit=1)
                if not mapping_line:
                    mapping_line = self.env['pms.account.mapping.line'].create({
                        'mapping_id': mapping.id,
                        'pms_account_id': desc_unk_id,
                        'pms_account_name': desc_name,
                        'pms_account_type_id': desc_type_unk_id,
                        'pms_account_type_name': rec.get('descriptiontype'),
                    })
                    mapping.write({
                        'line_ids': [(4, mapping_line.id)]
                    })
                else:
                     mapping.write({
                        'line_ids': [(4, mapping_line.id)]
                    })
            # elif 'TAX' in desc_type:
            #     mapping = self.env['pms.tax.mapping'].search([
            #         ('hotel_id', '=', self.id),
            #         ('pms_tax_id', '=', str(unk_id))
            #     ], limit=1)
                
            #     vals = {
            #         'pms_tax_name': name,
            #         'hotel_id': self.id,
            #         'pms_tax_id': str(unk_id),
            #     }
                
            #     if mapping:
            #         mapping.write({'pms_tax_name': name})
            #     else:
            #         self.env['pms.tax.mapping'].create(vals)

            # elif desc_type == 'PAYMENT TYPE':
            #     if str(unk_id) == '1' and name == 'Payment Type':
            #         continue
                    
            #     mapping = self.env['pms.payment.mapping'].search([
            #         ('hotel_id', '=', self.id),
            #         '|',
            #         ('pms_payment_id', '=', str(unk_id)),
            #         ('pms_payment_type', '=', name)
            #     ], limit=1)
                
            #     vals = {
            #         'pms_payment_type': name,
            #         'pms_payment_id': str(unk_id),
            #         'hotel_id': self.id,
            #     }
                
            #     if mapping:
            #         mapping.write(vals)
            #     else:
            #         vals['journal_id'] = self.journal_id.id or False
            #         self.env['pms.payment.mapping'].create(vals)
