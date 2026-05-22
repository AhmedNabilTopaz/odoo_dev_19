import logging
from datetime import timedelta

import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class EzeeOptimusSync(models.Model):
    _name = 'ezee.optimus.sync'
    _description = 'eZee Optimus POS Sync'

    @api.model
    def _cron_daily_sync(self):
        yesterday = (fields.Date.context_today(self) - timedelta(days=1)).strftime('%Y-%m-%d')
        return self.sync_all(yesterday, yesterday)

    def _get_optimus_connection(self):
        """Helper to get credentials via the config model."""
        return self.env['res.config.settings'].sudo()._get_optimus_connection()

    def _post_optimus(self, endpoint, payload, timeout=30):
        base_url, hotel_code, headers, auth = self._get_optimus_connection()
        payload = dict(payload, hotel_code=hotel_code)
        url = base_url.rstrip('/') + '/' + endpoint
        try:
            session = requests.Session()
            session.trust_env = False
            resp = session.post(url, headers=headers, auth=auth, json=payload, timeout=timeout)
        except requests.exceptions.RequestException as e:
            raise UserError(f'eZee Optimus connection failed for {endpoint}: {e}')

        try:
            result = resp.json()
        except ValueError:
            result = {}

        if resp.status_code >= 400 or result.get('statusCode') not in (None, 200):
            message = result.get('message') or result.get('status') or resp.text or resp.reason
            raise UserError(f'eZee Optimus API error on {endpoint}: {message}')

        return result

    def sync_all(self, from_date: str, to_date: str):
        """
        Master sync method — called by cron and manual button.
        Runs in this order:
        1. Fetch and refresh outlets
        2. Fetch and refresh account config
        3. Sync sales for date range
        4. Sync purchases for date range
        """
        try:
            outlets = self.fetch_outlets()
            _logger.info('eZee Optimus: %d outlets found', len(outlets))
        except Exception as e:
            _logger.error('Outlet fetch failed: %s', e)
            raise

        try:
            _, config_map = self.fetch_config()
            _logger.info('eZee Optimus: config loaded (%d entries)', len(config_map))
        except Exception as e:
            _logger.error('Config fetch failed: %s', e)
            raise

        try:
            sales_result = self.sync_sales(from_date, to_date)
            _logger.info('Sales sync: %s', sales_result)
        except Exception as e:
            _logger.error('Sales sync failed: %s', e)

        try:
            purch_result = self.sync_purchases(from_date, to_date)
            _logger.info('Purchases sync: %s', purch_result)
        except Exception as e:
            _logger.error('Purchases sync failed: %s', e)

    def fetch_outlets(self):
        """
        Calls get_store_name and returns list of outlets as:
        [{'id': '1000000000000001', 'name': 'Main Restaurant'}, ...]
        Raises on auth failure or network error.
        """
        result = self._post_optimus('get_store_name', {}, timeout=30)

        outlets = result.get('data', [])
        if not outlets:
            raise UserError('No outlets returned from eZee Optimus.')
        
        OutletModel = self.env['ezee.optimus.outlet']
        for out in outlets:
            existing = OutletModel.search([('ezee_outlet_id', '=', out['id'])], limit=1)
            if existing:
                existing.name = out['name']
            else:
                OutletModel.create({
                    'ezee_outlet_id': out['id'],
                    'name': out['name']
                })
        return outlets

    def fetch_config(self):
        """
        Fetches the full F&B financial account config from eZee Optimus.
        Returns a lookup dict keyed by (headerid, descriptionunkid) -> description.
        Also returns a list of all raw config items.
        """
        result = self._post_optimus('get_config_data', {}, timeout=30)

        config_items = result.get('data', [])
        # Build lookup: (headerid_int, descriptionunkid_str) -> description
        config_map = {}
        for item in config_items:
            key = (int(item['headerid']), str(item['descriptionunkid']))
            config_map[key] = item.get('description', '')

        return config_items, config_map

    def action_import_config(self):
        """
        Imports all F&B financial heads from eZee Optimus.
        Creates mapping records with empty odoo_account_id for the accountant to fill.
        Skips records that already exist.
        """
        config_items, _ = self.fetch_config()
        Mapping = self.env['ezee.optimus.account.mapping']
        created = 0
        for item in config_items:
            exists = Mapping.search([
                ('header_id', '=', int(item['headerid'])),
                ('desc_type_id', '=', int(item['descriptiontypeunkid'])),
                ('ezee_desc_unk_id', '=', str(item['descriptionunkid'])),
            ], limit=1)
            if exists:
                continue

            Mapping.create({
                'header_id': int(item['headerid']),
                'header_name': item.get('header', ''),
                'desc_type_id': int(item['descriptiontypeunkid']),
                'desc_type_name': item.get('descriptiontype', ''),
                'ezee_desc_unk_id': str(item['descriptionunkid']),
                'description': item.get('description', ''),
                'odoo_account_id': False, # Accountant fills this in
            })
            created += 1

        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': 'Import Complete',
                           'message': f'{created} new mapping rows created.',
                           'type': 'success'}}

    def sync_sales(self, from_date: str, to_date: str):
        """
        Main sales sync method.
        from_date / to_date: 'YYYY-MM-DD' strings.
        Creates one account.move per unique record_id not yet in Odoo.
        """
        payload = {
            'fromdate': from_date,
            'todate': to_date,
            'exclude_roomposting': '0',
            'exclude_nocharge': '0'
        }
        result = self._post_optimus('get_sales_data', payload, timeout=120)

        records = result.get('data', [])
        created, skipped = 0, 0

        for rec in records:
            record_id = rec.get('record_id')
            # Duplicate guard
            existing = self.env['account.move'].search([
                ('ref', '=', f'EZEEPOS-{record_id}')
            ], limit=1)
            if existing:
                skipped += 1
                continue

            move = self._create_sales_move(rec)
            if move:
                created += 1

        return {'created': created, 'skipped': skipped}

    def _create_sales_move(self, rec):
        """Creates one account.move from a single sales record."""
        record_id = rec['record_id']
        rec_date = rec['record_date']
        receipt_no = rec.get('reference1', '')
        outlet_id = rec.get('reference2', '')
        outlet_nm = rec.get('reference3', '')
        cashier = rec.get('reference18', '')
        order_type = rec.get('reference21', '')

        # Find the journal for this outlet
        outlet = self.env['ezee.optimus.outlet'].search([
            ('ezee_outlet_id', '=', outlet_id)
        ], limit=1)
        
        journal = outlet.sales_journal_id if outlet and outlet.sales_journal_id else \
                  self.env['account.journal'].search([
                      ('type', 'in', ['sale', 'general'])
                  ], limit=1)

        narration = (f'POS Sale | Outlet: {outlet_nm} | '
                     f'Receipt: {receipt_no} | Cashier: {cashier} | '
                     f'Type: {order_type}')

        line_vals = []
        for detail in rec.get('details', []):
            account = self._resolve_account(
                int(detail.get('reference_id', 0)),
                str(detail.get('sub_ref2_value', '') or '')
            )
            if not account:
                _logger.warning("No mapping for sales line %s", detail)
                continue # Log missing mapping

            amount = float(detail.get('amount', 0) or 0)
            tran_type = detail.get('tran_type', 'Dr')
            debit = amount if tran_type == 'Dr' else 0.0
            credit = amount if tran_type == 'Cr' else 0.0

            line_vals.append({
                'account_id': account.id,
                'name': detail.get('charge_name', '') or detail.get('reference_name', ''),
                'debit': debit,
                'credit': credit,
            })

        if not line_vals:
            return None

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': rec_date,
            'ref': f'EZEEPOS-{record_id}',
            'journal_id': journal.id,
            'narration': narration,
            'line_ids': [(0, 0, lv) for lv in line_vals],
        })
        return move

    def _resolve_account(self, header_id: int, desc_unk_id: str):
        """
        Looks up account.account from the mapping model.
        Falls back to Single Ledger (desc_type_id=1) if sub-type not found.
        """
        Mapping = self.env['ezee.optimus.account.mapping']
        # Try exact sub-type match first
        if desc_unk_id and desc_unk_id not in ('0', ''):
            m = Mapping.search([
                ('header_id', '=', header_id),
                ('ezee_desc_unk_id', '=', desc_unk_id)
            ], limit=1)
            if m and m.odoo_account_id:
                return m.odoo_account_id

        # Fall back to Single Ledger
        m = Mapping.search([
            ('header_id', '=', header_id),
            ('desc_type_id', '=', 1) # Single Ledger
        ], limit=1)
        return m.odoo_account_id if m else None

    def sync_purchases(self, from_date: str, to_date: str):
        """
        Syncs all F&B purchase records as Odoo vendor bills.
        Creates one account.move (move_type='in_invoice') per record_id.
        """
        payload = {
            'fromdate': from_date,
            'todate': to_date
            # outlet omitted = returns all outlets
        }
        result = self._post_optimus('get_purchase_data', payload, timeout=120)

        records = result.get('data', [])
        created, skipped = 0, 0

        for rec in records:
            record_id = rec.get('record_id')
            existing = self.env['account.move'].search([
                ('ref', '=', f'EZEEPURCHASE-{record_id}')
            ], limit=1)
            if existing:
                skipped += 1
                continue

            move = self._create_purchase_move(rec)
            if move:
                created += 1

        return {'created': created, 'skipped': skipped}

    def _create_purchase_move(self, rec):
        """Creates one vendor bill from a purchase record."""
        record_id = rec['record_id']
        rec_date = rec['record_date']
        grn_no = rec.get('reference1', '')
        outlet_nm = rec.get('reference4', '')
        doc_type = rec.get('reference15', 'Goods Received Note')
        outlet_id = rec.get('reference3', '')

        # Find or create vendor partner
        vendor = self._resolve_vendor(rec)

        outlet = self.env['ezee.optimus.outlet'].search([
            ('ezee_outlet_id', '=', outlet_id)
        ], limit=1)

        journal = outlet.purchase_journal_id if outlet and outlet.purchase_journal_id else \
                  self.env['account.journal'].search([
                      ('type', '=', 'purchase')
                  ], limit=1)

        invoice_lines = []
        for detail in rec.get('details', []):
            ref_id = int(detail.get('reference_id', 0))
            # Only create lines for purchase/tax heads
            # Vendor account lines (ref_id 20) are handled by move_type='in_invoice'
            if ref_id not in (17, 18, 32):
                continue

            account = self._resolve_account(
                ref_id,
                str(detail.get('sub_ref2_value', '') or '')
            )
            if not account:
                _logger.warning("No mapping for purchase line %s", detail)
                continue

            amount = float(detail.get('amount', 0) or 0)
            charge = detail.get('charge_name', '') or detail.get('reference_name', '')
            qty = float(detail.get('qty', 1) or 1)
            price = float(detail.get('rate_per_unit', amount) or amount)

            invoice_lines.append({
                'account_id': account.id,
                'name': charge,
                'quantity': qty,
                'price_unit': price,
            })

        if not invoice_lines:
            return None

        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': rec_date,
            'invoice_date': rec_date,
            'ref': f'EZEEPURCHASE-{record_id}',
            'partner_id': vendor.id if vendor else False,
            'journal_id': journal.id if journal else False,
            'narration': f'{doc_type} | GRN: {grn_no} | Outlet: {outlet_nm}',
            'invoice_line_ids': [(0, 0, lv) for lv in invoice_lines],
        })
        return move

    def _resolve_vendor(self, rec):
        """
        Finds the vendor partner for a purchase record.
        Looks for a Vendor-type detail line (reference_id=19)
        and matches its sub_ref2_value to a City Ledger / Vendor mapping.
        """
        for detail in rec.get('details', []):
            if int(detail.get('reference_id', 0)) == 19:
                vendor_id = str(detail.get('sub_ref2_value', '') or '')
                mapping = self.env['ezee.optimus.account.mapping'].search([
                    ('header_id', '=', 19),
                    ('ezee_desc_unk_id', '=', vendor_id)
                ], limit=1)

                # Try to find res.partner by name from description
                if mapping and mapping.description:
                    partner = self.env['res.partner'].search([
                        ('name', 'ilike', mapping.description),
                        ('supplier_rank', '>', 0)
                    ], limit=1)
                    if partner:
                        return partner
        return None
