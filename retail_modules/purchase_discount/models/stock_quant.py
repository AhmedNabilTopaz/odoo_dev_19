# from odoo import models

# class StockQuant(models.Model):
#     _inherit = "stock.quant"
    
#     @api.model
#     def _unlink_zero_quants(self):
#         pass
# #         """ _update_available_quantity may leave quants with no
# #         quantity and no reserved_quantity. It used to directly unlink
# #         these zero quants but this proved to hurt the performance as
# #         this method is often called in batch and each unlink invalidate
# #         the cache. We defer the calls to unlink in this method.
# #         """
# #         precision_digits = max(6, self.sudo().env.ref('product.decimal_product_uom').digits * 2)
# #         # Use a select instead of ORM search for UoM robustness.
# #         query = """SELECT id FROM stock_quant WHERE (round(quantity::numeric, %s) = 0 OR quantity IS NULL) AND round(reserved_quantity::numeric, %s) = 0;"""
# #         params = (precision_digits, precision_digits)
# #         self.env.cr.execute(query, params)
# #         quant_ids = self.env['stock.quant'].browse([quant['id'] for quant in self.env.cr.dictfetchall()])
# #         #quant_ids.sudo().unlink()


#     @api.model
#     def _quant_tasks(self):
#         self._merge_quants()
         
    
# class QuantPackage(models.Model):
#     _inherit = "stock.quant.package"

#     def unpack(self):
#         for package in self:
#             move_line_to_modify = self.env['stock.move.line'].search([
#                 ('package_id', '=', package.id),
#                 ('state', 'in', ('assigned', 'partially_available')),
#                 ('product_qty', '!=', 0),
#             ])
#             move_line_to_modify.write({'package_id': False})
#             package.mapped('quant_ids').sudo().write({'package_id': False})
#             self.env['stock.quant']._merge_quants()
 
