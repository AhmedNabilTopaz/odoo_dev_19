# Quick Reference: Key Changes Odoo 16 → 19

## Critical Changes You Must Know

### 1. Python Version
- **Required:** Python 3.10 or higher
- Check: `python3 --version`

### 2. Module Version Format
```python
# Old (Odoo 16)
'version': '16.0.0.0'

# New (Odoo 19)
'version': '19.0.1.0.0'
```

### 3. Many2one Field Definition
```python
# Old (Odoo 16) - Still works but deprecated
vendor_id = fields.Many2one("res.partner", string="Vendor")

# New (Odoo 19) - Recommended
vendor_id = fields.Many2one(
    comodel_name="res.partner",
    string="Vendor"
)
```

### 4. Related Fields Should Be Readonly
```python
# Add readonly=True to related fields
vendor_id = fields.Many2one(
    comodel_name="res.partner",
    related="move_id.vendor_id",
    readonly=True,  # ← Add this
)
```

### 5. XML Views Must Have Declaration
```xml
<?xml version="1.0" encoding="UTF-8"?>  <!-- ← Add this at top -->
<odoo>
    ...
</odoo>
```

---

## What Stayed The Same ✅

1. **Tax Computation API** - No changes needed
2. **Field Names** - All identical, no DB migration
3. **Computed Field Logic** - Works the same way
4. **XML XPath Syntax** - Compatible
5. **Model Inheritance** - Same `_inherit` approach

---

## Installation Commands

### Upgrade Existing Module
```bash
# Backup database first!
./odoo-bin -d DATABASE_NAME -u subtotal_received_po --stop-after-init

# Or in Odoo Apps interface:
# 1. Activate Developer Mode
# 2. Go to Apps
# 3. Remove "Apps" filter
# 4. Search for your module
# 5. Click "Upgrade"
```

### Fresh Install
```bash
./odoo-bin -d DATABASE_NAME -i subtotal_received_po --stop-after-init
```

---

## File Reorganization

### Renamed Files (Same Content, Better Names)
- `total_received.py` → `purchase_order.py`
- `sub_total_received.py` → `purchase_order_line.py`

### Updated models/__init__.py
```python
# Old
from . import total_received
from . import sub_total_received

# New  
from . import purchase_order
from . import purchase_order_line
from . import stock_move  # This was missing!
```

---

## Testing Quick Commands

```python
# In Odoo shell
./odoo-bin shell -d DATABASE_NAME

# Test field computation
po = self.env['purchase.order'].search([], limit=1)
po.order_line._compute_amount_received()
print(po.amount_received_total)

# Test vendor tracking
moves = self.env['stock.move'].search([('vendor_id', '!=', False)], limit=5)
for move in moves:
    print(f"{move.product_id.name} - Vendor: {move.vendor_id.name}")
```

---

## Common Errors and Quick Fixes

### Error: "comodel_name is required"
**Fix:** Add `comodel_name=` parameter to Many2one fields

### Error: "Module not found"
**Fix:** Check `__init__.py` files import the correct renamed files

### Error: "Field does not exist"
**Fix:** Run upgrade command with `-u module_name`

### Error: XML parsing error
**Fix:** Add `<?xml version="1.0" encoding="UTF-8"?>` at top of XML files

---

## No Breaking Changes In:

- Purchase order line received computations
- Tax calculation methods  
- Stock move vendor tracking
- View inheritance structure
- Field storage and indexing

---

## Summary

This is a **straightforward migration** - mostly code cleanup and Python 3.10+ compatibility. The business logic remains unchanged.

**Time Required:** 15-30 minutes for testing after installation  
**Risk Level:** Low (no data structure changes)  
**Rollback:** Easy (restore database backup)
