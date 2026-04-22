from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    pms_tran_id = fields.Char(string='PMS Transaction ID', copy=False, index=True)
    pms_hotel_id = fields.Many2one('pms.credentials', string='PMS Hotel', copy=False)
    pms_reference = fields.Char(string='PMS Reference', copy=False)
    
    # eZee Info fields
    ezee_id = fields.Char(string='Ezee ID', readonly=True, copy=False)
    ezee_guest_name = fields.Char(string='Guest Name', readonly=True, copy=False)
    ezee_reservation_number = fields.Char(string='Reservation Number', readonly=True, copy=False)
    ezee_folio_number = fields.Char(string='Folio Number', readonly=True, copy=False)
    ezee_type = fields.Char(string='Room Type', readonly=True, copy=False)
    ezee_room_number = fields.Char(string='Room Number', readonly=True, copy=False)
    ezee_checkin_date = fields.Date(string='Check-In Date', readonly=True, copy=False)
    ezee_checkout_date = fields.Date(string='Check-Out Date', readonly=True, copy=False)
    ezee_receipt_no = fields.Char(string='Receipt No', readonly=True, copy=False)
    ezee_amount = fields.Float(string='Amount', readonly=True, copy=False)
    ezee_rate_plan = fields.Char(string='Rate Plan', readonly=True, copy=False)
    ezee_source = fields.Char(string='Source', readonly=True, copy=False)
    ezee_bill_no=fields.Char(string='Bill Number', readonly=True, copy=False)
    ezee_bill_name=fields.Char(string='Bill To Name', readonly=True, copy=False)
    ezee_voucher_no=fields.Char(string='Voucher Number', readonly=True, copy=False)
    ezee_voucher_name=fields.Char(string='Voucher Name', readonly=True, copy=False)
    ezee_rate_type=fields.Char(string='Rate Type', readonly=True, copy=False)   
    ezee_market=fields.Char(string='Market', readonly=True, copy=False)
    ezee_company_tax_id=fields.Char(string='Identity Card Type', readonly=True, copy=False)
    ezee_tax_number=fields.Char(string='Card Number', readonly=True, copy=False)
    is_sale_installed = fields.Boolean()
    ezee_email = fields.Char(string='Email Address', readonly=True, copy=False)
    ezee_address = fields.Char(string='Address', readonly=True, copy=False)
    ezee_address_line = fields.Char(string='Address Line', readonly=True, copy=False)
    ezee_address1 = fields.Char(string='Address Line 1', readonly=True, copy=False)
    ezee_address2 = fields.Char(string='Address Line 2', readonly=True, copy=False)
    ezee_address_line2 = fields.Char(string='Phone Number', readonly=True, copy=False)
    ezee_address3 = fields.Char(string='Address Line 3', readonly=True, copy=False)
    ezee_country = fields.Char(string='Country', readonly=True, copy=False)
    ezee_registration_no = fields.Char(string='Registration No.', readonly=True, copy=False)
    ezee_booking_no = fields.Char(string='OTA  Reference)', readonly=True, copy=False)
    ezee_remark = fields.Char(string='Remark', readonly=True, copy=False)
    ezee_number_of_nights = fields.Integer(string='Number of Nights',compute='_compute_number_of_nights', store=True)
    bussiness_source_name=fields.Char(string='Business Source', readonly=True)
    partner_postal_address = fields.Text(
        string='Partner Address',
        compute='_compute_partner_postal_address',
    )

    def _compute_number_of_nights(self):
        for rec in self:
            if rec.ezee_checkin_date and rec.ezee_checkout_date:
                rec.ezee_number_of_nights = (rec.ezee_checkout_date - rec.ezee_checkin_date).days
            else:
                rec.ezee_number_of_nights = 0

    @api.depends(
        'partner_id',
        'partner_id.street',
        'partner_id.street2',
        'partner_id.city',
        'partner_id.state_id',
        'partner_id.zip',
        'partner_id.country_id',
    )
    def _compute_partner_postal_address(self):
        for rec in self:
            partner = rec.partner_id
            rec.partner_postal_address = partner._display_address(without_company=True).strip() if partner else False

    def cron_apply_outstanding_credits(self):

        invoices = self.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
        ])

        for invoice in invoices:

            receivable_line = invoice.line_ids.filtered(
                lambda l: l.account_id.account_type == 'asset_receivable'
            )

            if not receivable_line:
                continue

            credits = self.env['account.move.line'].search([
                ('partner_id', '=', invoice.commercial_partner_id.id),
                ('account_id', '=', receivable_line.account_id.id),
                ('reconciled', '=', False),
                ('credit', '>', 0),
                ('move_id.state', '=', 'posted'),
            ], order='date')

            for credit in credits:

                if invoice.payment_state == 'paid':
                    break

                try:
                    invoice.js_assign_outstanding_line(credit.id)
                except Exception:
                    continue
    _sql_constraints = [
        ('pms_tran_id_unique', 'unique(pms_tran_id, pms_hotel_id, move_type)', 'PMS Transaction ID must be unique per hotel and type!')
    ]

    def get_extra_print_items(self):
        # get_extra_print_items() requires a singleton.
        # Guard against both multi-record calls (list view selection)
        # and invoices with no commercial_partner_id (PMS-generated records).
        if len(self) != 1 or not self.commercial_partner_id:
            return []
        return super().get_extra_print_items()

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    pms_tran_id = fields.Char(string='PMS Transaction ID', copy=False, index=True)
    pms_hotel_id = fields.Many2one('pms.credentials', string='PMS Hotel', copy=False)
    pms_reference = fields.Char(string='PMS Reference', copy=False)
    # eZee Info fields
    ezee_id = fields.Char(string='Ezee ID', readonly=True, copy=False)
    ezee_guest_name = fields.Char(string='Guest Name', readonly=True, copy=False)
    ezee_reservation_number = fields.Char(string='Reservation Number', readonly=True, copy=False)
    ezee_folio_number = fields.Char(string='Folio Number', readonly=True, copy=False)
    ezee_type = fields.Char(string='eZee Payment Type', readonly=True, copy=False)
    ezee_room_number = fields.Char(string='Room Number', readonly=True, copy=False)
    ezee_checkin_date = fields.Date(string='Check-In Date', readonly=True, copy=False)
    ezee_checkout_date = fields.Date(string='Check-Out Date', readonly=True, copy=False)
    ezee_receipt_no = fields.Char(string='Receipt Number', readonly=True, copy=False)
    ezee_invoice_no = fields.Char(string='Invoice Number', readonly=True, copy=False)
    ezee_bill_name = fields.Char(string='Bill To Name', readonly=True, copy=False)
    ezee_amount = fields.Float(string='Amount', readonly=True, copy=False)
    ezee_payment_method = fields.Char(string='eZee Payment Method', readonly=True, copy=False)
    ezee_voucher_type=fields.Char(string='Voucher Type', readonly=True)
    ezee_voucher_number=fields.Char(string='OTA Voucher Number', readonly=True)
    ezee_credit_number=fields.Char(string='Credit Number', readonly=True)
    remarks=fields.Char(string='Remarks', readonly=True)
    market=fields.Char(string='Market', readonly=True)
    bussiness_source_name=fields.Char(string='Business Source', readonly=True)

    sql_constraints = [
        ('pms_tran_id_unique', 'unique(pms_tran_id, pms_hotel_id, payment_type)', 'PMS Transaction ID must be unique per hotel and payment type!')
    ]


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    transaction_id = fields.Char(
        string='Transaction ID',
        compute='_compute_transaction_id',
        store=True,
        index=True,
    )

    @api.depends(
        'move_id.pms_tran_id',
        'payment_id.pms_tran_id',
        'payment_id.reconciled_invoice_ids.pms_tran_id',
        'payment_id.reconciled_bill_ids.pms_tran_id',
        'matched_debit_ids.debit_move_id.move_id.pms_tran_id',
        'matched_credit_ids.credit_move_id.move_id.pms_tran_id',
    )
    def _compute_transaction_id(self):
        invoice_move_types = (
            'out_invoice',
            'out_refund',
            'out_receipt',
            'in_invoice',
            'in_refund',
            'in_receipt',
        )
        for line in self:
            transaction_id = line.move_id.pms_tran_id or False

            if not transaction_id and line.payment_id and line.payment_id.pms_tran_id:
                transaction_id = line.payment_id.pms_tran_id

            if not transaction_id and line.payment_id:
                payment_invoices = (
                    line.payment_id.reconciled_invoice_ids |
                    line.payment_id.reconciled_bill_ids
                ).filtered(lambda move: move.pms_tran_id)
                transaction_id = payment_invoices[:1].pms_tran_id or False

            if not transaction_id:
                reconciled_invoices = (
                    line.matched_debit_ids.debit_move_id.move_id |
                    line.matched_credit_ids.credit_move_id.move_id
                ).filtered(
                    lambda move: move.move_type in invoice_move_types and move.pms_tran_id
                )
                transaction_id = reconciled_invoices[:1].pms_tran_id or False

            line.transaction_id = transaction_id
