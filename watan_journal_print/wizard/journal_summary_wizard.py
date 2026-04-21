# -*- coding: utf-8 -*-
from odoo import models, fields, api


class JournalSummaryWizard(models.TransientModel):
    _name = 'watan.journal.summary.wizard'
    _description = 'Journal Summary Print Wizard'

    company_id = fields.Many2one(
        'res.company',
        string='Hotel / Company',
        required=True,
        default=lambda self: self.env.company,
    )

    allowed_company_ids = fields.Many2many(
        'res.company',
        compute='_compute_allowed_company_ids',
    )


    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)

    summary_line_ids = fields.One2many(
        'watan.journal.summary.line',
        'wizard_id',
        string='Account Totals',
    )

    @api.depends_context('allowed_company_ids')
    def _compute_allowed_company_ids(self):
        for rec in self:
            rec.allowed_company_ids = self.env.companies


    def action_preview(self):
        """Compute totals and refresh the wizard to show them."""
        self.ensure_one()
        self.summary_line_ids.unlink()

        domain = [
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('move_id.state', '=', 'posted'),
            '|',
            ('account_id.name', 'ilike', 'إيزي'),
            ('account_id.code', '=', '201017'),
            ('account_id.name', 'ilike', 'ezee'),
        ]

        groups = self.env['account.move.line']._read_group(
            domain=domain,
            groupby=['account_id'],
            aggregates=['debit:sum', 'credit:sum'],
        )
        print("GROUPS ===>", groups)

        lines = []
        for account, total_debit, total_credit in groups:
            print("ACCOUNT:", account, account.id, account.name)
            lines.append({
                'wizard_id': self.id,
                'account_id': account.id,
                'account_code': getattr(account, 'code', '') or '',
                'account_name': account.name,
                'total_debit': total_debit or 0.0,
                'total_credit': total_credit or 0.0,
            })

        if lines:
            self.env['watan.journal.summary.line'].create(lines)
            print("LINES CREATED:", len(lines))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'watan.journal.summary.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # def action_print_pdf(self):
    #     """Print PDF directly (auto-computes if lines not yet loaded)."""
    #     self.ensure_one()
    #     if not self.summary_line_ids:
    #         self.action_preview()
    #     return self.env.ref(
    #         'watan_journal_print.action_report_journal_summary'
    #     ).report_action(self)

    def action_print_pdf(self):
        """Print PDF directly (auto-computes if lines not yet loaded)."""
        self.ensure_one()
        if not self.summary_line_ids:
            self.action_preview()

        # 1. تحديد لغة المستخدم الحالي
        user_lang = self.env.context.get('lang') or self.env.user.lang

        # 2. إرسال اللغة للتقرير عن طريق with_context
        return self.env.ref(
            'watan_journal_print.action_report_journal_summary'
        ).with_context(lang=user_lang).report_action(self)



class JournalSummaryLine(models.TransientModel):
    _name = 'watan.journal.summary.line'
    _description = 'Journal Summary Line'
    _order = 'account_code'

    wizard_id    = fields.Many2one('watan.journal.summary.wizard', ondelete='cascade')
    account_id   = fields.Many2one('account.account', string='Account')
    account_code = fields.Char(string='Code')
    account_name = fields.Char(string='Account Name')
    total_debit  = fields.Float(string='Debit',   digits=(16, 2))
    total_credit = fields.Float(string='Credit',  digits=(16, 2))
    balance      = fields.Float(
        string='Balance',
        digits=(16, 2),
        compute='_compute_balance',
    )

    @api.depends('total_debit', 'total_credit')
    def _compute_balance(self):
        for rec in self:
            rec.balance = rec.total_debit - rec.total_credit
