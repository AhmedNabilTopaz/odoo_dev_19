# -*- coding: utf-8 -*-
import logging

from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class INVCurrentReportWizard(models.TransientModel):
    _name = "inv.current.report.wizard"

    product_filter = fields.Selection(string="Report Type", selection=[('inv', 'Inv Current Stock'),
                                                            ('sale', 'Sales Report'),
                                                            ('purchase', 'Purchase Report'),
                                                            ], required=True, default='inv')
    def _get_default_date_from(self):
        year = fields.Date.from_string(fields.Date.today()).strftime('%Y-%m')
        return '{}-01'.format(year)

    def _get_default_date_to(self):
        date = fields.Date.from_string(fields.Date.today())
        return date.strftime('%Y') + '-' + date.strftime('%m') + '-' + date.strftime('%d')

    date_from = fields.Date(string='From Date', required=True, default=_get_default_date_from)
    date_to = fields.Date(string='To Date', required=True, default=_get_default_date_to)

    # @api.multi
    def print_xlsx_report(self):
        """
         To get the date and print the report
         @return: return report
        """
        self.ensure_one()
        data = {'ids': self.env.context.get('active_ids', [])}
        res = self.read()
        res = res and res[0] or {}
        data.update({'form': res})
        if self.product_filter=='inv':
            report = self.env['ir.actions.report']._get_report_from_name('inv_current_stock_report_xlsx')
        elif self.product_filter=='sale':
            report = self.env['ir.actions.report']._get_report_from_name('sales_order_report_xlsx')
        elif self.product_filter == 'purchase':
            report = self.env['ir.actions.report']._get_report_from_name('purchase_order_report_xlsx')
        return {
            'data': data,
            'type': 'ir.actions.report',
            'report_name': report.report_name,
            'report_type': report.report_type,
            'report_file': report.report_file,
        }



# class SalesReportReportWizard(models.TransientModel):
#     _name = "sale.order.users.details.report.wizard"
#
#     def _get_default_date_from(self):
#         year = fields.Date.from_string(fields.Date.today()).strftime('%Y-%m')
#         return '{}-01'.format(year)
#
#     def _get_default_date_to(self):
#         date = fields.Date.from_string(fields.Date.today())
#         return date.strftime('%Y') + '-' + date.strftime('%m') + '-' + date.strftime('%d')
#
#     # def _get_location_domain(self):
#     #     if self.env.user.has_group('stock.group_stock_manager'):
#     #         return []
#     #     else:
#     #         return []
#             # return [('branch_id', '=', self.env.user.branch_id.id)]
#
#     date_from = fields.Date(string='From Date', required=True, default=_get_default_date_from)
#     date_to = fields.Date(string='To Date', required=True, default=_get_default_date_to)
#     # product_filter = fields.Selection(string="", selection=[('product', 'On One Product'),
#     #                                                         ('all_product', 'On ALL Products'),
#     #                                                         ('product_category', 'On Product Category'),
#     #                                                         ], required=True, default='all_product')
#     user_id =fields.Many2one(string='Sales Person',comodel_name='hr.employee',domain="[['department_id','=',2]]")
#
#
#     # product_id = fields.Many2many(comodel_name="product.product", string="Product")
#     # product_categ_id = fields.Many2one(comodel_name="product.category", string="Product Category")
#     # location_id = fields.Many2one(comodel_name="stock.location", string="Location",
#     #                               domain=lambda self: self._get_location_domain())
#     # is_all_internal_location = fields.Boolean(string="ALL Internal Locations")
#
#     # @api.onchange('product_filter')
#     # def onchange_method(self):
#     #     if self.product_filter == 'all_product':
#     #         self.product_id = False
#     #         self.product_categ_id = False
#     #
#     #     elif self.product_filter == 'product_category':
#     #         self.product_id = False
#     #     else:
#     #         self.product_categ_id = False
#
#     # @api.multi
#     def print_xlsx_report(self):
#         """
#          To get the date and print the report
#          @return: return report
#         """
#         self.ensure_one()
#         data = {'ids': self.env.context.get('active_ids', [])}
#         res = self.read()
#         res = res and res[0] or {}
#         data.update({'form': res})
#         if data['form']['user_id']:
#             report = self.env['ir.actions.report']._get_report_from_name('single_sale_order_user_details_report_xlsx')
#         else:
#             report = self.env['ir.actions.report']._get_report_from_name('all_sale_order_user_details_report_xlsx')
#
#         return {
#             'data': data,
#             'type': 'ir.actions.report',
#             'report_name': report.report_name,
#             'report_type': report.report_type,
#             'report_file': report.report_file,
#         }
#
#
# class PurchasesReportReportWizard(models.TransientModel):
#     _name = "sale.order.users.details.report.wizard"
#
#     def _get_default_date_from(self):
#         year = fields.Date.from_string(fields.Date.today()).strftime('%Y-%m')
#         return '{}-01'.format(year)
#
#     def _get_default_date_to(self):
#         date = fields.Date.from_string(fields.Date.today())
#         return date.strftime('%Y') + '-' + date.strftime('%m') + '-' + date.strftime('%d')
#
#     # def _get_location_domain(self):
#     #     if self.env.user.has_group('stock.group_stock_manager'):
#     #         return []
#     #     else:
#     #         return []
#             # return [('branch_id', '=', self.env.user.branch_id.id)]
#
#     date_from = fields.Date(string='From Date', required=True, default=_get_default_date_from)
#     date_to = fields.Date(string='To Date', required=True, default=_get_default_date_to)
#     # product_filter = fields.Selection(string="", selection=[('product', 'On One Product'),
#     #                                                         ('all_product', 'On ALL Products'),
#     #                                                         ('product_category', 'On Product Category'),
#     #                                                         ], required=True, default='all_product')
#     user_id =fields.Many2one(string='Sales Person',comodel_name='hr.employee',domain="[['department_id','=',2]]")
#
#
#     # product_id = fields.Many2many(comodel_name="product.product", string="Product")
#     # product_categ_id = fields.Many2one(comodel_name="product.category", string="Product Category")
#     # location_id = fields.Many2one(comodel_name="stock.location", string="Location",
#     #                               domain=lambda self: self._get_location_domain())
#     # is_all_internal_location = fields.Boolean(string="ALL Internal Locations")
#
#     # @api.onchange('product_filter')
#     # def onchange_method(self):
#     #     if self.product_filter == 'all_product':
#     #         self.product_id = False
#     #         self.product_categ_id = False
#     #
#     #     elif self.product_filter == 'product_category':
#     #         self.product_id = False
#     #     else:
#     #         self.product_categ_id = False
#
#     # @api.multi
#     def print_xlsx_report(self):
#         """
#          To get the date and print the report
#          @return: return report
#         """
#         self.ensure_one()
#         data = {'ids': self.env.context.get('active_ids', [])}
#         res = self.read()
#         res = res and res[0] or {}
#         data.update({'form': res})
#         if data['form']['user_id']:
#             report = self.env['ir.actions.report']._get_report_from_name('single_sale_order_user_details_report_xlsx')
#         else:
#             report = self.env['ir.actions.report']._get_report_from_name('all_sale_order_user_details_report_xlsx')
#
#         return {
#             'data': data,
#             'type': 'ir.actions.report',
#             'report_name': report.report_name,
#             'report_type': report.report_type,
#             'report_file': report.report_file,
#         }