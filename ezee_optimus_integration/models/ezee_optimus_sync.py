import logging
import json
from datetime import timedelta

import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EzeeOptimusSync(models.Model):
    _name = 'ezee.optimus.sync'
    _description = 'eZee Optimus POS Sync'

    # ---------------------------------------------------------------------------
    # Cron entry point
    # ---------------------------------------------------------------------------

    @api.model
    def _cron_daily_sync(self):
        yesterday = (fields.Date.context_today(self) - timedelta(days=1)).strftime('%Y-%m-%d')
        return self.sync_all(yesterday, yesterday)

    # ---------------------------------------------------------------------------
    # HTTP helper
    # ---------------------------------------------------------------------------

    def _get_optimus_connection(self):
        return self.env['res.config.settings'].sudo()._get_optimus_connection()

    def _post_optimus(self, requestfor, payload, timeout=30):
        base_url, company_id, auth_code, headers = self._get_optimus_connection()
        payload = dict(payload, auth_code=auth_code, comanyunkid=company_id, requestfor=requestfor)

        _logger.info('eZee POST | requestfor: %s | company: %s', requestfor, company_id)

        try:
            session = requests.Session()
            session.trust_env = False
            resp = session.post(base_url, headers=headers, data=json.dumps(payload), timeout=timeout)
        except requests.exceptions.RequestException as e:
            raise UserError(f'eZee Optimus connection failed for {requestfor}: {e}')

        _logger.info('eZee RESPONSE | status: %s | body: %s', resp.status_code, resp.text[:300])

        try:
            result = resp.json()
        except ValueError:
            result = {}

        if result.get('status') in ('error', 'warning'):
            message = result.get('message') or result.get('code') or resp.text
            raise UserError(f'eZee Optimus API error on {requestfor}: {message}')

        if resp.status_code >= 400:
            raise UserError(f'eZee Optimus HTTP {resp.status_code} on {requestfor}: {resp.text}')

        return result

    # ---------------------------------------------------------------------------
    # Master sync
    # ---------------------------------------------------------------------------

    def sync_all(self, from_date: str, to_date: str):
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

    # ---------------------------------------------------------------------------
    # Outlets
    # ---------------------------------------------------------------------------

    def fetch_outlets(self):
        result = self._post_optimus('XERO_GET_STORE_CONFIG', {}, timeout=30)
        outlets = result.get('data', [])
        if not outlets:
            raise UserError('No outlets returned from eZee Optimus.')

        OutletModel = self.env['ezee.optimus.outlet']
        for out in outlets:
            existing = OutletModel.search([('ezee_outlet_id', '=', out['id'])], limit=1)
            if existing:
                existing.name = out['name']
            else:
                OutletModel.create({'ezee_outlet_id': out['id'], 'name': out['name']})
        return outlets

    # ---------------------------------------------------------------------------
    # Config / mapping import
    # ---------------------------------------------------------------------------

    def fetch_config(self):
        result = self._post_optimus('XERO_GET_CONFIG_DATA', {}, timeout=30)
        config_items = result.get('data', [])
        config_map = {}
        for item in config_items:
            key = (int(item['headerid']), str(item['descriptionunkid']))
            config_map[key] = item.get('description', '')
        return config_items, config_map

    def action_import_config(self):
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
                'odoo_account_id': False,
            })
            created += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Import Complete',
                'message': f'{created} new mapping rows created.',
                'type': 'success',
            },
        }

    # ---------------------------------------------------------------------------
    # Account resolution
    # ---------------------------------------------------------------------------

    def _resolve_account(self, header_id: int, desc_unk_id: str):
        """
        Two-step lookup:
          1. Exact match on (header_id, ezee_desc_unk_id)
          2. Fallback to Single Ledger (desc_type_id=1) for same header_id
        Returns account.account record or None.
        """
        Mapping = self.env['ezee.optimus.account.mapping']
        if desc_unk_id and desc_unk_id not in ('0', ''):
            m = Mapping.search([
                ('header_id', '=', header_id),
                ('ezee_desc_unk_id', '=', desc_unk_id),
            ], limit=1)
            if m and m.odoo_account_id:
                return m.odoo_account_id
        # Single Ledger fallback
        m = Mapping.search([
            ('header_id', '=', header_id),
            ('desc_type_id', '=', 1),
        ], limit=1)
        return m.odoo_account_id if m else None

    def _get_sales_line_account_key(self, detail: dict) -> tuple[int, str]:
        """
        Returns (header_id, desc_unk_id) for a single sales detail line.

        Resolution per reference_id — derived from real API response analysis:

          ref_id=1  POS Sales  → header_id=1,  key = Menu Group ID from sub_ref6_value
                                 sub_ref6_value comes as "1592070000000001 + ", strip " + "
                                 If sub_ref6 is empty/0 fall back to sub_ref2_value then '0'

          ref_id=3  Taxes      → header_id=3,  key = sub_ref2_value (tax descriptionunkid)
                                 When sub_ref2 is outlet ID (e.g. 1592070000000001) that IS
                                 the VAT descriptionunkid for this property — use it directly.

          ref_id=5  Adjustment → header_id=5,  key = '1' (always Single Ledger)

          ref_id=8  Payment    → header_id=8,  key = sub_ref2_value (payment method ID)

          Any other ref_id     → (ref_id, sub_ref2_value) — generic fallback, may return None
        """
        ref_id = int(detail.get('reference_id', 0))

        if ref_id == 1:
            # LIVE API FACT: Menu Group ID lives in sub_ref7_value, NOT sub_ref6_value.
            key = str(detail.get('sub_ref7_value', '') or '')

            # Fallbacks just in case of malformed data
            if not key or key in ('0', ''):
                key = str(detail.get('sub_ref2_value', '') or '')
            return (1, key)

        if ref_id == 3:
            # sub_ref2_value holds the tax descriptionunkid
            key = str(detail.get('sub_ref2_value', '') or '')
            return (3, key)

        if ref_id == 5:
            # Adjustment — always maps to Single Ledger '1'
            return (5, '1')

        if ref_id == 8:
            # Payment method ID
            key = str(detail.get('sub_ref2_value', '') or '')
            return (8, key)

        # Generic: use reference_id as header_id and sub_ref2_value as key
        key = str(detail.get('sub_ref2_value', '') or '')
        return (ref_id, key)
    # ---------------------------------------------------------------------------
    # Sales sync
    # ---------------------------------------------------------------------------

    def sync_sales(self, from_date: str, to_date: str):
        payload = {
            'fromdate': from_date,
            'todate': to_date,
            'exclude_roomposting': '0',
            'exclude_nocharge': '0',
        }
        result = self._post_optimus('XERO_GET_SALES_DATA', payload, timeout=120)
        records = result.get('data', [])
        created, skipped = 0, 0
        for rec in records:
            record_id = rec.get('record_id')
            existing = self.env['account.move'].search(
                [('ref', '=', f'EZEEPOS-{record_id}')], limit=1
            )
            if existing:
                skipped += 1
                continue
            move = self._create_sales_move(rec)
            if move:
                created += 1
        return {'created': created, 'skipped': skipped}

    def _create_sales_move(self, rec):
        record_id = rec['record_id']
        rec_date  = rec['record_date']
        receipt_no = rec.get('reference1', '')
        outlet_id  = rec.get('reference2', '')
        outlet_nm  = rec.get('reference3', '')
        cashier    = rec.get('reference18', '')
        order_type = rec.get('reference21', '')

        # Journal — prefer outlet-specific, fall back to any sale/general journal
        outlet = self.env['ezee.optimus.outlet'].search(
            [('ezee_outlet_id', '=', outlet_id)], limit=1
        )
        journal = (
            outlet.sales_journal_id
            if outlet and outlet.sales_journal_id
            else self.env['account.journal'].search(
                [('type', 'in', ['sale', 'general'])], limit=1
            )
        )

        narration = (
            f'POS Sale | Outlet: {outlet_nm} | Receipt: {receipt_no} | '
            f'Cashier: {cashier} | Type: {order_type}'
        )

        line_vals = []
        for detail in rec.get('details', []):
            ref_id = int(detail.get('reference_id', 0))

            # Skip unknown / unhandled reference types
            if ref_id not in (1, 3, 5, 8):
                _logger.debug(
                    'eZee sales: skipping unhandled ref_id=%s on record %s',
                    ref_id, record_id,
                )
                continue

            header_id, desc_unk_id = self._get_sales_line_account_key(detail)
            account = self._resolve_account(header_id, desc_unk_id)

            if not account:
                _logger.warning(
                    'eZee sales: no account mapping for header_id=%s desc_unk_id=%s '
                    '(record=%s ref_id=%s charge=%s)',
                    header_id, desc_unk_id, record_id, ref_id,
                    detail.get('charge_name', ''),
                )
                continue

            amount    = float(detail.get('amount', 0) or 0)
            tran_type = detail.get('tran_type', 'Dr')
            name      = detail.get('charge_name', '') or detail.get('reference_name', '')

            line_vals.append({
                'account_id': account.id,
                'name': name,
                'debit':  amount if tran_type == 'Dr' else 0.0,
                'credit': amount if tran_type == 'Cr' else 0.0,
            })

        if not line_vals:
            _logger.warning(
                'eZee sales: no valid lines for record %s — move not created', record_id
            )
            return None

        return self.env['account.move'].create({
            'move_type': 'entry',
            'date': rec_date,
            'ref': f'EZEEPOS-{record_id}',
            'journal_id': journal.id,
            'narration': narration,
            'line_ids': [(0, 0, lv) for lv in line_vals],
        })

    # ---------------------------------------------------------------------------
    # Purchases sync
    # ---------------------------------------------------------------------------

    def sync_purchases(self, from_date: str, to_date: str):
        payload = {'fromdate': from_date, 'todate': to_date}
        result = self._post_optimus('XERO_GET_PURCHASE_DATA', payload, timeout=120)
        records = result.get('data', [])
        created, skipped = 0, 0
        for rec in records:
            record_id = rec.get('record_id')
            existing = self.env['account.move'].search(
                [('ref', '=', f'EZEEPURCHASE-{record_id}')], limit=1
            )
            if existing:
                skipped += 1
                continue
            move = self._create_purchase_move(rec)
            if move:
                created += 1
        return {'created': created, 'skipped': skipped}

    def _create_purchase_move(self, rec):
        record_id = rec['record_id']
        rec_date = rec['record_date']
        grn_no = rec.get('reference1', '')
        outlet_id = rec.get('reference3', '')
        outlet_nm = rec.get('reference4', '')
        doc_type = rec.get('reference15', 'Goods Received Note')

        vendor = self._resolve_vendor(rec)
        if not vendor:
            _logger.error('eZee Purchase: Skipping record %s because no Odoo Partner was found.', record_id)
            return None

        outlet = self.env['ezee.optimus.outlet'].search([('ezee_outlet_id', '=', outlet_id)], limit=1)
        journal = (
            outlet.purchase_journal_id
            if outlet and outlet.purchase_journal_id
            else self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        )

        invoice_lines = []
        for detail in rec.get('details', []):
            ref_id = int(detail.get('reference_id', 0))
            # 17=Items, 18=Tax, 32=Extra Charges
            if ref_id not in (17, 18, 32):
                continue

            desc_unk_id = str(detail.get('sub_ref2_value', '') or '')
            account = self._resolve_account(ref_id, desc_unk_id)

            if not account:
                _logger.warning('eZee Purchase: No account mapping for ref_id %s (record %s)', ref_id, record_id)
                continue

            # API FACT: amount is usually the TOTAL for the line.
            # Odoo's price_unit should be (amount / quantity) if rate_per_unit is missing.
            amount = float(detail.get('amount', 0) or 0)
            qty = float(detail.get('qty', 1) or 1)
            # Use rate_per_unit if available, otherwise calculate it
            price_unit = float(detail.get('rate_per_unit') or (amount / qty if qty != 0 else amount))

            invoice_lines.append({
                'account_id': account.id,
                'name': detail.get('charge_name', '') or detail.get('reference_name', 'Purchase Item'),
                'quantity': qty,
                'price_unit': price_unit,
            })

        if not invoice_lines:
            return None

        return self.env['account.move'].create({
            'move_type': 'in_invoice',  # Vendor Bill
            'date': rec_date,
            'invoice_date': rec_date,
            'ref': f'EZEEPURCHASE-{record_id}',
            'partner_id': vendor.id,
            'journal_id': journal.id if journal else False,
            'narration': f'{doc_type} | GRN: {grn_no} | Outlet: {outlet_nm}',
            'invoice_line_ids': [(0, 0, lv) for lv in invoice_lines],
        })

    def _resolve_vendor(self, rec):
        """
        Matches eZee Vendor (ref_id 19) to Odoo res.partner
        """
        for detail in rec.get('details', []):
            if int(detail.get('reference_id', 0)) != 19:
                continue

            vendor_id = str(detail.get('sub_ref2_value', '') or '')
            mapping = self.env['ezee.optimus.account.mapping'].search([
                ('header_id', '=', 19),
                ('ezee_desc_unk_id', '=', vendor_id),
            ], limit=1)

            # Use the 'description' from mapping to find the Odoo Partner
            if mapping and mapping.description:
                # Search for partner by name
                partner = self.env['res.partner'].search([
                    ('name', '=', mapping.description)
                ], limit=1)
                if partner:
                    return partner
        return None