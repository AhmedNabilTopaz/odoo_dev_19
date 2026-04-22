from odoo import models, fields, api
from datetime import datetime
import logging
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)


class PMSSyncWizard(models.TransientModel):
    _name = 'pms.sync.wizard'
    _description = 'PMS Sync Wizard'

    hotel_ids = fields.Many2many('pms.credentials', string='Hotels', required=True)
    from_date = fields.Date(string='From Date', required=True, default=fields.Date.context_today)
    to_date = fields.Date(string='To Date', required=True, default=fields.Date.context_today)

    sync_sales = fields.Boolean(string='Sync Sales', default=True)
    sync_receipts = fields.Boolean(string='Sync Receipts', default=True)
    sync_payments = fields.Boolean(string='Sync Payments', default=True)
    sync_journals = fields.Boolean(string='Sync Journals', default=True)
    sync_incidentals = fields.Boolean(string='Sync Incidentals', default=True)

    def action_sync(self):
        failed = []

        for hotel in self.hotel_ids:
            mapping = self.env['pms.account.mapping'].search([
                ('hotel_id', '=', hotel.id)
            ], limit=1)
            if not mapping:
                raise UserError("No Mapping found for Hotel %s. Please Configure it" % hotel.name)
            from ..services.ezee_api_service import eZeeAPIService
            service = eZeeAPIService(hotel)

            # Ensure logged in
            if not hotel.auth_code:
                service.login()

            if self.sync_sales:
                data = service.fetch_data('sales', self.from_date, self.to_date)
                if self._process_sales(hotel, data) == "Failed":
                    failed.append('Sales')

            if self.sync_receipts:
                data = service.fetch_data('receipt', self.from_date, self.to_date)
                if self._process_receipts(hotel, data) == "Failed":
                    failed.append('Receipts')

            if self.sync_payments:
                data = service.fetch_data('payment', self.from_date, self.to_date)
                if self._process_payments(hotel, data) == "Failed":
                    failed.append('Payments')

            if self.sync_journals:
                data = service.fetch_data('journal', self.from_date, self.to_date)
                self._process_journals(hotel, data)

            if self.sync_incidentals:
                data = service.fetch_data('incidental', self.from_date, self.to_date)
                self._process_incidentals(hotel, data)

        if failed:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sync Completed with Errors',
                    'message': f'{", ".join(failed)} failed. Check Sync Logs for details.',
                    'type': 'danger',
                    'sticky': True,
                }
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sync Complete',
                'message': 'All selected data has been synced successfully.',
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def _process_sales(self, hotel, data):
        if not data: return "Failed"

        company = hotel.company_id

        records = data.get('data', []) if isinstance(data, dict) else data
        if not records or not isinstance(records, list): return

        income_account = self.env['account.account'].sudo().search([
            ('account_type', '=', 'income'),
        ], limit=1)

        for record in records:
            tran_id = record.get('record_id')
            bill_no = record.get('reference8')
            if not tran_id: continue

            existing = self.env['account.move'].sudo().search([
                ('pms_tran_id', '=', tran_id),
                ('pms_hotel_id', '=', hotel.id),
                ('move_type', '=', 'out_invoice'),
                ('invoice_date', '=', self._parse_ezee_date(record.get('record_date')))
            ])
            if existing:
                continue
                # existing.button_draft()
            company_partner, partner = self._get_or_create_partner(record, hotel)
            # partner.write({'company_id': False})
            ezee_total = self._parse_ezee_amount(
                record.get('total_amount') or record.get('TotalAmount') or record.get('Amount'))
            # Determine move type based on amount sign
            move_type = 'out_refund' if ezee_total < 0 else 'out_invoice'
            journal_id = self.env['account.journal'].sudo().search(
                [('type', '=', 'sale'), ('company_id', '=', company.id)], limit=1)
            if not journal_id:
                raise UserError("No sales journal found for company %s. Please create one" % company.name)
            invoice_vals = {
                'move_type': move_type,
                'partner_id': partner.id if partner else company_partner.id,
                'invoice_date': self._parse_ezee_date(record.get('record_date')) or fields.Date.today(),
                'invoice_date_due': self._parse_ezee_date(record.get('record_date')) or fields.Date.today(),
                'pms_tran_id': tran_id,
                'pms_hotel_id': hotel.id,
                'pms_reference': record.get('reference3'),  # Reservation No
                'journal_id': journal_id.id if journal_id else hotel.journal_id.id,
                'invoice_line_ids': [],
                'company_id': company.id if company else self.env.company.id,
                'ezee_id': record.get('record_id'),
                'ezee_guest_name': record.get('reference5'),
                'ezee_reservation_number': record.get('reference3'),
                'ezee_folio_number': record.get('reference4'),
                'ezee_type': record.get('reference14'),
                'ezee_room_number': record.get('reference13'),
                'ezee_checkin_date': self._parse_ezee_date(record.get('reference1')),
                'ezee_checkout_date': self._parse_ezee_date(record.get('reference2')),
                'ezee_receipt_no': bill_no,  # Bill No
                'ezee_amount': ezee_total,
                'ezee_rate_plan': record.get('reference6'),
                'ezee_source': record.get('reference7'),
                'ezee_rate_type': record.get('reference15'),
                'ezee_market': record.get('reference16'),
                'ezee_company_tax_id': record.get('reference17'),
                'ezee_tax_number': record.get('reference18'),
                'ezee_bill_name': record.get('reference9'),
                'ezee_voucher_no': record.get('reference10'),
                'ezee_bill_no': bill_no,
                'ezee_email': record.get('reference19'),
                'ezee_address': record.get('reference22'),
                'ezee_address_line': record.get('reference20'),
                'ezee_address1': record.get('reference23'),
                'ezee_address2': record.get('reference24'),
                'ezee_address_line2': record.get('reference21'),
                'ezee_address3': record.get('reference25'),
                'ezee_country': record.get('reference26'),
                'ezee_registration_no': record.get('reference27'),
                'ezee_booking_no': record.get('reference10'),
                'bussiness_source_name': record.get('reference10'),

            }
            lines = {}
            tax_ids = []
            municipality_lines = {}  # separate dict to hold municipality extra lines
            for detail in record.get('detail', []):
                record_id = detail['detail_record_id']
                amount = float(detail.get('amount', 0) or 0)
                ref_name = detail.get('reference_name')
                line_name = detail.get('charge_name') or 'PMS Charge'
                amount = self._parse_ezee_amount(detail.get('amount'))
                reference_id = detail['reference_id']
                sub_ref2_value=detail['sub_ref2_value']
                sub_ref2_id=detail['sub_ref2_id']
                if move_type == 'out_refund':
                    amount = abs(amount)
                if record_id not in lines:
                    tax_ids = []
                    mapping = self.env['pms.account.mapping'].sudo().search([
                        ('pms_account_header_id', '=',
                         int(detail.get('reference_id')) if detail.get('reference_id') else 0),
                        ('hotel_id', '=', hotel.id)
                    ], limit=1)
                    account_id = False
                    if mapping:
                        mapping_line=False
                        if sub_ref2_value:
                            mapping_line = self.env['pms.account.mapping.line'].search([
                    ('mapping_id', '=', mapping.id),
                    ('pms_account_id', '=', sub_ref2_value),('hotel_id','=',hotel.id)
                ], limit=1)
                        if mapping_line and mapping_line.account_id:
                            account_id=mapping_line.account_id.id
                        else:
                            account_id = mapping.account_id.id
                    elif hotel.journal_id.default_account_id:
                        account_id = hotel.journal_id.default_account_id.id
                    elif income_account:
                        account_id = income_account.id
                    lines[record_id] = {
                        'name': line_name,
                        'discount': 0,
                        'account_id': account_id,
                        'price_unit': amount,
                        'quantity': 1,
                        'tax_ids': [],
                        'analytic_distribution': {
                            str(hotel.analytic_account_id.id): 100} if hotel.analytic_account_id else {},
                    }

                if ref_name == 'Taxes':
                    charge_name = detail.get('charge_name')
                    tax_ref_id = str(detail.get('sub_ref2_value'))
                    if 'municipality' in str(charge_name).lower():
                        # ── MUNICIPALITY: create a dedicated invoice line with VAT applied ──
                        muni_amount = abs(self._parse_ezee_amount(detail.get('amount')))
                        vat_tax = self.env['account.tax'].sudo().search([
                            ('type_tax_use', '=', 'sale'),
                            ('amount_type', '=', 'percent'),
                            ('amount', '=', 15.0),
                        ], limit=1)

                        # Search mapping for municipality account
                        mapping = self.env['pms.tax.mapping'].sudo().search([
                            ('hotel_id', '=', hotel.id),
                            '|',
                            ('pms_tax_id', '=', tax_ref_id),
                            ('pms_tax_name', '=', charge_name)
                        ], limit=1)
                        if mapping and mapping.tax_id:
                            muni_account_id = mapping.tax_id.invoice_repartition_line_ids.filtered(
                                lambda l: l.repartition_type == 'tax'
                            ).mapped('account_id')[:1].id or account_id or (
                                                  income_account.id if income_account else False)
                        else:
                            muni_account_id = account_id or (income_account.id if income_account else False)
                        muni_line_key = 'municipality_%s' % record_id
                        if muni_line_key not in municipality_lines:
                            municipality_lines[muni_line_key] = {
                                'name': charge_name or 'Municipality Tax',
                                'discount': 0,
                                'account_id': muni_account_id,
                                'price_unit': muni_amount,
                                'quantity': 1,
                                'tax_ids': [(6, 0, vat_tax.ids)] if vat_tax else [],
                                'analytic_distribution': {
                                    str(hotel.analytic_account_id.id): 100} if hotel.analytic_account_id else {},
                            }
                        else:
                            municipality_lines[muni_line_key]['price_unit'] += muni_amount

                    else:
                        mapping = self.env['pms.tax.mapping'].sudo().search([
                            ('hotel_id', '=', hotel.id),
                            '|',
                            ('pms_tax_id', '=', tax_ref_id),
                            ('pms_tax_name', '=', charge_name)
                        ], limit=1)
                        if mapping and mapping.tax_id:
                            tax_id = mapping.tax_id
                        else:
                            tax_id = self.env['account.tax'].sudo().search([
                                ('type_tax_use', '=', 'sale'),
                                ('name', '=', charge_name),
                            ], limit=1)

                        if tax_id:
                            if not tax_id.include_base_amount:
                                tax_id.include_base_amount = True  # or fix it in UI
                            # أضف المعرف للمصفوفة الخاصة بهذا السطر
                            if tax_id.id not in lines[record_id]['tax_ids']:
                                lines[record_id]['tax_ids'].append(tax_id.id)

            if lines:
                for record_id, line_vals in lines.items():
                    if line_vals['tax_ids']:
                        # نقوم بجلب الضرائب وترتيبها حسب الـ Sequence الموجود في إعدادات أودو
                        # إذا كنت وضعت الـ 15% بـ sequence أقل (مثلاً 5) والـ 2.5% بـ sequence (مثلاً 10)
                        # فإن أودو سيطبقها بالترتيب الصحيح
                        ordered_taxes = self.env['account.tax'].browse(line_vals['tax_ids']).sorted(
                            key=lambda t: t.sequence)

                        # نضع الضرائب المرتبة في سطر الفاتورة
                        line_vals['tax_ids'] = [(6, 0, ordered_taxes.ids)]

                    invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
            # Append municipality lines (each gets its own invoice line with VAT)
            for muni_line_vals in municipality_lines.values():
                invoice_vals['invoice_line_ids'].append((0, 0, muni_line_vals))

            if invoice_vals['invoice_line_ids']:
                inv = self.env['account.move'].sudo().create(invoice_vals)

                mapping = self.env['pms.account.mapping'].sudo().search([
                    ('pms_account_header_name', '=', 'Guest Ledger'),
                    ('hotel_id', '=', hotel.id)
                ], limit=1)
                receivable_account_id = mapping.account_id if mapping else False

                # Force receivable line to use individual partner's account, not the company's
                if receivable_account_id:
                    for line in inv.line_ids:
                        if not inv.partner_id.is_company and line.account_id.account_type == 'asset_receivable' :
                            line.account_id = receivable_account_id
                            # ✅ Add this: ensure due date is set on receivable lines
                            if not line.date_maturity:
                                line.date_maturity = inv.invoice_date_due or inv.invoice_date or fields.Date.today()

                if any(inv.invoice_line_ids.mapped('tax_ids')):
                    inv._compute_tax_totals()

                if any(line.price_unit != 0.0 for line in inv.invoice_line_ids):
                    inv.action_post()
        return "Success"

    def _parse_ezee_amount(self, value):
        """Robust float parsing for eZee amounts"""
        if not value:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        try:

            clean_value = str(value).replace(',', '').strip()
            return float(clean_value)
        except:
            return 0.0

    def _parse_ezee_date(self, date_str):
        """Helper to parse dates from eZee API (DD/MM/YYYY or YYYY-MM-DD)"""
        if not date_str:
            return False

        date_str = str(date_str).split(' ')[0]

        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            # Try DD/MM/YYYY (eZee UI format)
            try:
                return datetime.strptime(date_str, '%d/%m/%Y').date()
            except:
                try:
                    return fields.Date.from_string(date_str)
                except:
                    return False

    def _get_or_create_partner(self, record, hotel=False):
        company = self.env.company
        if hotel:
            company = hotel.company_id
        name = record.get('reference5') or 'Guest'
        email = record.get('reference19')
        address = record.get('reference22')
        ezee_address1 = record.get('reference23')
        ezee_address2 = record.get('reference24')
        ezee_address_line2 = record.get('reference21')

        if 'Company' in str(record.get('reference17')):
            partner_type = 'company'
            mapping = self.env['pms.account.mapping'].sudo().search([
                ('pms_account_header_name', '=', 'City Ledger'),
                ('hotel_id', '=', hotel.id)
            ], limit=1)
            company_name = record.get('reference7') or record.get('reference5')
            person_name = record.get('reference5') or 'Guest'
        else:
            partner_type = 'person'
            mapping = self.env['pms.account.mapping'].sudo().search([
                ('pms_account_header_name', '=', 'Guest Ledger'),
                ('hotel_id', '=', hotel.id)
            ], limit=1)

        if mapping and mapping.account_id:
            default_receivable = mapping.account_id
        else:
            default_receivable = company.account_default_pos_receivable_account_id or self.env[
                'account.account'].sudo().search(
                [('account_type', '=', 'asset_receivable')], limit=1)

        if partner_type == 'company':
            # Get or create the company partner
            company_partner = self.env['res.partner'].sudo().search([
                ('name', '=', company_name),
                ('is_company', '=', True),
                ('company_id', '=', company.id),
                ('active', '=', True),
            ], limit=1)

            if not company_partner:
                company_partner = self.env['res.partner'].sudo().create({
                    'company_id': company.id,
                    'name': company_name,
                    'email': email,
                    'street': address,
                    'street2': ezee_address1,
                    'city': ezee_address2,
                    'phone': ezee_address_line2,
                    'company_type': 'company',
                    'is_company': True,
                    'property_account_receivable_id': default_receivable.id,
                })
            else:
                if not company_partner.property_account_receivable_id or company_partner.property_account_receivable_id != default_receivable:
                    company_partner.write({'property_account_receivable_id': default_receivable.id})
            person_partner = False
            if record.get('reference7') and record.get('reference5'):
                # Get or create the person contact linked to the company
                person_partner = self.env['res.partner'].sudo().search([
                    ('name', '=', person_name),
                    ('parent_id', '=', company_partner.id),
                    ('is_company', '=', False),
                    ('active', '=', True),
                    ('company_id', '=', company.id),

                ], limit=1)
                mapping = self.env['pms.account.mapping'].sudo().search([
                    ('pms_account_header_name', '=', 'Guest Ledger'),
                    ('hotel_id', '=', hotel.id)
                ], limit=1)
                if not person_partner:
                    person_partner = self.env['res.partner'].sudo().create({
                        'company_id': company.id,
                        'name': person_name,
                        'email': email,
                        'street': address,
                        'street2': ezee_address1,
                        'city': ezee_address2,
                        'phone': ezee_address_line2,
                        'company_type': 'person',
                        'is_company': False,
                        'parent_id': company_partner.id,  # Link person to company
                        'property_account_receivable_id': mapping.account_id.id if mapping and mapping.account_id else default_receivable.id,
                    })
                else:
                    if not person_partner.property_account_receivable_id or person_partner.property_account_receivable_id != default_receivable:
                        person_partner.write({
                            'property_account_receivable_id': mapping.account_id.id if mapping and mapping.account_id else default_receivable.id})
                if person_partner.company_id.id != company.id:
                    person_partner.sudo().write({'company_id': company.id})
            return company_partner, person_partner  # Return the person contact (linked to company)

        else:
            # Original logic for non-company partners
            partner = self.env['res.partner'].sudo().search([('name', '=', name)
                                                                , ('company_id', '=', company.id),
                                                             ('active', '=', True),
                                                             ], limit=1)
            if not partner:
                partner = self.env['res.partner'].sudo().create({
                    'company_id': company.id,
                    'name': name,
                    'email': email,
                    'street': address,
                    'street2': ezee_address1,
                    'city': ezee_address2,
                    'phone': ezee_address_line2,
                    'company_type': 'person',
                    'property_account_receivable_id': default_receivable.id,
                })
            else:
                if not partner.property_account_receivable_id or partner.property_account_receivable_id != default_receivable:
                    partner.write({'property_account_receivable_id': default_receivable.id})
            if partner.company_id.id != company.id:
                partner.sudo().write({'company_id': company.id})
            return None, partner

    def _process_receipts(self, hotel, data):
        company = hotel.company_id
        if not company:
            company = self.env.company
        if not data or data.get('status') != 'Success': return "Failed"
        for group in data.get('data', []):
            type = group.get('type')
            for record in group.get('data', []):
                existing = self.env['account.payment'].sudo().search([
                    ('pms_tran_id', '=', record['tranId']),
                    ('pms_hotel_id', '=', hotel.id),
                    ('date', '=', record['tran_datetime'])
                ])
                if existing: continue

                company_partner, partner = self._get_or_create_partner({'reference5': record.get('reference2')
                                                                           , 'reference7': record.get('reference7')
                                                                           , 'reference22': record.get('reference22')
                                                                           , 'reference21': record.get('reference21')
                                                                           , 'reference23': record.get('reference23')
                                                                           , 'reference24': record.get('reference24')
                                                                           , 'reference17': record.get('reference17')},
                                                                       hotel)
                # if partner.company_id:
                #     partner.write({'company_id': False})
                journal_id = hotel.journal_id
                if type == 'Advance Deposit':
                    if 'CASH' in str(record.get('reference14')).upper():
                        journal_id = self.env['account.journal'].sudo().search(
                            [('type', '=', 'cash'), ('company_id', '=', company.id)], limit=1) or journal_id
                    else:
                        journal_id = self.env['account.journal'].sudo().search(
                            [('type', '=', 'bank'), ('company_id', '=', company.id)], limit=1) or journal_id
                if type == 'Received From Guest' or type == 'Received From Cityledger':
                    if 'CASH' in str(record.get('reference14')).upper():
                        journal_id = self.env['account.journal'].sudo().search(
                            [('type', '=', 'cash'), ('company_id', '=', company.id)], limit=1) or journal_id
                    else:
                        journal_id = self.env['account.journal'].sudo().search(
                            [('type', '=', 'bank'), ('company_id', '=', company.id)], limit=1) or journal_id
                payment_method_line = (
                        journal_id._get_available_payment_method_lines('inbound')[:1]
                        or journal_id.inbound_payment_method_line_ids[:1]
                )
                # if partner.id == 53 or partner.id == 52 or partner.id == 59:
                #     partner = self.env['res.partner'].browse(162)
                if not payment_method_line:
                    raise UserError(
                        "No payment method found for journal %s. Please configure at least one." % journal_id.name)
                payment_vals = {
                    'payment_type': 'inbound',
                    'company_id': company.id if company else journal_id.env.company.id,
                    'partner_type': 'customer',
                    'date': record['tran_datetime'],
                    'pms_tran_id': record['tranId'],
                    'pms_hotel_id': hotel.id,
                    'pms_reference': record.get('reference1'),  # Receipt No
                    'journal_id': journal_id.id if journal_id else hotel.journal_id.id,
                    'partner_id': partner.id if partner else company_partner.id,
                    'payment_method_line_id': payment_method_line.id,
                    'amount': self._parse_ezee_amount(
                        record.get('gross_amount') or record.get('TotalAmount') or record.get('Amount')),
                    'ezee_reservation_number': record.get('reference4'),
                    'ezee_id': record.get('tranId'),
                    'ezee_guest_name': record.get('reference2'),
                    'ezee_folio_number': record.get('reference5'),
                    'ezee_type': record.get('reference14'),
                    'ezee_room_number': record.get('reference13'),
                    'ezee_checkin_date': self._parse_ezee_date(record.get('reference8')),
                    'ezee_checkout_date': self._parse_ezee_date(record.get('reference9')),
                    'ezee_receipt_no': record.get('reference1'),
                    'ezee_payment_method': record.get('reference14'),
                    'ezee_voucher_type': type,
                    'ezee_amount': self._parse_ezee_amount(
                        record.get('gross_amount') or record.get('"amount_paid') or record.get('Amount')),
                    'market': record.get('reference12'),
                    'remarks': '',
                    'bussiness_source_name': record.get('reference10'),
                    'ezee_credit_number': record.get('reference15'),
                    'ezee_voucher_number': record.get('reference11'),
                    'ezee_bill_name': record.get('reference7'),
                    'ezee_invoice_no': record.get('reference6'),
                    'ezee_room_number': record.get('reference13'),
                }

                payment = self.env['account.payment'].sudo().create(payment_vals)

                payment.action_post()
                payment.action_validate()
                mapping_name = None
                if type == 'Advance Deposit':
                    mapping_name = 'Advance From Guest'
                elif type == 'Received From Guest':
                    mapping_name = 'Guest Ledger'
                elif type == 'Received From Cityledger':
                    mapping_name = 'City Ledger'

                if mapping_name:
                    mapping = self.env['pms.account.mapping'].sudo().search([
                        ('pms_account_header_name', '=', mapping_name),
                        ('hotel_id', '=', hotel.id)

                    ], limit=1)
                    if mapping and mapping.account_id:
                        credit_line = payment.move_id.line_ids.filtered(
                            lambda l: l.credit > 0
                        )[:1]
                        if credit_line:
                            credit_line.with_context(check_move_validity=False).write({
                                'account_id': mapping.account_id.id,
                            })
                            payment.move_id.with_context(check_move_validity=False)._synchronize_business_models(
                                ['line_ids'])

        return "Success"

    def _process_payments(self, hotel, data):
        company = hotel.company_id
        if not company:
            company = self.env.company
        if not data or data.get('status') != 'Success':
            return "Failed"
        for group in data.get('data', []):
            type = group.get('type')
            for record in group.get('data', []):
                existing = self.env['account.payment'].sudo().search([
                    ('pms_tran_id', '=', record['tranId']),
                    ('pms_hotel_id', '=', hotel.id),
                    ('date', '=', record['tran_datetime'])
                ])
                if existing: continue

                company_partner, partner = self._get_or_create_partner({'reference5': record.get('reference2')
                                                                           , 'reference7': record.get('reference7')
                                                                           , 'reference22': record.get('reference23')
                                                                           , 'reference21': record.get('reference21')
                                                                           , 'reference23': record.get('reference23')
                                                                           , 'reference24': record.get('reference24')
                                                                           , 'reference17': record.get('reference17')},
                                                                       hotel)
                # if partner.company_id:
                #     partner.write({'company_id': False})
                journal_id = hotel.journal_id
                debit_account = False
                if type == 'General Expense':
                    if 'CASH' or 'CREDIT' in str(record.get('reference14')).upper():
                        journal_id = self.env['account.journal'].sudo().search(
                            [('type', '=', 'cash'), ('company_id', '=', company.id)], limit=1) or journal_id
                    else:
                        journal_id = self.env['account.journal'].sudo().search(
                            [('type', '=', 'bank'), ('company_id', '=', company.id)], limit=1) or journal_id
                if type == 'Advance Deposit Refund':
                    if 'CASH' or 'CREDIT' in str(record.get('reference14')).upper():
                        journal_id = self.env['account.journal'].sudo().search(
                            [('type', '=', 'cash'), ('company_id', '=', company.id)], limit=1) or journal_id
                    else:
                        journal_id = self.env['account.journal'].sudo().search(
                            [('type', '=', 'bank'), ('company_id', '=', company.id)], limit=1) or journal_id

                if type == 'Guest Refund' or type == 'Cityledger Refund':
                    if 'CASH' or 'CREDIT' in str(record.get('reference14')).upper():
                        journal_id = self.env['account.journal'].sudo().search(
                            [('type', '=', 'cash'), ('company_id', '=', company.id)], limit=1) or journal_id
                    else:
                        journal_id = self.env['account.journal'].sudo().search(
                            [('type', '=', 'bank'), ('company_id', '=', company.id)], limit=1) or journal_id
                payment_method_line = (
                        journal_id._get_available_payment_method_lines('outbound')[:1]
                        or journal_id.inbound_payment_method_line_ids[:1]
                )
                payment_vals = {
                    'payment_type': 'outbound',
                    'company_id': company.id if company else journal_id.env.company.id,
                    'partner_type': 'customer',
                    'date': record['tran_datetime'],
                    'pms_tran_id': record['tranId'],
                    'pms_hotel_id': hotel.id,
                    'pms_reference': record.get('reference1'),  # Receipt No
                    'journal_id': journal_id.id if journal_id else hotel.journal_id.id,
                    'partner_id': partner.id if partner else company_partner.id,
                    'payment_method_line_id': payment_method_line.id,
                    'amount': self._parse_ezee_amount(
                        record.get('gross_amount') or record.get('TotalAmount') or record.get('Amount')),
                    'ezee_reservation_number': record.get('reference4'),
                    'ezee_id': record.get('tranId'),
                    'ezee_guest_name': record.get('reference2'),
                    'ezee_folio_number': record.get('reference5'),
                    'ezee_type': record.get('reference14'),
                    'ezee_room_number': record.get('reference13'),
                    'ezee_checkin_date': self._parse_ezee_date(record.get('reference8')),
                    'ezee_checkout_date': self._parse_ezee_date(record.get('reference9')),
                    'ezee_receipt_no': record.get('reference1'),
                    'ezee_payment_method': record.get('reference14'),
                    'ezee_voucher_type': type,
                    'ezee_amount': self._parse_ezee_amount(
                        record.get('gross_amount') or record.get('"amount_paid') or record.get('Amount')),
                }

                payment = self.env['account.payment'].sudo().create(payment_vals)
                payment.action_post()
                payment.action_validate()
                mapping_name = None
                if type == 'Advance Deposit Refund':
                    mapping_name = 'Advance From Guest'
                elif type == 'Guest Refund':
                    mapping_name = 'Guest Ledger'
                elif type == 'Cityledger Refund':
                    mapping_name = 'City Ledger'
                elif type == 'General Expense':
                    mapping_name = 'Paid Out'
                if mapping_name:
                    mapping = self.env['pms.account.mapping'].sudo().search([
                        ('pms_account_header_name', '=', mapping_name),
                        ('hotel_id', '=', hotel.id)
                    ], limit=1)
                    if mapping and mapping.account_id:
                        debit_line = payment.move_id.line_ids.filtered(
                            lambda l: l.debit > 0
                        )[:1]
                        if debit_line:
                            debit_line.with_context(check_move_validity=False).write({
                                'account_id': mapping.account_id.id,
                            })
                            payment.move_id.with_context(check_move_validity=False)._synchronize_business_models(
                                ['line_ids'])

        return "Success"

    def _process_journals(self, hotel, data):
        if not data or data.get('status') != 'Success': return
        company = hotel.company_id

        for group in data.get('data', []):
            for record in group.get('data', []):
                type = group.get('type')
                existing = self.env['account.move'].sudo().search([
                    ('pms_tran_id', '=', record['tranId']),
                    ('pms_hotel_id', '=', hotel.id),
                    ('move_type', '=', 'entry'),
                    ('date', '=', record['tran_datetime'])
                ])
                if existing: continue

                company_partner, partner = self._get_or_create_partner(
                    {'reference5': record.get('reference2') or 'Guest'
                        , 'reference7': record.get('reference13')
                        , 'reference22': record.get('reference22')
                        , 'reference21': record.get('reference21')
                        , 'reference23': record.get('reference23')
                        , 'reference24': record.get('reference24')
                        , 'reference17': record.get('reference17')}, hotel)

                move_vals = {
                    'move_type': 'entry',
                    'date': record['tran_datetime'],
                    'pms_tran_id': record['tranId'],
                    'pms_hotel_id': hotel.id,
                    'pms_reference': record.get('reference1'),
                    'journal_id': hotel.debt_transfer_journal_id.id if hotel.debt_transfer_journal_id and type == 'Cityledger Transfer' else hotel.journal_id.id,
                    'company_id': company.id if company else self.env.company.id,
                    'line_ids': [],
                }

                for detail in record.get('detail', []):
                    receivable_account = partner.property_account_receivable_id if partner else company_partner.property_account_receivable_id or \
                                                                                                self.env[
                                                                                                    'account.account'].sudo().search(
                                                                                                    [
                                                                                                        ('account_type',
                                                                                                         '=',
                                                                                                         'asset_receivable'),
                                                                                                        ('company_ids',
                                                                                                         'in',
                                                                                                         company.id)
                                                                                                    ], limit=1)
                    if type == 'Advance Deposit Transfer':
                        mapping_name = 'Advance From Guest'
                    elif type == 'Folio Transfer':
                        mapping_name = 'Folio Transfer'
                    elif type == 'Cityledger Transfer':
                        mapping_name = 'City Ledger'
                        mapping = self.env['pms.account.mapping'].sudo().search([
                            ('pms_account_header_name', '=', 'Guest Ledger'),
                            ('hotel_id', '=', hotel.id)
                        ], limit=1)
                        receivable_account = mapping.account_id if mapping else receivable_account
                    elif type == 'Cityledger Commision':
                        mapping_name = 'Paid Out'
                    if mapping_name:
                        mapping = self.env['pms.account.mapping'].sudo().search([
                            ('pms_account_header_name', '=', mapping_name),
                            ('hotel_id', '=', hotel.id)
                        ], limit=1)

                    account_id = mapping.account_id.id if mapping else None
                    if not account_id: continue

                    amount = float(detail.get('amount', 0))
                    if detail.get('tran_type') == 'Dr':
                        line_name = (mapping.pms_account_header_name if mapping else False) or \
                                    detail.get('reference_value') or \
                                    (mapping.account_id.name if mapping else False) or \
                                    'PMS Journal'

                        move_vals['line_ids'].append((0, 0, {
                            'name': line_name,
                            'partner_id': company_partner.id if company_partner else partner.id,
                            'account_id': account_id,
                            'debit': amount,
                            'credit': 0,
                            'analytic_distribution': {
                                str(hotel.analytic_account_id.id): 100} if hotel.analytic_account_id else {},
                        }))
                    else:
                        move_vals['line_ids'].append((0, 0, {
                            'name': line_name,
                            'partner_id': partner.id if partner else company_partner.id,
                            'account_id': receivable_account.id if receivable_account else account_id.id,
                            'debit': 0,
                            'credit': amount,
                            'analytic_distribution': {
                                str(hotel.analytic_account_id.id): 100} if hotel.analytic_account_id else {},
                        }))
                if move_vals['line_ids']:
                    self.env['account.move'].sudo().create(move_vals).action_post()

    def _process_incidentals(self, hotel, data):
        company = hotel.company_id
        income_account = self.env['account.account'].sudo().search([
            ('account_type', '=', 'income'),
        ], limit=1)
        if not data or data.get('status') != 'Success': return
        for group in data.get('data', []):
            for record in group.get('data', []):
                existing = self.env['account.move'].sudo().search([
                    ('pms_tran_id', '=', record['tranId']),
                    ('pms_hotel_id', '=', hotel.id),
                    ('move_type', '=', 'out_invoice'),
                    ('invoice_date', '=', self._parse_ezee_date(record.get('record_date')))
                ])
                if existing: continue
                ezee_total = self._parse_ezee_amount(
                    record.get('gross_amount') or record.get('TotalAmount') or record.get('Amount'))
                company_partner, partner = self._get_or_create_partner({'reference5': record.get('reference1')
                                                                           , 'reference7': record.get('reference7')
                                                                           , 'reference22': record.get('reference22')
                                                                           , 'reference21': record.get('reference21')
                                                                           , 'reference23': record.get('reference23')
                                                                           , 'reference24': record.get('reference24')
                                                                           , 'reference17': record.get('reference17')},
                                                                       hotel)
                # partner.write({'company_id': False})
                journal_id = self.env['account.journal'].sudo().search(
                    [('type', '=', 'sale'), ('company_id', '=', company.id)], limit=1)
                if not journal_id:
                    raise UserError("No sales journal found for company %s. Please create one" % company.name)

                invoice_vals = {
                    'move_type': 'out_invoice',
                    'partner_id': partner.id if partner else company_partner.id,
                    'invoice_date': self._parse_ezee_date(record.get('tran_datetime')) or fields.Date.today(),
                    'pms_tran_id': record['tranId'],
                    'pms_hotel_id': hotel.id,
                    'pms_reference': record.get('reference3'),  # Reservation No
                    'journal_id': journal_id.id if journal_id else hotel.journal_id.id,
                    'invoice_line_ids': [],
                    'company_id': company.id if company else self.env.company.id,
                    'ezee_id': record.get('tranId'),
                    'ezee_guest_name': record.get('reference1'),
                    'ezee_type': record.get('reference14'),
                    'ezee_receipt_no': record.get('reference3'),  # Bill No
                    'ezee_amount': ezee_total,
                }
                lines = {}
                tax_ids = []
                for detail in record.get('detail', []):
                    ref_name = detail.get('reference_value')

                    parent_id = detail['parentid']

                    if parent_id == '':
                        record_id = detail['detailId']
                    if (parent_id == '' or parent_id not in lines) and detail.get('tran_type') == 'Cr':
                        tax_ids = []
                        mapping = self.env['pms.account.mapping'].sudo().search([
                            ('pms_account_header_id', '=',
                             int(detail.get('reference_id')) if detail.get('reference_id') else 0),
                            ('hotel_id', '=', hotel.id)
                        ], limit=1)
                        account_id = False
                        if mapping:
                            account_id = mapping.account_id.id
                        elif hotel.journal_id.default_account_id:
                            account_id = hotel.journal_id.default_account_id.id
                        elif income_account:
                            account_id = income_account.id
                        lines[record_id] = {
                            'name': detail.get('reference_value') + " " + detail.get('remark') or 'Incidental Charge',
                            'discount': 0,
                            'account_id': account_id,
                            'price_unit': float(detail.get('amount', 0)),
                            'tax_ids': [],
                            'quantity': 1,
                            'tax_ids': [],
                            'analytic_distribution': {
                                str(hotel.analytic_account_id.id): 100} if hotel.analytic_account_id else {},
                        }
                    if ref_name == 'Tax':
                        charge_name = 'VAT 15%'
                        tax_ref_id = str(detail.get('sub_reference2_value'))
                        mapping = self.env['pms.tax.mapping'].sudo().search([
                            ('hotel_id', '=', hotel.id),
                            ('pms_tax_id', '=', tax_ref_id),
                        ], limit=1)
                        if mapping and mapping.tax_id:
                            tax_id = mapping.tax_id
                        else:
                            tax_id = self.env['account.tax'].sudo().search([
                                ('type_tax_use', '=', 'sale'),
                                ('name', '=', charge_name),
                            ], limit=1)

                        if tax_id:
                            if not tax_id.include_base_amount:
                                tax_id.include_base_amount = True  # or fix it in UI
                            # أضف المعرف للمصفوفة الخاصة بهذا السطر
                            if record_id and tax_id.id not in lines[record_id]['tax_ids']:
                                lines[record_id]['tax_ids'].append(tax_id.id)

                if lines:
                    for record_id, line_vals in lines.items():
                        if line_vals['tax_ids']:
                            # نقوم بجلب الضرائب وترتيبها حسب الـ Sequence الموجود في إعدادات أودو
                            # إذا كنت وضعت الـ 15% بـ sequence أقل (مثلاً 5) والـ 2.5% بـ sequence (مثلاً 10)
                            # فإن أودو سيطبقها بالترتيب الصحيح
                            ordered_taxes = self.env['account.tax'].browse(line_vals['tax_ids']).sorted(
                                key=lambda t: t.sequence)

                            # نضع الضرائب المرتبة في سطر الفاتورة
                            line_vals['tax_ids'] = [(6, 0, ordered_taxes.ids)]

                        invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                if invoice_vals['invoice_line_ids']:
                    invoice = self.env['account.move'].sudo().create(invoice_vals)

                    mapping = self.env['pms.account.mapping'].sudo().search([
                        ('pms_account_header_name', '=', 'Guest Ledger'),
                        ('hotel_id', '=', hotel.id)
                    ], limit=1)
                    receivable_account_id = mapping.account_id if mapping else False

                    # Force receivable line to use individual partner's account, not the company's
                    if receivable_account_id:
                        for line in invoice.line_ids:
                            if not invoice.partner_id.is_company and line.debit > 0:
                                line.account_id = receivable_account_id
                    # 2. Confirm (validate) the invoice
                    invoice.action_post()
                    # Get the invoice's receivable account
                    # Use the wizard-based payment registration programmatically
                    # Find payment journal with fallback
                    payment_journal = self.env['account.journal'].sudo().search([
                        ('type', 'in', ['bank', 'cash']),
                        ('company_id', '=', invoice.company_id.id),
                    ], limit=1)
                    if 'CASH' in str(record.get('reference14')).upper():
                        payment_journal = self.env['account.journal'].sudo().search(
                            [('type', '=', 'cash'), ('company_id', '=', company.id)], limit=1) or journal_id
                    else:
                        payment_journal = self.env['account.journal'].sudo().search(
                            [('type', '=', 'bank'), ('company_id', '=', company.id)], limit=1) or journal_id

                    if not payment_journal:
                        raise UserError(
                            "No bank or cash journal found. Please create one in Accounting → Configuration → Journals.")

                    payment_register = self.env['account.payment.register'].with_context(
                        active_model='account.move',
                        active_ids=invoice.ids,
                    ).sudo().create({
                        'payment_date': invoice.invoice_date or fields.Date.today(),
                        'journal_id': payment_journal.id,
                        'amount': invoice.amount_residual,
                    })

                    payment_register._create_payments()
                #     payment_vals = {
                #         'payment_type': 'inbound',
                #         'partner_type': 'customer',
                #         'partner_id': invoice.partner_id.id,
                #         'amount': invoice.amount_residual,
                #         'currency_id': invoice.currency_id.id,
                #         'journal_id': payment_journal.id,
                #         'date': invoice.invoice_date or fields.Date.today(),
                #         'memo': invoice.name,
                #         'company_id': invoice.company_id.id,
                #     }

                #     payment = self.env['account.payment'].create(payment_vals)
                #     payment.action_post()

                #     # Fix the payment receivable line to match the invoice receivable account
                #     payment_receivable_line = payment.move_id.line_ids.filtered(
                #         lambda l: l.account_type == 'asset_receivable'
                #     )

                #     if payment_receivable_line.account_id != invoice_receivable_account:
                #         payment_receivable_line.with_context(check_move_validity=False).write({
                #             'account_id': invoice_receivable_account.id,
                #         })

                #     # Reconcile
                #     domain = [
                #         ('account_type', 'in', ('asset_receivable', 'liability_payable')),
                #         ('reconciled', '=', False),
                #     ]
                #     payment_lines = payment.move_id.line_ids.filtered_domain(domain)
                #     invoice_lines = invoice.line_ids.filtered_domain(domain)

                #     (payment_lines + invoice_lines).reconcile()
        return "Success"
