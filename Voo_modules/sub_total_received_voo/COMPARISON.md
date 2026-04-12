# Side-by-Side Code Comparison: Odoo 16 vs Odoo 19

## File: __manifest__.py

### Odoo 16 Version
```python
{
    'name': "subtotal received po",
    'version': '16.0.0.0',
    'category': 'Sales',
    'depends': ['stock', 'sale', 'purchase'],
    'data': [
        'views/sub_total_received_views.xml',
        'views/barcode_edits.xml'
    ],
}
```

### Odoo 19 Version
```python
{
    'name': "Subtotal Received PO",
    'version': '19.0.1.0.0',  # ← 5-part version
    'category': 'Inventory/Purchase',  # ← More specific
    'depends': ['stock', 'sale', 'purchase'],
    'data': [
        'views/sub_total_received_views.xml',
        'views/stock_search_view.xml',  # ← Added missing file
        'views/barcode_edits.xml',
    ],
    'application': False,  # ← Added metadata
}
```

---

## File: stock_move.py

### Odoo 16 Version
```python
class StockMove(models.Model):
    _inherit = "stock.move"

    vendor_id = fields.Many2one(
        "res.partner",  # ← String reference
        string="Vendor",
        related="purchase_line_id.order_id.partner_id",
        store=True,
        index=True,
    )
```

### Odoo 19 Version
```python
class StockMove(models.Model):
    _inherit = "stock.move"

    vendor_id = fields.Many2one(
        comodel_name="res.partner",  # ← Explicit parameter
        string="Vendor",
        related="purchase_line_id.order_id.partner_id",
        store=True,
        index=True,
        readonly=True,  # ← Added for related field
    )
```

**Changes:**
- ✅ Added `comodel_name=` parameter
- ✅ Added `readonly=True` for related field

---

## File: purchase_order_line.py (was sub_total_received.py)

### Odoo 16 Version
```python
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    price_tax_received=fields.Monetary(
        string="Price Tax Received",
        readonly=1  # ← Should be True/False
    )

    @api.depends('qty_received', 'price_unit', 'taxes_id','discount')
    def _compute_amount_received(self):
        for line in self:
            tax_results = self.env['account.tax']._compute_taxes(
                [line._convert_to_tax_base_line_dict_received()]
            )
            totals = list(tax_results['totals'].values())[0]  # ← Can fail
            
            # ... calculations with emojis 🔑
```

### Odoo 19 Version
```python
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    price_tax_received = fields.Monetary(
        string="Tax Received",  # ← Cleaner name
        compute="_compute_amount_received",  # ← Now computed
        store=True,
        currency_field="currency_id",
    )

    @api.depends('qty_received', 'price_unit', 'taxes_id', 'discount')
    def _compute_amount_received(self):
        """
        Compute received amounts based on qty_received.
        """  # ← Added docstring
        for line in self:
            tax_line_dict = line._convert_to_tax_base_line_dict_received()
            tax_results = line.env['account.tax']._compute_taxes([tax_line_dict])
            totals = next(iter(tax_results['totals'].values()))  # ← Safer
            
            # All fields computed together
            line.sub_total_received = totals['amount_untaxed']
            line.price_tax_received = totals['amount_tax']
            line.price_total_received = totals['amount_untaxed'] + totals['amount_tax']
```

**Changes:**
- ✅ Renamed file for clarity
- ✅ Made price_tax_received computed (was readonly)
- ✅ Safer dictionary iteration
- ✅ Removed emoji characters
- ✅ Added comprehensive docstrings
- ✅ All received fields computed together

---

## File: purchase_order.py (was total_received.py)

### Odoo 16 Version
```python
class SubTotalReceived(models.Model):  # ← Confusing name
    _inherit = "purchase.order"

    @api.depends("order_line.qty_received", ...)
    def _compute_amount_received_total(self):
        for order in self:
            total = 0.0
            untaxed = 0.0
            tax = 0.0

            for line in order.order_line:
                untaxed += line.sub_total_received
                tax += line.price_tax_received
                total += line.price_total_received
                order.amount_received_total = total  # ← In loop!

            # for line in order.order_line:  # ← Commented code
            #     price_unit = line.price_unit * ...
            #     taxes_res = line.taxes_id._origin.compute_all(...)
            #     total += taxes_res["total_included"]
            
            order.amount_received_untaxed = untaxed
            order.amount_received_tax = tax
            order.amount_received_total = total  # ← Set again
```

### Odoo 19 Version
```python
class PurchaseOrder(models.Model):  # ← Clear name
    _inherit = "purchase.order"

    @api.depends(
        "order_line.qty_received",
        "order_line.price_unit",
        "order_line.discount",
        "order_line.taxes_id"
    )
    def _compute_amount_received_total(self):
        """
        Compute total received amounts by aggregating line amounts.
        """  # ← Documentation
        for order in self:
            total_untaxed = 0.0
            total_tax = 0.0
            total_with_tax = 0.0
            
            # Clean loop - no assignments inside
            for line in order.order_line:
                total_untaxed += line.sub_total_received
                total_tax += line.price_tax_received
                total_with_tax += line.price_total_received
            
            # Update all at once
            order.amount_received_untaxed = total_untaxed
            order.amount_received_tax = total_tax
            order.amount_received_total = total_with_tax
```

**Changes:**
- ✅ Renamed class for clarity
- ✅ Removed all commented code
- ✅ Fixed assignment in loop
- ✅ Added docstrings
- ✅ Cleaner variable names
- ✅ More efficient computation

---

## File: sub_total_received_views.xml

### Odoo 16 Version
```xml
<odoo>
    Inherit the purchase order form
    <record id="view_purchase_order_form_inherit_Topaz" ...>
        ...
        <xpath expr="//field[@name='order_line']/tree/field[@name='taxes_id']" position="after">
            <field name="sub_total_received" optional="show"/>
            <field name="product_barcode" optional="show"/>
        </xpath>
        ...
```

### Odoo 19 Version
```xml
<?xml version="1.0" encoding="UTF-8"?>  <!-- ← Added -->
<odoo>
    <!-- Inherit the purchase order form -->  <!-- ← Proper comment -->
    <record id="view_purchase_order_form_inherit_topaz" ...>
        ...
        <xpath expr="//field[@name='order_line']/tree/field[@name='taxes_id']" position="after">
            <field name="sub_total_received" optional="show" widget="monetary"/>
            <field name="product_barcode" optional="show"/>
        </xpath>
        ...
```

**Changes:**
- ✅ Added XML declaration
- ✅ Fixed comment syntax
- ✅ Added explicit `widget="monetary"`
- ✅ Consistent formatting

---

## Summary of All Changes

### Required Changes (Breaking)
1. ✅ Python 3.10+ compatibility
2. ✅ Version format: 19.0.1.0.0
3. ✅ `comodel_name=` in Many2one fields

### Recommended Changes (Best Practice)
4. ✅ Added `readonly=True` to related fields
5. ✅ XML declarations on all view files
6. ✅ Explicit widget declarations
7. ✅ Comprehensive docstrings
8. ✅ Removed emoji characters

### Code Quality Improvements
9. ✅ Removed commented code
10. ✅ Better file organization
11. ✅ Safer dictionary iteration
12. ✅ Clearer variable names
13. ✅ Fixed assignment in loops

### No Changes Needed
- Tax computation API ✅
- Field names ✅
- View inheritance ✅
- Business logic ✅
