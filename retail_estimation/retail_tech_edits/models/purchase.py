
from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from functools import partial
from itertools import groupby
import json

from markupsafe import escape, Markup
from pytz import timezone, UTC
from werkzeug.urls import url_encode

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang, format_amount

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    rate_date = fields.Date(string="Rate Date")


# class PurchaseOrderLine(models.Model):
#     _inherit = 'purchase.order.line'
#
#     def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
#         vals = super()._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
#         # Pass rate_date to stock move context
#         vals['rate_date'] = self.order_id.rate_date
#         return vals
#
#     def _get_stock_move_price_unit(self):
#         self.ensure_one()
#         if self.product_id.cost_method in ('average', 'fifo'):
#             return self.price_unit
#         # Use rate_date if set, else fallback to PO's date_order
#         date = self.order_id.rate_date or self.order_id.date_order.date()
#         return self.currency_id._convert(
#             self.price_unit,
#             self.company_id.currency_id,
#             self.company_id,
#             date,
#             round=False
#         )
