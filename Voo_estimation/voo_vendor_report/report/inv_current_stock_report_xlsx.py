# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from odoo import fields, models, _
import pytz
from pytz import timezone
from datetime import timedelta

_logger = logging.getLogger(__name__)


class AllProductMovesReportXlsx(models.AbstractModel):
    _name = 'report.inv_current_stock_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, objects):
        stock_location_obj = self.env['stock.location']
        stock_quant_obj = self.env['stock.quant']
        so_obj = self.env['sale.order.line']
        po_obj = self.env['purchase.order.line']
        product_obj = self.env['product.product']
        product_data = product_obj.search(domain=[])
        stock_location_data = stock_location_obj.search(
            domain=[('scrap_location', '=', False), ('return_location', '=', False), ('usage', '=', 'internal')])
        header_format = workbook.add_format({
            'bold': 1,
            'border': 2,
            'align': 'left',
            'valign': 'vcenter',
            'color': 'blue',
        })
        left_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'bold': 1,
            'border': 2,
            'bg_color': 'gray',

        })
        sheet = workbook.add_worksheet('sheet' + '/' + str(1))
        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 20)
        sheet.set_column('G:G', 20)
        sheet.set_column('H:H', 20)
        sheet.set_column('I:I', 20)
        sheet.set_column('J:J', 20)
        sheet.set_column('K:K', 20)
        sheet.set_column('L:L', 20)  # Added for Internal Reference

        sheet.write("A1", "Last ordered date", left_format)
        sheet.write("B1", "Last Received Date", left_format)
        sheet.write("C1", "Category", left_format)
        sheet.write("D1", "Vendor Name", left_format)
        sheet.write("E1", "Barcode", left_format)
        sheet.write("F1", "Product Name", left_format)
        sheet.write("G1", "Internal Reference", left_format)  # NEW COLUMN
        sheet.write("H1", "Status", left_format)
        sheet.write("I1", "UOM", left_format)
        sheet.write("J1", "Cost price", left_format)
        sheet.write("K1", "VAT", left_format)
        sheet.write("L1", "Selling price", left_format)

        stock_columns = 12  # Changed from 11 to 12
        stock_list = {}
        for stock in stock_location_data:
            sheet.write(0, stock_columns, stock.name, left_format)
            stock_list[stock.name] = stock_columns
            stock_columns += 1

        row = 1
        col = 0
        for product in product_data:
            stock_quant_data = stock_quant_obj.search(domain=[('product_id', '=', product.id)])
            so_data = so_obj.search(domain=[('product_id', '=', product.id), ('order_id.state', '=', 'sale')],
                                    order='create_date desc', limit=1)
            po_data = po_obj.search(domain=[('product_id', '=', product.id), ('order_id.state', '=', 'purchase')],
                                    order='create_date desc', limit=1)

            if so_data and so_data.order_id.date_order:
                sheet.write(row, 0, so_data.order_id.date_order.strftime('%d/%m/%Y'))
            if po_data and po_data.order_id.date_order:
                sheet.write(row, 1, po_data.order_id.date_order.strftime('%d/%m/%Y'))

            sheet.write(row, 2, product.categ_id.name)

            vendor_name = ""
            for seller in product.seller_ids:
                if len(vendor_name) > 0:
                    vendor_name = vendor_name + "," + seller.display_name
                else:
                    vendor_name = seller.display_name
            sheet.write(row, 3, vendor_name)
            sheet.write(row, 4, product.barcode)
            sheet.write(row, 5, product.name)

            # ADD INTERNAL REFERENCE
            sheet.write(row, 6, product.default_code or '')

            if 'status_topaz' in product:
                sheet.write(row, 7, product.status_topaz)
            sheet.write(row, 8, product.uom_id.display_name)
            sheet.write(row, 9, product.product_tmpl_id.standard_price)

            tax_name = ""
            for tax in product.taxes_id:
                if len(tax_name) > 0:
                    tax_name = tax_name + "," + tax.display_name
                else:
                    tax_name = tax.display_name
            sheet.write(row, 10, tax_name)
            sheet.write(row, 11, product.lst_price)
            for stock in stock_quant_data:
                if stock.location_id.name in stock_list:
                    sheet.write(row, stock_list[stock.location_id.name], stock.quantity)
                print(stock)
            print(product)

            row = row + 1


class AllSalesProductMovesReportXlsx(models.AbstractModel):
    _name = 'report.sales_order_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, objects):
        stock_location_obj = self.env['stock.location']
        stock_quant_obj = self.env['stock.picking']
        so_obj = self.env['sale.order.line']
        po_obj = self.env['purchase.order.line']
        product_obj = self.env['product.product']
        user_tz = timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        date_from = fields.Datetime.from_string(data['form']['date_from'])
        date_to = fields.Datetime.from_string(data['form']['date_to'])
        date_to = date_to + timedelta(hours=23, minutes=59, seconds=59)

        product_data = product_obj.search(domain=[])
        stock_location_data = stock_location_obj.search(
            domain=[('scrap_location', '=', False), ('return_location', '=', False), ('usage', '=', 'internal')])

        header_format = workbook.add_format({
            'bold': 1,
            'border': 2,
            'align': 'left',
            'valign': 'vcenter',
            'color': 'blue',
        })
        left_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'bold': 1,
            'border': 2,
            'bg_color': 'gray',
        })

        sheet = workbook.add_worksheet('sheet' + '/' + str(1))
        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 20)
        sheet.set_column('G:G', 20)
        sheet.set_column('H:H', 20)
        sheet.set_column('I:I', 20)
        sheet.set_column('J:J', 20)

        sheet.write("A1", "Category", left_format)
        sheet.write("B1", "Vendor Name", left_format)
        sheet.write("C1", "Barcode", left_format)
        sheet.write("D1", "Product Name", left_format)
        sheet.write("E1", "Internal Reference", left_format)  # NEW COLUMN
        sheet.write("F1", "Status", left_format)
        sheet.write("G1", "UOM", left_format)
        sheet.write("H1", "Cost price", left_format)
        sheet.write("I1", "VAT", left_format)
        sheet.write("J1", "Selling price", left_format)

        stock_columns = 10  # Changed from 9 to 10
        stock_list = {}
        for stock in stock_location_data:
            sheet.write(0, stock_columns, stock.name + "  Sold Qty", left_format)
            stock_list[stock.name] = stock_columns
            stock_columns += 1

        row = 1
        col = 0
        for product in product_data:
            domain = [('product_id', '=', product.id), ('order_id.date_order', '>=', date_from),
                      ('order_id.date_order', '<=', date_to),
                      ('order_id.state', '=', 'sale')]
            so_data = so_obj.search(domain=domain)

            sheet.write(row, 0, product.categ_id.name)

            vendor_name = ""
            for seller in product.seller_ids:
                if len(vendor_name) > 0:
                    vendor_name = vendor_name + "," + seller.display_name
                else:
                    vendor_name = seller.display_name
            sheet.write(row, 1, vendor_name)

            sheet.write(row, 2, product.barcode)
            sheet.write(row, 3, product.name)

            # ADD INTERNAL REFERENCE
            sheet.write(row, 4, product.default_code or '')

            if 'status_topaz' in product:
                sheet.write(row, 5, product.status_topaz)
            sheet.write(row, 6, product.uom_id.display_name)
            sheet.write(row, 7, product.product_tmpl_id.standard_price)

            tax_name = ""
            for tax in product.taxes_id:
                if len(tax_name) > 0:
                    tax_name = tax_name + "," + tax.display_name
                else:
                    tax_name = tax.display_name
            sheet.write(row, 8, tax_name)
            sheet.write(row, 9, product.lst_price)

            sale_stock = {}
            for sale_line in so_data:
                for stock in sale_line.order_id.picking_ids:
                    lines = stock.move_line_ids.filtered(lambda l: l.product_id.id == product.id)
                    for line in lines:
                        if stock.location_id.name in sale_stock:
                            sale_stock[stock.location_id.name] = sale_stock[stock.location_id.name] + line.qty_done
                        else:
                            sale_stock[stock.location_id.name] = line.qty_done

            for sstock in sale_stock:
                if sstock in stock_list:
                    sheet.write(row, stock_list[sstock], sale_stock[sstock])
                print(sstock)
            print(product)

            row = row + 1


class AllPurchaseProductMovesReportXlsx(models.AbstractModel):
    _name = 'report.purchase_order_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, objects):
        stock_location_obj = self.env['stock.location']
        stock_quant_obj = self.env['stock.picking']
        so_obj = self.env['sale.order']
        po_obj = self.env['purchase.order']
        product_obj = self.env['product.product']
        user_tz = timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        date_from = fields.Datetime.from_string(data['form']['date_from'])
        date_to = fields.Datetime.from_string(data['form']['date_to'])
        date_to = date_to + timedelta(hours=23, minutes=59, seconds=59)

        product_data = product_obj.search(domain=[])
        stock_location_data = stock_location_obj.search(
            domain=[('scrap_location', '=', False), ('return_location', '=', False), ('usage', '=', 'internal')])

        header_format = workbook.add_format({
            'bold': 1,
            'border': 2,
            'align': 'left',
            'valign': 'vcenter',
            'color': 'blue',
        })
        left_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'bold': 1,
            'border': 2,
            'bg_color': 'gray',
        })

        sheet = workbook.add_worksheet('sheet' + '/' + str(1))
        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 20)
        sheet.set_column('G:G', 20)
        sheet.set_column('H:H', 20)
        sheet.set_column('I:I', 20)
        sheet.set_column('J:J', 20)

        sheet.write("A1", "Category", left_format)
        sheet.write("B1", "Vendor Name", left_format)
        sheet.write("C1", "Barcode", left_format)
        sheet.write("D1", "Product Name", left_format)
        sheet.write("E1", "Internal Reference", left_format)  # NEW COLUMN
        sheet.write("F1", "Status", left_format)
        sheet.write("G1", "UOM", left_format)
        sheet.write("H1", "Cost price", left_format)
        sheet.write("I1", "VAT", left_format)
        sheet.write("J1", "Selling price", left_format)

        stock_columns = 10  # Changed from 9 to 10
        stock_list = {}
        for stock in stock_location_data:
            sheet.write(0, stock_columns, stock.name + "  Received QTY", left_format)
            stock_list[stock.name] = stock_columns
            stock_columns += 1

        row = 1
        col = 0
        for product in product_data:
            domain = [('order_line.product_id', '=', product.id), ('date_order', '>=', date_from),
                      ('date_order', '<=', date_to),
                      ('state', '=', 'purchase')]
            po_data = po_obj.search(domain=domain)

            sheet.write(row, 0, product.categ_id.name)

            vendor_name = ""
            for seller in product.seller_ids:
                if len(vendor_name) > 0:
                    vendor_name = vendor_name + "," + seller.display_name
                else:
                    vendor_name = seller.display_name
            sheet.write(row, 1, vendor_name)
            sheet.write(row, 2, product.barcode)
            sheet.write(row, 3, product.name)
            sheet.write(row, 4, product.default_code or '')
            if 'status_topaz' in product:
                sheet.write(row, 5, product.status_topaz)
            sheet.write(row, 6, product.uom_id.display_name)
            sheet.write(row, 7, product.product_tmpl_id.standard_price)

            tax_name = ""
            for tax in product.taxes_id:
                if len(tax_name) > 0:
                    tax_name = tax_name + "," + tax.display_name
                else:
                    tax_name = tax.display_name
            sheet.write(row, 8, tax_name)
            sheet.write(row, 9, product.lst_price)

            col = 11
            purchase_stock = {}
            if product.name == '12 Staedtler Pencils 2HB With Eraser Tip':
                print(product)
            for purchase in po_data:
                for stock in purchase.picking_ids:
                    lines = stock.move_line_ids.filtered(lambda l: l.product_id.id == product.id)
                    for line in lines:
                        if stock.location_id.name in purchase_stock:
                            purchase_stock[stock.location_id.name] = purchase_stock[
                                                                         stock.location_id.name] + line.qty_done
                        else:
                            purchase_stock[stock.location_id.name] = line.qty_done

            for sstock in purchase_stock:
                if sstock in stock_list:
                    sheet.write(row, stock_list[sstock], purchase_stock[sstock])
                print(sstock)
            print(product)

            row = row + 1