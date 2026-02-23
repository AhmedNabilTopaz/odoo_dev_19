# -*- coding: utf-8 -*-
"""
Encopedia RSMS API Controller - Odoo 19
"""
from odoo import http, fields
from odoo.http import request, Response
import json
import logging

_logger = logging.getLogger(__name__)


# ----------------------------------------------------------
# Centralized API Response Helpers
# ----------------------------------------------------------
def api_error(code, message, status=200):
    body = json.dumps({
        "success": False,
        "error": {
            "code": code,
            "message": message
        }
    })
    return Response(body, status=status, mimetype='application/json')


def api_success(data):
    body = json.dumps(data)
    return Response(body, status=200, mimetype='application/json')


class RSMSInvoiceController(http.Controller):

    # ----------------------------------------------------------
    # CRITICAL FIX 1: type='http' instead of type='json'
    # -------------------------------------------------------
    # In Odoo 19, type='json' routes expect the exact Odoo
    # JSON-RPC 2.0 envelope format:
    #   {"jsonrpc":"2.0","method":"call","params":{...}}
    # A plain REST POST body does NOT match this — Odoo routes
    # it to the website 404 handler instead of your controller.
    # Using type='http' lets us handle the raw body ourselves,
    # which is correct for a REST API consumed by Postman/external.
    #
    # CRITICAL FIX 2: save_session=False
    # -------------------------------------------------------
    # Prevents Odoo from trying to write a session for a public
    # request, which can cause silent failures on auth='public'.
    # ----------------------------------------------------------
    @http.route(
        '/api/rsms/invoices',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def get_posted_invoices(self, **kwargs):
        """
        Encopedia RSMS REST API
        Returns ONLY POSTED customer invoices filtered by date range
        and analytic-account-based location (accounts starting with '9').

        Request headers:
            Authorization: <api_key>
            Content-Type:  application/json

        Request body:
            {"date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD"}
        """
        try:
            # ----------------------------------------------------------
            # AUTHENTICATION — raw API key in Authorization header
            # ----------------------------------------------------------
            api_key = request.httprequest.headers.get('Authorization', '').strip()
            if not api_key:
                return api_error("AUT001", "Missing Authorization header", 401)

            key_record = request.env['auth.api.key'].sudo().search(
                [('key', '=', api_key)],
                limit=1
            )
            if not key_record:
                return api_error("AUT002", "Invalid or unknown API key", 401)

            # ----------------------------------------------------------
            # CRITICAL FIX 3: correct way to switch user env in Odoo 19
            # ----------------------------------------------------------
            env = request.env(user=key_record.user_id.id)

            # ----------------------------------------------------------
            # READ JSON BODY — type='http' means we read it manually
            # ----------------------------------------------------------
            try:
                raw_body = request.httprequest.get_data(as_text=True)
                data = json.loads(raw_body) if raw_body else {}
            except (json.JSONDecodeError, Exception):
                return api_error("REQ001", "Invalid or empty JSON body", 400)

            if not data:
                return api_error("REQ001", "Empty request body", 400)

            date_from = data.get('date_from')
            date_to   = data.get('date_to')

            if not date_from or not date_to:
                return api_error("REQ002", "Missing required fields: date_from, date_to", 400)

            # ----------------------------------------------------------
            # GET ANALYTIC ACCOUNTS REPRESENTING LOCATIONS (code ~ '9...')
            # ----------------------------------------------------------
            analytic_locations = env['account.analytic.account'].sudo().search([
                ('name', '=like', '9%')
            ])

            if not analytic_locations:
                return api_error("ANA001", "No analytic accounts starting with '9' were found")

            location_analytic_ids = set(analytic_locations.ids)

            # ----------------------------------------------------------
            # SEARCH POSTED CUSTOMER INVOICES IN DATE RANGE
            # ----------------------------------------------------------
            domain = [
                ('move_type', '=', 'out_invoice'),
                ('state',     '=', 'posted'),
                ('invoice_date', '>=', date_from),
                ('invoice_date', '<=', date_to),
            ]

            invoices = env['account.move'].sudo().search(domain, order='invoice_date asc')

            if not invoices:
                return api_error("DAT001", "No posted invoices found for the given criteria")

            # ----------------------------------------------------------
            # BUILD RESPONSE — filter lines by analytic location
            # ----------------------------------------------------------
            invoice_data = []

            for inv in invoices:
                has_valid_lines = False
                total_discount  = 0.0

                for line in inv.invoice_line_ids:
                    # Odoo 19: analytic_distribution is always a dict {str(id): pct}
                    distribution = line.analytic_distribution or {}

                    # Normalise: handle the rare case it arrives as a JSON string
                    if isinstance(distribution, str):
                        try:
                            distribution = json.loads(distribution)
                        except (json.JSONDecodeError, TypeError):
                            distribution = {}

                    # Extract numeric IDs from the dict keys
                    analytic_ids_on_line = {
                        int(k) for k in distribution
                        if isinstance(k, str) and k.isdigit()
                    }

                    # Skip lines that don't belong to a location analytic
                    if not (analytic_ids_on_line & location_analytic_ids):
                        continue

                    has_valid_lines = True

                    if line.discount and line.discount > 0:
                        total_discount += (line.price_unit * line.quantity * line.discount) / 100.0

                if not has_valid_lines:
                    continue

                invoice_data.append({
                    "invoice_number": inv.name,
                    "invoice_type":   "invoice",
                    "invoice_date":   fields.Date.to_string(inv.invoice_date),
                    "total_discount": round(total_discount, 2),
                    "subtotal":       inv.amount_untaxed,
                    "tax_total":      inv.amount_tax,
                    "total":          inv.amount_total,
                })

            if not invoice_data:
                return api_error("DAT002", "Invoices found but none matched analytic location rules")

            return api_success({
                "success":     True,
                "application": "Encopedia RSMS",
                "count":       len(invoice_data),
                "invoices":    invoice_data,
            })

        except Exception as e:
            _logger.exception("RSMS API unexpected error")
            return api_error("SRV001", f"Internal server error: {str(e)}", 500)