# -*- coding: utf-8 -*-
from odoo import models, fields, api


class JournalLinePrintWizard(models.TransientModel):
    _name = 'watan.journal.print.wizard'
    _description = 'Print Journal Lines Wizard'

    # The selected move line IDs passed from the list view action
    line_ids = fields.Many2many(
        'account.move.line',
        string='Journal Lines',
    )

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    allowed_company_ids = fields.Many2many(
        'res.company',
        compute='_compute_allowed_company_ids',
    )

    @api.depends_context('allowed_company_ids')
    def _compute_allowed_company_ids(self):
        for rec in self:
            rec.allowed_company_ids = self.env.companies

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # If called from list view with selected records
        active_ids = self.env.context.get('active_ids', [])
        if active_ids and self.env.context.get('active_model') == 'account.move.line':
            res['line_ids'] = [(6, 0, active_ids)]
        return res

    def action_print_pdf(self):
        """Generate and return the PDF report."""
        self.ensure_one()
        return self.env.ref(
            'watan_journal_print.action_report_journal_lines'
        ).report_action(self)
