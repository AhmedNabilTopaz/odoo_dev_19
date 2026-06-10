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
        configs = self.env['ezee.optimus.fas.config'].sudo().search([('active', '=', True)])
        for config in configs:
            try:
                env = self.env(context={
                    **self.env.context,
                    'allowed_company_ids': [config.company_id.id],
                    'force_company': config.company_id.id,
                })
                sync = env['ezee.optimus.sync'].with_context(
                    fas_config_id=config.id, sync_date_from=yesterday,
                    sync_date_to=yesterday,
                ).sudo().create({})
            except Exception as e:
                _logger.error('eZee cron setup failed for %s (company=%s): %s', config.name, config.company_id.display_name, e)
                continue
            try:
                sync.sync_sales(yesterday, yesterday)
            except Exception as e:
                _logger.error('eZee cron sales sync failed for %s (company=%s): %s', config.name, config.company_id.display_name, e)
            try:
                sync.sync_purchases(yesterday, yesterday)
            except Exception as e:
                _logger.error('eZee cron purchases sync failed for %s (company=%s): %s', config.name, config.company_id.display_name, e)

    # ---------------------------------------------------------------------------
    # HTTP helper
    # ---------------------------------------------------------------------------

    def _get_optimus_connection(self):
        fas_config_id = self.env.context.get('fas_config_id')
        if not fas_config_id:
            raise UserError('Please select an eZee Optimus FAS Configuration before running this sync.')

        config = self.env['ezee.optimus.fas.config'].sudo().browse(fas_config_id).exists()
        if not config:
            raise UserError('The selected eZee Optimus FAS Configuration no longer exists.')

        headers = {'Content-Type': 'application/json'}
        return config.base_url, config.optimus_company_id, config.auth_code, headers

    def _post_optimus(self, requestfor, payload, timeout=30):
        base_url, company_id, auth_code, headers = self._get_optimus_connection()
        payload = dict(payload, auth_code=auth_code, comanyunkid=company_id, requestfor=requestfor)
        log_vals = self._prepare_sync_log_vals(requestfor, base_url, headers, payload)

        _logger.info('eZee POST | requestfor: %s | company: %s', requestfor, company_id)

        try:
            session = requests.Session()
            session.trust_env = False
            resp = session.post(base_url, headers=headers, data=json.dumps(payload), timeout=timeout)
        except requests.exceptions.RequestException as e:
            self._create_sync_log(dict(log_vals, status='failed', error_message=str(e)))
            raise UserError(f'eZee Optimus connection failed for {requestfor}: {e}')

        _logger.info('eZee RESPONSE | status: %s | body: %s', resp.status_code, resp.text[:300])
        log_vals.update({'response_status_code': resp.status_code, 'response_body': resp.text, })

        try:
            result = resp.json()
        except ValueError:
            result = {}

        if result.get('status') in ('error', 'warning'):
            message = result.get('message') or result.get('code') or resp.text
            self._create_sync_log(dict(log_vals, status='failed', error_message=message))
            raise UserError(f'eZee Optimus API error on {requestfor}: {message}')

        if resp.status_code >= 400:
            self._create_sync_log(dict(log_vals, status='failed', error_message=resp.text))
            raise UserError(f'eZee Optimus HTTP {resp.status_code} on {requestfor}: {resp.text}')

        self._create_sync_log(dict(log_vals, status='success'))
        return result

    def _prepare_sync_log_vals(self, requestfor, base_url, headers, payload):
        sync_type = self.env.context.get('sync_log_type') or self._get_sync_type_from_requestfor(requestfor)
        return {'hotel_id': self.env.context.get('fas_config_id') or False, 'sync_type': sync_type,
            'date_from': self.env.context.get('sync_date_from') or payload.get('fromdate'),
            'date_to': self.env.context.get('sync_date_to') or payload.get('todate'), 'request_url': base_url,
            'request_headers': json.dumps(headers, indent=2), 'request_payload': json.dumps(payload, indent=2), }

    def _create_sync_log(self, vals):
        self.env['ezee.optimus.sync.log'].sudo().create(vals)

    @api.model
    def _get_sync_type_from_requestfor(self, requestfor):
        return {'XERO_GET_STORE_CONFIG': 'outlets', 'XERO_GET_CONFIG_DATA': 'config', 'XERO_GET_SALES_DATA': 'sales',
            'XERO_GET_PURCHASE_DATA': 'purchase', }.get(requestfor, 'other')

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

        config = self._get_hotel_config()
        if not config:
            raise UserError('FAS Configuration context required for outlet import.')

        OutletModel = self.env['ezee.optimus.outlet']
        for out in outlets:
            outlet_id = str(out.get('id') or '')
            outlet_name = out.get('name') or outlet_id
            if not outlet_id:
                continue

            existing = OutletModel.search([('hotel_id', '=', config.id), ('ezee_outlet_id', '=', outlet_id), ], limit=1)
            if existing:
                existing.name = outlet_name
            else:
                OutletModel.create({'hotel_id': config.id, 'ezee_outlet_id': outlet_id, 'name': outlet_name, })
        return outlets

    def test_connection(self):
        self._post_optimus('XERO_GET_STORE_CONFIG', {}, timeout=30)
        return True

    # ---------------------------------------------------------------------------
    # Config / mapping import
    # ---------------------------------------------------------------------------

    def fetch_config(self):
        result = self._post_optimus('XERO_GET_CONFIG_DATA', {}, timeout=30)
        config_items = result.get('data', [])
        config_map = {}
        for item in config_items:
            header_id = self._safe_int(item.get('headerid'))
            desc_unk_id = item.get('descriptionunkid')
            if not header_id or desc_unk_id is None:
                continue
            key = (header_id, str(desc_unk_id))
            config_map[key] = item.get('description', '')
        return config_items, config_map

    def _get_hotel_config(self):
        fas_config_id = self.env.context.get('fas_config_id')
        if not fas_config_id:
            return None
        return self.env['ezee.optimus.fas.config'].sudo().browse(fas_config_id).exists()

    def action_import_config(self):
        config_items, _ = self.fetch_config()
        config = self._get_hotel_config()
        if not config:
            raise UserError('FAS Configuration context required for import.')

        MappingHeader = self.env['ezee.optimus.account.mapping']
        MappingLine = self.env['ezee.optimus.account.mapping.line']
        TaxMapping = self.env['ezee.optimus.tax.mapping']

        header_created = 0
        line_created = 0
        tax_created = 0

        for item in config_items:
            header_id = self._safe_int(item.get('headerid'))
            if not header_id:
                continue
            header_name = item.get('header', '')
            normalized_header_name = str(header_name or '').strip().upper()
            desc_type = str(item.get('descriptiontype', '')).upper()
            desc_type_unk_id = item.get('descriptiontypeunkid')
            desc_unk_id = str(item.get('descriptionunkid') or '')
            desc_name = item.get('description', '')

            # --- Taxes go to tax mapping and never to account mapping ---
            if desc_type in ('TAX', 'TAXES') or normalized_header_name in ('TAX', 'TAXES'):
                if not desc_unk_id:
                    continue
                existing_tax = TaxMapping.search([('hotel_id', '=', config.id), ('tax_id', '=', desc_unk_id),
                    ('company_id', '=', config.company_id.id), ], limit=1)
                if existing_tax:
                    existing_tax.write({'tax_name': desc_name})
                else:
                    TaxMapping.create({'hotel_id': config.id, 'tax_id': desc_unk_id, 'tax_name': desc_name,
                        'company_id': config.company_id.id, })
                    tax_created += 1
                continue

            # --- Non-tax items go to account mapping (header + lines) ---
            header = MappingHeader.search([('header_id', '=', header_id), ('hotel_id', '=', config.id), ], limit=1)

            if not header:
                header = MappingHeader.create(
                    {'hotel_id': config.id, 'header_id': header_id, 'header_name': header_name,
                        'company_id': config.company_id.id, })
                header_created += 1
            else:
                if header.header_name != header_name:
                    header.write({'header_name': header_name})

            if not desc_unk_id:
                continue

            existing_line = MappingLine.search(
                [('mapping_id', '=', header.id), ('ezee_desc_unk_id', '=', desc_unk_id), ], limit=1)

            if not existing_line:
                MappingLine.create({'mapping_id': header.id, 'desc_type_id': desc_type_unk_id or 0,
                    'desc_type_name': item.get('descriptiontype', ''), 'ezee_desc_unk_id': desc_unk_id,
                    'description': desc_name, })
                line_created += 1

        self._update_fas_environment(config, config_items)

        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': 'Import Complete',
            'message': '%d header(s), %d line(s), %d tax(es) created.' % (header_created, line_created, tax_created),
            'type': 'success', }, }

    def _update_fas_environment(self, config, config_items):
        vals = {}
        working_date = self._find_config_value(config_items,
            ('working_date', 'workingdate', 'hotelworkingdate', 'business_date', 'businessdate'), )
        currency_code = self._find_config_value(config_items,
            ('currency_code', 'currencycode', 'hotelcurrencycode', 'default_currency', 'currency'), )
        if working_date:
            try:
                vals['working_date'] = fields.Date.to_date(working_date)
            except ValueError:
                _logger.warning('Ignoring invalid Optimus working date value: %s', working_date)
        if currency_code:
            vals['currency_code'] = currency_code
        if vals:
            config.write(vals)

    @api.model
    def _safe_int(self, value):
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @api.model
    def _find_config_value(self, config_items, keys):
        normalized_keys = {key.lower().replace(' ', '').replace('_', '') for key in keys}
        for item in config_items:
            if not isinstance(item, dict):
                continue
            for key, value in item.items():
                normalized_key = str(key).lower().replace(' ', '').replace('_', '')
                if normalized_key in normalized_keys and value:
                    return value

            desc_name = str(item.get('description') or '').lower().replace(' ', '').replace('_', '')
            if desc_name in normalized_keys:
                return item.get('value') or item.get('descriptionvalue') or item.get('descriptionunkid')
        return False

    # ---------------------------------------------------------------------------
    # Account resolution
    # ---------------------------------------------------------------------------

    def _resolve_account(self, header_id: int, desc_unk_id: str):
        """
        Three-step lookup:
          1. Mapping line with exact (header_id, ezee_desc_unk_id) and its own account_id override
          2. Header-level account_id for the header_id
          3. Single Ledger (desc_type_id=1) line fallback
        Returns account.account record or None.
        """
        config = self._get_hotel_config()
        if not config:
            return None

        MappingLine = self.env['ezee.optimus.account.mapping.line']
        MappingHeader = self.env['ezee.optimus.account.mapping']

        header = MappingHeader.search([('header_id', '=', header_id), ('hotel_id', '=', config.id), ], limit=1)
        if not header:
            return None

        if desc_unk_id and desc_unk_id not in ('0', ''):
            line = MappingLine.search([('mapping_id', '=', header.id), ('ezee_desc_unk_id', '=', desc_unk_id), ],
                limit=1)
            if line and line.account_id:
                return line.account_id

        if header.account_id:
            return header.account_id

        single_line = MappingLine.search([('mapping_id', '=', header.id), ('desc_type_id', '=', 1), ], limit=1)
        return single_line.account_id if single_line and single_line.account_id else None

    def _get_sales_line_account_key(self, detail: dict) -> tuple[int, str]:
        """
        Returns (header_id, desc_unk_id) for a single sales detail line.

        Resolution per reference_id:

          ref_id=1  POS Sales  -> header_id=1,  key = Menu Group ID from sub_ref7_value
                                 If empty/0 fall back to sub_ref2_value then '0'

          ref_id=3  Taxes      -> header_id=3,  key = sub_ref2_value (tax descriptionunkid)

          ref_id=5  Adjustment -> header_id=5,  key = '1' (always Single Ledger)

          ref_id=8  Payment    -> header_id=8,  key = sub_ref2_value (payment method ID)

          Any other ref_id     -> (ref_id, sub_ref2_value) — generic fallback
        """
        ref_id = int(detail.get('reference_id', 0))

        if ref_id == 1:
            key = str(detail.get('sub_ref7_value', '') or '')
            if not key or key in ('0', ''):
                key = str(detail.get('sub_ref2_value', '') or '')
            return (1, key)

        if ref_id == 3:
            key = str(detail.get('sub_ref2_value', '') or '')
            return (3, key)

        if ref_id == 5:
            return (5, '1')

        if ref_id == 8:
            key = str(detail.get('sub_ref2_value', '') or '')
            return (8, key)

        key = str(detail.get('sub_ref2_value', '') or '')
        return (ref_id, key)

    # ---------------------------------------------------------------------------
    # Sales sync
    # ---------------------------------------------------------------------------

    def sync_sales(self, from_date: str, to_date: str):
        payload = {'fromdate': from_date, 'todate': to_date, 'exclude_roomposting': '0', 'exclude_nocharge': '0', }
        result = self._post_optimus('XERO_GET_SALES_DATA', payload, timeout=120)
        records = result.get('data', [])
        _logger.info('eZee sales: syncing %d record(s) from %s to %s', len(records), from_date, to_date, )
        created = 0
        skipped_existing = 0
        skipped_no_lines = 0
        missing_mappings = 0
        for rec in records:
            record_id = rec.get('record_id')
            existing = self.env['account.move'].search(
                # TODO search b el date kman 3lshan mmkn ykon feh duplicate record id
                [('ref', '=', f'EZEEPOS-{record_id}')], limit=1)
            if existing:
                _logger.info('eZee sales: re-syncing existing record %s (current state=%s)', record_id,
                    existing.ezee_payment_status, )
                balance = float(rec.get('balance', 0) or 0)
                amount_paid = float(rec.get('amount_paid', 0) or 0)
                total_amount = float(rec.get('total_amount', 0) or 0)
                is_paid = (balance == 0.0 and amount_paid >= total_amount)
                new_status = 'paid' if is_paid else 'unpaid'

                update_vals = {'ezee_balance': balance, 'ezee_payment_status': new_status, }
                if existing.ezee_payment_status != new_status or existing.ezee_balance != balance:
                    existing.write(update_vals)
                    _logger.info('eZee sales: updated status for %s → %s (balance=%s)', record_id, new_status,
                        balance, )

                if is_paid and existing.payment_state != 'paid':
                    _logger.info('eZee sales: record %s is now paid in eZee, auto-paying in Odoo', record_id, )
                    config = self._get_hotel_config()
                    if config and not self._pay_invoice(existing, config):
                        _logger.error('eZee sales: auto-pay failed for existing record %s', record_id)

                skipped_existing += 1
                continue
            move, missing_count = self._create_sales_move(rec)
            missing_mappings += missing_count
            if move:
                created += 1
            else:
                skipped_no_lines += 1
        return {'received': len(records), 'created': created, 'skipped_existing': skipped_existing,
            'skipped_no_lines': skipped_no_lines, 'missing_mappings': missing_mappings, }

    def _create_sales_move(self, rec):
        record_id = rec.get('record_id')
        rec_date = rec.get('record_date')
        _logger.info('eZee sales: creating invoice for record %s (date=%s)', record_id, rec_date, )
        receipt_no = rec.get('reference1', '')
        outlet_id = rec.get('reference2', '')
        outlet_nm = rec.get('reference3', '')
        cashier = rec.get('reference18', '')
        order_type = rec.get('reference21', '')
        # TODO we need a flag to know whether if the invoice coming from a pos
        config = self._get_hotel_config()
        if not config:
            _logger.error('eZee sales: no FAS config in context, cannot create invoice for record %s', record_id, )
            return None, 0

        partner = self._get_pos_customer(config)
        _logger.info('eZee sales: using partner %s (id=%s)', partner.name, partner.id)

        outlet_domain = [('ezee_outlet_id', '=', outlet_id)]
        if config:
            outlet_domain.append(('hotel_id', '=', config.id))
        outlet = self.env['ezee.optimus.outlet'].search(outlet_domain, limit=1)
        if outlet:
            _logger.info('eZee sales: matched outlet %s (id=%s)', outlet.name, outlet.ezee_outlet_id)
        else:
            _logger.info('eZee sales: no outlet match for outlet_id=%s', outlet_id)
        journal = (
            outlet.sales_journal_id if outlet and outlet.sales_journal_id else self.env['account.journal'].search(
                [('type', '=', 'sale')], limit=1))
        _logger.info('eZee sales: using journal %s (id=%s)', journal.name, journal.id)

        narration = (f'POS Sale | Outlet: {outlet_nm} | Receipt: {receipt_no} | '
                     f'Cashier: {cashier} | Type: {order_type}')

        details = rec.get('details', [])

        # Build a lookup: detail_record_id -> detail dict
        # detail_by_id = {str(d.get('detail_record_id', '')): d for d in details}

        # Build a lookup: parent_record_id -> list of tax children (ref_id=3 only)
        tax_children = {}
        for d in details:
            if int(d.get('reference_id', 0)) == 3:
                parent = str(d.get('parent_record_id', ''))
                if parent:
                    tax_children.setdefault(parent, []).append(d)

        # Track which ref_id=3 lines have been handled via their parent
        # handled_tax_ids = set()

        invoice_line_vals = []
        missing_mappings = 0

        for detail in details:
            ref_id = int(detail.get('reference_id', 0))

            # Tax lines are handled as tax_ids on their parent
            if ref_id == 3:
                continue

            if ref_id not in (1, 5):
                _logger.info('eZee sales: skipping ref_id=%s on record %s (payment lines go via Odoo payment)', ref_id,
                    record_id, )
                continue

            # --- Process the main line (ref_id 1 or 5) ---
            header_id, desc_unk_id = self._get_sales_line_account_key(detail)
            account = self._resolve_account(header_id, desc_unk_id)

            if not account:
                missing_mappings += 1
                self._ensure_sales_mapping_placeholder(header_id, desc_unk_id, detail)
                _logger.warning('eZee sales: no account mapping for header_id=%s desc_unk_id=%s '
                                '(record=%s ref_id=%s charge=%s)', header_id, desc_unk_id, record_id, ref_id,
                    detail.get('charge_name', ''), )
                continue

            amount = float(detail.get('amount', 0) or 0)
            tran_type = detail.get('tran_type', 'Dr')
            name = detail.get('charge_name', '') or detail.get('reference_name', '')

            # --- Resolve taxes from eZee tax children (only for ref_id=1) ---
            tax_ids = []
            if ref_id == 1:
                detail_record_id = str(detail.get('detail_record_id', ''))
                for tax_detail in tax_children.get(detail_record_id, []):
                    odoo_tax = self._resolve_tax_id(tax_detail)
                    if odoo_tax:
                        tax_ids.append(odoo_tax.id)
                    else:
                        missing_mappings += 1
                        _logger.warning('eZee sales: no tax mapping for tax_id=%s '
                                        '(record=%s parent_detail=%s taxper=%s)', tax_detail.get('sub_ref2_value', ''),
                            record_id, detail_record_id, tax_detail.get('taxper', ''), )

            # Cr = positive charge (revenue), Dr = negative (discount/refund)
            price_unit = amount if tran_type == 'Cr' else -amount
            _logger.info('eZee sales: line ref_id=%s account=%s(name=%s) amount=%s tran_type=%s '
                         'price_unit=%s tax_ids=%s', ref_id, account.code, account.name, amount, tran_type, price_unit,
                tax_ids, )

            invoice_line_vals.append({'account_id': account.id, 'name': name, 'quantity': 1, 'price_unit': price_unit,
                'tax_ids': [(6, 0, tax_ids)], })

        if not invoice_line_vals:
            _logger.warning('eZee sales: no valid lines for record %s — invoice not created', record_id)
            return None, missing_mappings

        move = self.env['account.move'].create(
            {'move_type': 'out_invoice', 'partner_id': partner.id, 'date': rec_date, 'invoice_date': rec_date,
                'ref': f'EZEEPOS-{record_id}', 'journal_id': journal.id, 'narration': narration,
                'invoice_line_ids': [(0, 0, lv) for lv in invoice_line_vals], })
        _logger.info('eZee sales: invoice created id=%s ref=%s total=%s lines=%d', move.id, move.ref, move.amount_total,
            len(invoice_line_vals), )

        # Post
        move.action_post()
        _logger.info('eZee sales: invoice %s posted (state=%s payment_state=%s)', move.ref, move.state,
            move.payment_state, )

        # Store eZee payment status
        balance = float(rec.get('balance', 0) or 0)
        amount_paid = float(rec.get('amount_paid', 0) or 0)
        total_amount = float(rec.get('total_amount', 0) or 0)
        is_paid = (balance == 0.0 and amount_paid >= total_amount)

        move.write({'ezee_balance': balance, 'ezee_payment_status': 'paid' if is_paid else 'unpaid', })
        _logger.info('eZee sales: invoice %s ezee_balance=%s ezee_payment_status=%s', move.ref, balance,
            'paid' if is_paid else 'unpaid', )

        # Auto-pay if eZee says paid
        if is_paid:
            _logger.info('eZee sales: auto-paying invoice %s (amount=%s)', move.ref, move.amount_total, )
            if not self._pay_invoice(move, config):
                _logger.error('eZee sales: auto-pay failed for new invoice %s', move.ref)

        return move, missing_mappings

    def _resolve_sales_tax_account(self, tax_id):
        config = self._get_hotel_config()
        if not config or not tax_id:
            return None

        mapping = self.env['ezee.optimus.tax.mapping'].sudo().search(
            [('hotel_id', '=', config.id), ('tax_id', '=', str(tax_id)), ('company_id', '=', config.company_id.id), ],
            limit=1)
        if not mapping or not mapping.odoo_tax_id:
            return None

        tax_lines = mapping.odoo_tax_id.invoice_repartition_line_ids.filtered(
            lambda line: line.repartition_type == 'tax' and line.account_id)
        return tax_lines[:1].account_id if tax_lines else None

    # ---------------------------------------------------------------------------
    # POS Customer
    # ---------------------------------------------------------------------------

    def _get_pos_customer(self, config):
        company = config.company_id
        name = 'POS Customer - %s' % company.name
        partner = self.env['res.partner'].search([('name', '=', name)], limit=1)
        if not partner:
            partner = self.env['res.partner'].sudo().create(
                {'name': name, 'company_id': company.id, 'customer_rank': 1, })
            _logger.info('eZee sales: created new POS customer partner %s (id=%s)', name, partner.id)
        else:
            _logger.info('eZee sales: found existing POS customer partner %s (id=%s)', name, partner.id)
        return partner

    # ---------------------------------------------------------------------------
    # Tax resolution for invoice lines (Option A: trust Odoo tax computation)
    # ---------------------------------------------------------------------------

    def _resolve_tax_id(self, tax_detail):
        tax_id = str(tax_detail.get('sub_ref2_value', '') or '')
        if not tax_id:
            return None
        config = self._get_hotel_config()
        if not config:
            return None
        mapping = self.env['ezee.optimus.tax.mapping'].sudo().search(
            [('hotel_id', '=', config.id), ('tax_id', '=', tax_id), ('company_id', '=', config.company_id.id), ],
            limit=1)
        result = mapping.odoo_tax_id if mapping else None
        _logger.info('eZee sales: resolve tax ezee_tax_id=%s → odoo_tax=%s', tax_id, result.name if result else None, )
        return result

    # ---------------------------------------------------------------------------
    # Payment auto-pay helpers
    # ---------------------------------------------------------------------------

    def _resolve_payment_account(self, config):
        header = self.env['ezee.optimus.account.mapping'].search(
            [('header_id', '=', 8), ('hotel_id', '=', config.id), ], limit=1)
        account = header.account_id if header and header.account_id else None
        _logger.info('eZee payment: resolved account from header_id=8 → %s',
            account.code if account else 'None (will use partner default)', )
        return account

    def _pay_invoice(self, invoice, config):
        self.ensure_one()

        is_purchase = invoice.move_type == 'in_invoice'
        payment_type = 'outbound' if is_purchase else 'inbound'
        method_field = 'outbound_payment_method_line_ids' if is_purchase else 'inbound_payment_method_line_ids'
        partner_type = 'supplier' if is_purchase else 'customer'

        # Find a suitable journal with payment method lines in the right direction
        journal = config.debt_transfer_journal_id
        if journal and not getattr(journal, method_field):
            _logger.info('eZee payment: debt_transfer_journal %s has no %s payment methods, '
                         'searching for alternative', journal.name, payment_type)
            journal = False
        if not journal:
            journal = self.env['account.journal'].search(
                [('company_id', '=', config.company_id.id), ('type', 'in', ('bank', 'cash')),
                    (method_field, '!=', False)], limit=1)
        if not journal:
            _logger.error('eZee: no suitable journal for %s payment hotel %s, cannot pay %s',
                          payment_type, config.name, invoice.ref)
            return False

        payment_method_line = getattr(journal, method_field)[:1]

        # Ensure journal.default_account_id matches payment_method_line's account
        # so that is_matched computes True (Path B in _compute_reconciliation_status)
        if payment_method_line.payment_account_id:
            if journal.default_account_id != payment_method_line.payment_account_id:
                _logger.info('eZee payment: setting journal %s default_account_id to %s (was %s)',
                             journal.name, payment_method_line.payment_account_id.display_name,
                             journal.default_account_id.display_name if journal.default_account_id else 'None')
                journal.write({'default_account_id': payment_method_line.payment_account_id.id})

        # Fresh state
        invoice.invalidate_recordset(['payment_state', 'amount_residual', 'amount_total'])

        # Collect unpaid receivable/payable lines
        account_types = ('asset_receivable', 'liability_payable')
        payable_lines = invoice.line_ids.filtered(
            lambda l: l.account_type in account_types and not l.reconciled and not l.company_currency_id.is_zero(
                l.amount_residual)
        )
        if not payable_lines:
            _logger.error('eZee payment: no unpaid receivable/payable lines on invoice %s', invoice.ref)
            return False

        residual = abs(sum(payable_lines.mapped('amount_residual')))
        _logger.info('eZee payment: paying invoice %s — residual=%s total=%s payable_lines=%s',
                     invoice.ref, residual, invoice.amount_total, payable_lines.ids)

        # ---------------------------------------------------------------------
        # Create payment, post, and reconcile — no wizard
        # ---------------------------------------------------------------------
        try:
            payment = self.env['account.payment'].create({
                'date': invoice.date,
                'amount': residual,
                'payment_type': payment_type,
                'partner_type': partner_type,
                'memo': 'PYMT-%s' % invoice.ref,
                'journal_id': journal.id,
                'company_id': invoice.company_id.id,
                'currency_id': invoice.currency_id.id or invoice.company_id.currency_id.id,
                'partner_id': invoice.partner_id.id,
                'payment_method_line_id': payment_method_line.id,
                'destination_account_id': payable_lines[0].account_id.id,
            })
            _logger.info('eZee payment: payment %s created (amount=%s)', payment.name, payment.amount)

            payment.action_post()
            _logger.info('eZee payment: payment %s posted (state=%s)', payment.name, payment.state)

            # DEBUG: check payment move and is_matched right after post
            payment.invalidate_recordset(['is_matched', 'is_reconciled', 'move_id'])
            _logger.info('eZee payment DEBUG after post: move_id=%s is_matched=%s is_reconciled=%s outstanding_acc=%s',
                         payment.move_id.id if payment.move_id else 'None',
                         payment.is_matched, payment.is_reconciled,
                         payment.outstanding_account_id.display_name if payment.outstanding_account_id else 'False')

            # Reconcile: match the payment's counterpart line(s) with the invoice's payable line(s)
            counterpart_lines = payment.move_id.line_ids.filtered(
                lambda l: l.account_type in account_types and not l.reconciled
            )
            if not counterpart_lines:
                _logger.error('eZee payment: no counterpart lines on payment %s move %s (lines=%s)',
                              payment.name, payment.move_id.id, payment.move_id.line_ids.ids)
                return False

            _logger.info('eZee payment: reconciling invoice lines %s with payment lines %s',
                         payable_lines.ids, counterpart_lines.ids)
            (payable_lines + counterpart_lines).reconcile()

            # Link the payment to the invoice (wizard does this, required for UI badge)
            invoice.matched_payment_ids += payment

            # DEBUG: dump payment is_matched state
            payment.invalidate_recordset(['is_matched', 'is_reconciled'])
            invoice.invalidate_recordset(['payment_state', 'amount_residual', 'reconciled_payment_ids'])
            liq_lines, cp_lines, wo_lines = payment._seek_for_lines()
            _logger.info('eZee payment DEBUG: pay=%s state=%s is_matched=%s is_reconciled=%s outstanding_acc=%s jrnl_def_acc=%s pml_pay_acc=%s',
                         payment.name, payment.state, payment.is_matched, payment.is_reconciled,
                         payment.outstanding_account_id.display_name if payment.outstanding_account_id else 'False',
                         payment.journal_id.default_account_id.display_name if payment.journal_id.default_account_id else 'None',
                         payment.payment_method_line_id.payment_account_id.display_name if payment.payment_method_line_id.payment_account_id else 'None')
            _logger.info('eZee payment DEBUG: liq_lines=%s amt_res=%s cp_lines=%s wo_lines=%s',
                         liq_lines.ids, liq_lines.mapped('amount_residual'), cp_lines.ids, wo_lines.ids)
            _logger.info('eZee payment DEBUG: reconciled_payment_ids=%s matched_payment_ids=%s',
                         invoice.reconciled_payment_ids.ids, invoice.matched_payment_ids.ids)
            _logger.info('eZee payment: invoice %s after reconciliation — payment_state=%s',
                         invoice.ref, invoice.payment_state)

            if invoice.payment_state == 'paid':
                _logger.info('eZee payment: invoice %s fully paid', invoice.ref)
                return True

            _logger.warning('eZee payment: invoice %s payment_state=%s after reconcile (expected "paid")',
                            invoice.ref, invoice.payment_state)
            return False

        except Exception as e:
            _logger.error('eZee payment: failed for invoice %s: %s', invoice.ref, str(e), exc_info=True)
            return False

    def _ensure_sales_mapping_placeholder(self, header_id, desc_unk_id, detail):
        if not desc_unk_id:
            return

        config = self._get_hotel_config()
        if not config:
            return

        MappingHeader = self.env['ezee.optimus.account.mapping'].sudo()
        MappingLine = self.env['ezee.optimus.account.mapping.line'].sudo()

        header = MappingHeader.search([('header_id', '=', header_id), ('hotel_id', '=', config.id), ], limit=1)

        if not header:
            header_names = {1: 'POS Sales', 3: 'Taxes', 5: 'Adjustments', 8: 'Payment'}
            header = MappingHeader.create({'hotel_id': config.id, 'header_id': header_id,
                'header_name': header_names.get(header_id, detail.get('reference_name', '')),
                'company_id': config.company_id.id, })

        existing_line = MappingLine.search(
            [('mapping_id', '=', header.id), ('ezee_desc_unk_id', '=', str(desc_unk_id)), ], limit=1)
        if existing_line:
            return

        desc_type_ids = {1: 2, 3: 2, 5: 1, 8: 2}
        desc_type_names = {1: 'Menu Group', 3: 'Tax', 5: 'Single Ledger', 8: 'Payment Type'}
        description = detail.get('charge_name') or detail.get('reference_name') or str(desc_unk_id)
        if header_id == 3 and detail.get('taxper'):
            description = 'Tax %s%%' % detail.get('taxper')

        MappingLine.create({'mapping_id': header.id, 'desc_type_id': desc_type_ids.get(header_id, 0),
            'desc_type_name': desc_type_names.get(header_id, ''), 'ezee_desc_unk_id': str(desc_unk_id),
            'description': description, })

    # ---------------------------------------------------------------------------
    # Purchase line account key resolution
    # ---------------------------------------------------------------------------

    def _get_purchase_line_account_key(self, detail: dict) -> tuple[int, str]:
        ref_id = int(detail.get('reference_id', 0))
        key = str(detail.get('sub_ref2_value', '') or '')
        return (ref_id, key)

    # ---------------------------------------------------------------------------
    # Purchases sync
    # ---------------------------------------------------------------------------

    def sync_purchases(self, from_date: str, to_date: str):
        payload = {'fromdate': from_date, 'todate': to_date}
        result = self._post_optimus('XERO_GET_PURCHASE_DATA', payload, timeout=120)
        records = result.get('data', [])

        # --- TEMP: inject test data if API returns empty — remove after testing ---
        if not records:
            _logger.warning('eZee purchase: API returned empty, using hardcoded test record')
            records = [{"record_id": "1251830000000784", "record_date": "2021-11-10", "reference1": "GRN-65",
                "reference2": "1891", "reference3": "1251830000000001", "reference4": "M3 BOUTIQUE HOTEL",
                "reference15": "Goods Received Note", "gross_amount": "266.0000", "flat_discount": "0.0000",
                "total_tax": "0.0000", "add_less_amount": "0.0000", "total_amount": "266.0000", "balance": "0.0000",
                "amount_paid": "266.0000", "details": [
                    {"detail_reference_id": "1251830000006363", "reference_id": 17, "reference_name": "Purchase",
                        "sub_ref2_id": 2, "sub_ref2_value": "1251830000000009", "amount": "266.0000"},
                    {"detail_reference_id": "1251830000000784", "reference_id": 19, "reference_name": "Vendor",
                        "sub_ref2_id": 2, "sub_ref2_value": "1251830000000008", "amount": "266.0000"}]}]
        # --- END TEMP ---
        _logger.info('eZee purchase: syncing %d record(s) from %s to %s', len(records), from_date, to_date, )
        created = 0
        skipped_existing = 0
        skipped_no_lines = 0
        missing_mappings = 0
        for rec in records:
            record_id = rec.get('record_id')
            existing = self.env['account.move'].search([('ref', '=', f'EZEEPURCHASE-{record_id}')], limit=1)
            if existing:
                _logger.info('eZee purchase: re-syncing existing record %s (current state=%s)', record_id,
                    existing.ezee_payment_status, )
                balance = float(rec.get('balance', 0) or 0)
                amount_paid = float(rec.get('amount_paid', 0) or 0)
                total_amount = float(rec.get('total_amount', 0) or 0)
                is_paid = (balance == 0.0 and amount_paid >= total_amount)
                new_status = 'paid' if is_paid else 'unpaid'

                update_vals = {'ezee_balance': balance, 'ezee_payment_status': new_status, }
                if existing.ezee_payment_status != new_status or existing.ezee_balance != balance:
                    existing.write(update_vals)
                    _logger.info('eZee purchase: updated status for %s → %s (balance=%s)', record_id, new_status,
                        balance, )

                if is_paid and existing.payment_state != 'paid':
                    _logger.info('eZee purchase: record %s is now paid in eZee, auto-paying in Odoo', record_id, )
                    config = self._get_hotel_config()
                    if config and not self._pay_invoice(existing, config):
                        _logger.error('eZee purchase: auto-pay failed for existing record %s', record_id)

                skipped_existing += 1
                continue
            move, missing_count = self._create_purchase_move(rec)
            missing_mappings += missing_count
            if move:
                created += 1
            else:
                skipped_no_lines += 1
        return {'received': len(records), 'created': created, 'skipped_existing': skipped_existing,
            'skipped': skipped_existing + skipped_no_lines, 'skipped_no_lines': skipped_no_lines,
            'missing_mappings': missing_mappings, }

    def _create_purchase_move(self, rec):
        record_id = rec.get('record_id')
        rec_date = rec.get('record_date')
        _logger.info('eZee purchase: creating bill for record %s (date=%s)', record_id, rec_date, )
        grn_no = rec.get('reference1', '')
        outlet_id = rec.get('reference3', '')
        outlet_nm = rec.get('reference4', '')
        doc_type = rec.get('reference15', 'Goods Received Note')

        vendor = self._resolve_vendor(rec)
        if not vendor:
            _logger.warning(
                'eZee purchase: no vendor mapping for record %s — falling back to POS Vendor',
                record_id,
            )
            config = self._get_hotel_config()
            if not config:
                return None, 0
            vendor = self._get_pos_vendor(config)

        config = self._get_hotel_config()
        if not config:
            _logger.error('eZee purchase: no FAS config in context, cannot create bill for record %s', record_id, )
            return None, 0

        outlet_domain = [('ezee_outlet_id', '=', outlet_id)]
        if config:
            outlet_domain.append(('hotel_id', '=', config.id))
        outlet = self.env['ezee.optimus.outlet'].search(outlet_domain, limit=1)
        if outlet:
            _logger.info('eZee purchase: matched outlet %s (id=%s)', outlet.name, outlet.ezee_outlet_id)
        journal = (
            outlet.purchase_journal_id if outlet and outlet.purchase_journal_id else self.env['account.journal'].search(
                [('type', '=', 'purchase')], limit=1))
        _logger.info('eZee purchase: using journal %s (id=%s), vendor=%s (id=%s)', journal.name, journal.id,
            vendor.name, vendor.id, )

        narration = (f'{doc_type} | GRN: {grn_no} | Outlet: {outlet_nm}')

        details = rec.get('details', [])

        # Build tax children lookup (ref_id=18 / Store Tax grouped by parent_record_id)
        tax_children = {}
        for d in details:
            if int(d.get('reference_id', 0)) == 18:
                parent = str(d.get('parent_record_id', ''))
                if parent:
                    tax_children.setdefault(parent, []).append(d)

        invoice_line_vals = []
        missing_mappings = 0

        for detail in details:
            ref_id = int(detail.get('reference_id', 0))

            # Store Tax lines handled as tax_ids on their parent
            if ref_id == 18:
                continue

            # Vendor Account (AP) lines — handled automatically by Odoo
            if ref_id == 20:
                continue

            # Only process purchase line item types
            if ref_id not in (17, 32):
                continue

            header_id, desc_unk_id = self._get_purchase_line_account_key(detail)
            account = self._resolve_account(header_id, desc_unk_id)

            if not account:
                missing_mappings += 1
                _logger.warning('eZee purchase: no account mapping for header_id=%s desc_unk_id=%s '
                                '(record=%s ref_id=%s charge=%s)', header_id, desc_unk_id, record_id, ref_id,
                    detail.get('charge_name', ''), )
                continue

            amount = float(detail.get('amount', 0) or 0)
            qty = float(detail.get('qty', 1) or 1)
            price_unit = float(detail.get('rate_per_unit') or (amount / qty if qty != 0 else amount))
            name = detail.get('charge_name', '') or detail.get('reference_name', 'Purchase Item')

            # Resolve taxes from eZee tax children (ref_id=18)
            tax_ids = []
            detail_record_id = str(detail.get('detail_record_id', ''))
            for tax_detail in tax_children.get(detail_record_id, []):
                odoo_tax = self._resolve_tax_id(tax_detail)
                if odoo_tax:
                    tax_ids.append(odoo_tax.id)
                else:
                    missing_mappings += 1
                    _logger.warning('eZee purchase: no tax mapping for tax_id=%s '
                                    '(record=%s parent_detail=%s taxper=%s)', tax_detail.get('sub_ref2_value', ''),
                        record_id, detail_record_id, tax_detail.get('taxper', ''), )

            _logger.info('eZee purchase: line ref_id=%s account=%s(name=%s) amount=%s qty=%s '
                         'price_unit=%s tax_ids=%s', ref_id, account.code, account.name, amount, qty, price_unit,
                tax_ids, )

            invoice_line_vals.append({'account_id': account.id, 'name': name, 'quantity': qty, 'price_unit': price_unit,
                'tax_ids': [(6, 0, tax_ids)], })

        if not invoice_line_vals:
            _logger.warning('eZee purchase: no valid lines for record %s — bill not created', record_id, )
            return None, missing_mappings

        move = self.env['account.move'].create(
            {'move_type': 'in_invoice', 'partner_id': vendor.id, 'date': rec_date, 'invoice_date': rec_date,
                'ref': f'EZEEPURCHASE-{record_id}', 'journal_id': journal.id if journal else False,
                'narration': narration, 'invoice_line_ids': [(0, 0, lv) for lv in invoice_line_vals], })
        _logger.info('eZee purchase: bill created id=%s ref=%s total=%s lines=%d', move.id, move.ref, move.amount_total,
            len(invoice_line_vals), )

        # Post
        move.action_post()
        _logger.info('eZee purchase: bill %s posted (state=%s payment_state=%s)', move.ref, move.state,
            move.payment_state, )

        # Store eZee payment status
        balance = float(rec.get('balance', 0) or 0)
        amount_paid = float(rec.get('amount_paid', 0) or 0)
        total_amount = float(rec.get('total_amount', 0) or 0)
        is_paid = (balance == 0.0 and amount_paid >= total_amount)

        move.write({'ezee_balance': balance, 'ezee_payment_status': 'paid' if is_paid else 'unpaid', })
        _logger.info('eZee purchase: bill %s ezee_balance=%s ezee_payment_status=%s', move.ref, balance,
            'paid' if is_paid else 'unpaid', )

        # Auto-pay if eZee says paid
        if is_paid:
            _logger.info('eZee purchase: auto-paying bill %s (amount=%s)', move.ref, move.amount_total, )
            if not self._pay_invoice(move, config):
                _logger.error('eZee purchase: auto-pay failed for new bill %s', move.ref)

        return move, missing_mappings

    def _resolve_vendor(self, rec):
        """
        Matches eZee Vendor (ref_id 19) to Odoo res.partner
        """
        config = self._get_hotel_config()
        if not config:
            return None

        for detail in rec.get('details', []):
            if int(detail.get('reference_id', 0)) != 19:
                continue

            vendor_id = str(detail.get('sub_ref2_value', '') or '')
            MappingLine = self.env['ezee.optimus.account.mapping.line']
            line = MappingLine.search([('ezee_desc_unk_id', '=', vendor_id), ('hotel_id', '=', config.id), ], limit=1)

            if line and line.description:
                partner = self.env['res.partner'].search([('name', '=', line.description)], limit=1)
                if partner:
                    return partner
        return None

    def _get_pos_vendor(self, config):
        company = config.company_id
        name = 'POS Vendor - %s' % company.name
        partner = self.env['res.partner'].search([('name', '=', name)], limit=1)
        if not partner:
            partner = self.env['res.partner'].sudo().create({
                'name': name,
                'company_id': company.id,
                'supplier_rank': 1,
            })
            _logger.info('eZee purchase: created new POS vendor partner %s (id=%s)', name, partner.id)
        else:
            _logger.info('eZee purchase: found existing POS vendor partner %s (id=%s)', name, partner.id)
        return partner
