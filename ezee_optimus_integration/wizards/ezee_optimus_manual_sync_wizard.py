from odoo import fields, models
from odoo.exceptions import UserError


class EzeeOptimusManualSyncWizard(models.TransientModel):
    _name = 'ezee.optimus.manual.sync.wizard'
    _description = 'eZee Optimus Manual Sync Wizard'

    hotel_ids = fields.Many2many(
        'ezee.optimus.fas.config',
        string='Hotels',
        required=True,
        domain=[('active', '=', True)],
    )
    date_from = fields.Date(string='From Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='To Date', required=True, default=fields.Date.context_today)
    sync_outlets = fields.Boolean(string='Get Outlets', default=False)
    sync_account_mapping = fields.Boolean(string='Get Account Mapping', default=False)
    sync_sales = fields.Boolean(string='Get Sales', default=True)
    sync_purchase = fields.Boolean(string='Get Purchase', default=False)

    def _get_sync_service(self, config, sync_type):
        return self.env['ezee.optimus.sync'].with_context(
            fas_config_id=config.id,
            sync_log_type=sync_type,
            sync_date_from=self.date_from,
            sync_date_to=self.date_to,
        ).sudo().create({})

    def _notify(self, title, message, notification_type='success'):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': notification_type,
                'sticky': False,
            },
        }

    def action_sync(self):
        self.ensure_one()
        if not any([
            self.sync_outlets,
            self.sync_account_mapping,
            self.sync_sales,
            self.sync_purchase,
        ]):
            raise UserError('Please select at least one sync option.')

        stats = {
            'outlets': 0,
            'account_mapping': 0,
            'sales_received': 0,
            'sales_created': 0,
            'sales_skipped_existing': 0,
            'sales_skipped_no_lines': 0,
            'sales_missing_mappings': 0,
            'purchase_received': 0,
            'purchase_created': 0,
            'purchase_skipped_existing': 0,
            'purchase_skipped_no_lines': 0,
            'purchase_missing_mappings': 0,
        }
        for config in self.hotel_ids:
            if self.sync_outlets:
                outlets = self._get_sync_service(config, 'outlets').fetch_outlets()
                stats['outlets'] += len(outlets)

            if self.sync_account_mapping:
                self._get_sync_service(config, 'account_mapping').action_import_config()
                stats['account_mapping'] += 1

            if self.sync_sales:
                result = self._get_sync_service(config, 'sales').sync_sales(
                    fields.Date.to_string(self.date_from),
                    fields.Date.to_string(self.date_to),
                )
                stats['sales_received'] += result.get('received', 0)
                stats['sales_created'] += result.get('created', 0)
                stats['sales_skipped_existing'] += result.get('skipped_existing', 0)
                stats['sales_skipped_no_lines'] += result.get('skipped_no_lines', 0)
                stats['sales_missing_mappings'] += result.get('missing_mappings', 0)

            if self.sync_purchase:
                result = self._get_sync_service(config, 'purchase').sync_purchases(
                    fields.Date.to_string(self.date_from),
                    fields.Date.to_string(self.date_to),
                )
                stats['purchase_received'] += result.get('received', 0)
                stats['purchase_created'] += result.get('created', 0)
                stats['purchase_skipped_existing'] += result.get('skipped_existing', 0)
                stats['purchase_skipped_no_lines'] += result.get('skipped_no_lines', 0)
                stats['purchase_missing_mappings'] += result.get('missing_mappings', 0)

        return self._notify(
            'Sync Complete',
            (
                'Outlets: %(outlets)s, account mapping imports: %(account_mapping)s, '
                'sales received/created/existing/no mapped lines: '
                '%(sales_received)s/%(sales_created)s/%(sales_skipped_existing)s/%(sales_skipped_no_lines)s, '
                'missing sales mappings: %(sales_missing_mappings)s, '
                'purchase received/created/existing/no mapped lines: '
                '%(purchase_received)s/%(purchase_created)s/%(purchase_skipped_existing)s/%(purchase_skipped_no_lines)s, '
                'missing purchase mappings: %(purchase_missing_mappings)s.'
            ) % stats,
        )

    def action_get_outlets(self):
        self.ensure_one()
        config = self.hotel_ids[:1]
        if not config:
            raise UserError('Please select at least one hotel.')
        outlets = self._get_sync_service(config, 'outlets').fetch_outlets()
        return self._notify('Outlets Synced', '%s outlet(s) received from Optimus.' % len(outlets))

    def action_get_account_mapping(self):
        self.ensure_one()
        config = self.hotel_ids[:1]
        if not config:
            raise UserError('Please select at least one hotel.')
        result = self._get_sync_service(config, 'account_mapping').action_import_config()
        return result or self._notify('Account Mapping Synced', 'Account mapping synchronization completed.')

    def action_get_sales(self):
        self.ensure_one()
        config = self.hotel_ids[:1]
        if not config:
            raise UserError('Please select at least one hotel.')
        result = self._get_sync_service(config, 'sales').sync_sales(
            fields.Date.to_string(self.date_from),
            fields.Date.to_string(self.date_to),
        )
        return self._notify(
            'Sales Synced',
            (
                'Received: %(received)s, created: %(created)s, existing: %(skipped_existing)s, '
                'no mapped lines: %(skipped_no_lines)s, missing mappings: %(missing_mappings)s.'
            ) % result,
        )

    def action_get_purchase(self):
        self.ensure_one()
        config = self.hotel_ids[:1]
        if not config:
            raise UserError('Please select at least one hotel.')
        result = self._get_sync_service(config, 'purchase').sync_purchases(
            fields.Date.to_string(self.date_from),
            fields.Date.to_string(self.date_to),
        )
        return self._notify(
            'Purchase Synced',
            (
                'Received: %(received)s, created: %(created)s, existing: %(skipped_existing)s, '
                'no mapped lines: %(skipped_no_lines)s, missing mappings: %(missing_mappings)s.'
            ) % result,
        )
