# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request, Response
import json
import logging

_logger = logging.getLogger(__name__)


def _api_ok(data):
    return Response(json.dumps(data), status=200, mimetype='application/json')


def _api_err(message, status=200):
    return Response(
        json.dumps({"success": False, "error": message}),
        status=status,
        mimetype='application/json',
    )


def _auth_and_parse(raw_required_fields):
    """
    Shared helper: authenticate API key, switch env, parse body.
    Returns (env, data, error_response) — if error_response is not None, return it immediately.
    """
    api_key = request.httprequest.headers.get('Authorization', '').strip()
    if not api_key:
        return None, None, _api_err("Missing Authorization header", 401)

    key_record = request.env['auth.api.key'].sudo().search(
        [('key', '=', api_key)], limit=1
    )
    if not key_record:
        return None, None, _api_err("Invalid or unknown API key", 401)

    # FIX: Odoo 19 — scoped env, don't mutate request.env
    env = request.env(user=key_record.user_id.id)

    try:
        raw_body = request.httprequest.get_data(as_text=True)
        data = json.loads(raw_body) if raw_body else {}
    except (json.JSONDecodeError, Exception):
        return None, None, _api_err("Invalid or empty JSON body", 400)

    if not data:
        return None, None, _api_err("Empty request body", 400)

    missing = [f for f in raw_required_fields if not data.get(f)]
    if missing:
        return None, None, _api_err(f"Missing required fields: {', '.join(missing)}", 400)

    return env, data, None


def _build_order(env, session, config, product, product_id, quantity, price, purchase_date,
                 payment_method, subtotal, vending_machine):
    """Shared order creation logic."""
    order = env['pos.order'].sudo().create({
        'session_id': session.id,
        'company_id': session.company_id.id,
        'user_id': session.user_id.id,
        'pricelist_id': config.pricelist_id.id,
        'amount_total': subtotal,
        'amount_paid': subtotal,
        'amount_return': 0.0,
        'amount_tax': 0.0,
        'purchase_date': purchase_date,
        'lines': [(0, 0, {
            'product_id': product_id,
            'qty': quantity,
            'price_unit': price,
            'price_subtotal': subtotal,
            'price_subtotal_incl': subtotal,
            'full_product_name': product.display_name,
        })],
    })

    env['pos.payment'].sudo().create({
        'pos_order_id': order.id,
        'amount': subtotal,
        'payment_method_id': payment_method.id,
        'session_id': session.id,
    })

    order.sudo().write({
        'amount_paid': subtotal,
        'amount_total': subtotal,
        'state': 'done',
    })
    order.action_pos_order_paid()

    base_url = env['ir.config_parameter'].sudo().get_param('web.base.url')
    return {
        "success": True,
        "order_id": order.id,
        "order_name": order.name,
        "product_name": product.display_name,
        "total": subtotal,
        "vending_machine": vending_machine.display_name,
        "order_url": f"{base_url}/web#id={order.id}&model=pos.order&view_type=form",
        "message": "Vending machine order created successfully",
    }


class VendingMachineController(http.Controller):

    # FIX: type='http' — plain REST body not JSON-RPC; saves us from 404 in Postman
    @http.route(
        '/vending/create_order',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def create_order(self, **kwargs):
        try:
            env, data, err = _auth_and_parse(['pos_id', 'payment_method_id'])
            if err:
                return err

            product_tmpl_id  = data.get('product_tmpl_id')
            product_id       = data.get('product_id')
            quantity         = data.get('quantity', 1)
            price            = data.get('price', 0.0)
            pos_id           = data.get('pos_id')
            payment_method_id = data.get('payment_method_id')

            session = env['pos.session'].sudo().browse(pos_id)
            if not session.exists():
                return _api_err(f"POS Session {pos_id} not found")

            config = session.config_id
            if not config:
                return _api_err(f"No POS configuration found for session {session.name}")

            vending_machine = getattr(config, 'vending_machine_id', False)
            if not vending_machine:
                return _api_err(f"POS Config '{config.name}' has no vending machine linked")

            if product_tmpl_id and not product_id:
                product = env['product.product'].sudo().search(
                    [('product_tmpl_id', '=', product_tmpl_id)], limit=1
                )
                if not product:
                    return _api_err(f"No product variant found for template ID {product_tmpl_id}")
                product_id = product.id
            else:
                product = env['product.product'].sudo().browse(product_id)

            if not all([product_id, quantity, price]):
                return _api_err("Missing one or more required fields (product_id, quantity, price)")

            payment_method = env['pos.payment.method'].sudo().browse(payment_method_id)
            if not payment_method.exists():
                return _api_err(f"Payment method {payment_method_id} not found")
            if payment_method not in config.payment_method_ids:
                return _api_err(
                    f"Payment method '{payment_method.name}' is not allowed in POS config '{config.name}'"
                )

            subtotal = price * quantity
            purchase_date_str = data.get('purchase_date')
            purchase_date = (
                fields.Datetime.from_string(purchase_date_str)
                if purchase_date_str else fields.Datetime.now()
            )

            result = _build_order(
                env, session, config, product, product_id,
                quantity, price, purchase_date, payment_method, subtotal, vending_machine
            )
            return _api_ok(result)

        except Exception as e:
            _logger.exception("create_order error")
            return _api_err(f"Error creating vending order: {str(e)}", 500)

    @http.route(
        '/vending/create_order_by_name',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def create_order_by_name(self, **kwargs):
        try:
            env, data, err = _auth_and_parse(['product_name', 'pos_id', 'payment_method_id'])
            if err:
                return err

            product_name     = data.get('product_name')
            quantity         = data.get('quantity', 1)
            price            = data.get('price', 0.0)
            pos_id           = data.get('pos_id')
            payment_method_id = data.get('payment_method_id')

            session = env['pos.session'].sudo().browse(pos_id)
            if not session.exists():
                return _api_err(f"POS Session {pos_id} not found")

            config = session.config_id
            vending_machine = getattr(config, 'vending_machine_id', False)
            if not vending_machine:
                return _api_err(f"POS Config '{config.name}' has no vending machine linked")

            product = env['product.product'].sudo().search([('name', '=', product_name)])
            if not product:
                return _api_err(f"No product found with name '{product_name}'")
            if len(product) > 1:
                return _api_err(
                    f"Multiple products found with name '{product_name}', please use an exact unique name"
                )
            product = product[0]

            payment_method = env['pos.payment.method'].sudo().browse(payment_method_id)
            if not payment_method.exists():
                return _api_err(f"Payment method {payment_method_id} not found")
            if payment_method not in config.payment_method_ids:
                return _api_err(
                    f"Payment method '{payment_method.name}' is not allowed in POS config '{config.name}'"
                )

            subtotal = price * quantity
            purchase_date_str = data.get('purchase_date')
            purchase_date = (
                fields.Datetime.from_string(purchase_date_str)
                if purchase_date_str else fields.Datetime.now()
            )

            result = _build_order(
                env, session, config, product, product.id,
                quantity, price, purchase_date, payment_method, subtotal, vending_machine
            )
            return _api_ok(result)

        except Exception as e:
            _logger.exception("create_order_by_name error")
            return _api_err(f"Error creating vending order: {str(e)}", 500)
