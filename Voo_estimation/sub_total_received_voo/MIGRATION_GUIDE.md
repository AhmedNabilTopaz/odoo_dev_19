# Migration Guide: Odoo 16 to Odoo 19
## Module: Subtotal Received PO

---

## Overview

This guide covers the migration of the "Subtotal Received PO" module from Odoo 16 to Odoo 19. The module calculates and displays received amounts with taxes for Purchase Orders.

**Migration Path:** Odoo 16 → 17 → 18 → 19

---

## 1. Key Changes Summary

### 1.1 Critical Breaking Changes Across Versions

#### **Python Version Requirement**
- **Odoo 16:** Python 3.8+
- **Odoo 17:** Python 3.10+
- **Odoo 18:** Python 3.10+
- **Odoo 19:** Python 3.10+

**Action Required:** Ensure your system runs Python 3.10 or higher.

#### **Module Version Naming**
- **Before:** `16.0.0.0`
- **After:** `19.0.1.0.0` (uses 5-part semantic versioning)

#### **Field Definition Updates**
All Many2one fields now require explicit `comodel_name` parameter instead of string reference.

---

## 2. Detailed Changes by File

### 2.1 `__manifest__.py`

**Changes Made:**
1. ✅ Updated version from `16.0.0.0` to `19.0.1.0.0`
2. ✅ Added missing `stock_search_view.xml` to data files (it was in your uploads but not referenced)
3. ✅ Improved descriptions and metadata
4. ✅ Changed category from 'Sales' to 'Inventory/Purchase' (more accurate)
5. ✅ Added `application: False` parameter
6. ✅ Proper capitalization and formatting

**Why:** Odoo 19 expects proper semantic versioning and complete data file references.

---

### 2.2 `models/stock_move.py`

**Changes Made:**

```python
# BEFORE (Odoo 16)
vendor_id = fields.Many2one(
    "res.partner",
    string="Vendor",
    ...
)

# AFTER (Odoo 19)
vendor_id = fields.Many2one(
    comodel_name="res.partner",  # ✅ Explicit parameter name
    string="Vendor",
    readonly=True,  # ✅ Added for related fields
    ...
)
```

**Why:** 
- Odoo 17+ enforces explicit `comodel_name` parameter for better code clarity
- Related fields should be marked as `readonly=True`

---

### 2.3 `models/purchase_order_line.py` (formerly `sub_total_received.py`)

**Changes Made:**

1. **File Renamed:** `sub_total_received.py` → `purchase_order_line.py`
   - **Why:** Better naming convention matching the inherited model

2. **Improved Documentation:**
   ```python
   @api.depends('qty_received', 'price_unit', 'taxes_id', 'discount')
   def _compute_amount_received(self):
       """
       Compute received amounts based on qty_received instead of product_qty.
       Uses the same tax computation logic as standard order amounts.
       """
   ```

3. **Removed Emoji Characters:**
   - Removed `🔑` emojis from comments
   - **Why:** Can cause encoding issues in some environments

4. **Updated Field Definitions:**
   ```python
   # Added compute dependency to price_tax_received and price_total_received
   price_tax_received = fields.Monetary(
       string="Tax Received",
       compute="_compute_amount_received",  # ✅ Now computed
       store=True,
   )
   ```

5. **Improved Tax Computation:**
   ```python
   # More robust iteration over tax results
   totals = next(iter(tax_results['totals'].values()))
   ```

**Why:** 
- Tax computation API remains compatible but code clarity improved
- All related received fields now computed together for consistency

---

### 2.4 `models/purchase_order.py` (formerly `total_received.py`)

**Changes Made:**

1. **File Renamed:** `total_received.py` → `purchase_order.py`

2. **Cleaned Up Code:**
   - Removed all commented-out code
   - Simplified computation logic
   - Added proper documentation

3. **Before (with commented code):**
   ```python
   # for line in order.order_line:
   #     # Apply discount on unit price
   #     price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
   #     ...
   ```

4. **After (clean):**
   ```python
   # Sum up amounts from all order lines
   for line in order.order_line:
       total_untaxed += line.sub_total_received
       total_tax += line.price_tax_received
       total_with_tax += line.price_total_received
   ```

**Why:** Clean, maintainable code without legacy commented sections

---

### 2.5 XML View Files

**Changes Made:**

1. **sub_total_received_views.xml:**
   - ✅ Added XML declaration: `<?xml version="1.0" encoding="UTF-8"?>`
   - ✅ Fixed missing comment tag on line 2
   - ✅ Added explicit `widget="monetary"` attributes
   - ✅ Made optional fields explicitly `optional="show"`
   - ✅ Improved formatting and consistency

2. **stock_search_view.xml:**
   - ✅ Added XML declaration
   - ✅ No functional changes (already compatible)

3. **barcode_edits.xml:**
   - ✅ Cleaned up commented code
   - ✅ Added explanatory comment

**Why:** Odoo 19 is stricter about XML formatting and widget declarations

---

## 3. Module Structure Changes

### 3.1 Old Structure (Odoo 16)
```
subtotal_received_po/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py  (imports total_received, sub_total_received)
│   ├── total_received.py
│   └── sub_total_received.py
└── views/
    ├── sub_total_received_views.xml
    └── barcode_edits.xml
```

### 3.2 New Structure (Odoo 19)
```
subtotal_received_po/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py  (imports purchase_order, purchase_order_line, stock_move)
│   ├── purchase_order.py
│   ├── purchase_order_line.py
│   └── stock_move.py
└── views/
    ├── sub_total_received_views.xml
    ├── stock_search_view.xml
    └── barcode_edits.xml
```

**Why:** 
- Better organization matching inherited model names
- Easier to maintain and understand
- `stock_move.py` was missing from models/__init__.py - now included

---

## 4. Database Migration Considerations

### 4.1 Field Names
All field names remain the same - **no database migration needed** for field renames.

### 4.2 Upgrade Path

**Option 1: Direct Upgrade (Recommended for this module)**
```bash
# Backup your database first!
./odoo-bin -d your_database -u subtotal_received_po --stop-after-init
```

**Option 2: Uninstall and Reinstall (if issues occur)**
```bash
# Backup your database first!
# 1. In Odoo 16, uninstall the module
# 2. Upgrade Odoo to 19
# 3. Install the new version
```

### 4.3 Data Preservation
- All computed fields will automatically recalculate
- No data loss expected as field names are unchanged
- Test on a copy of your production database first!

---

## 5. Testing Checklist

After migration, test the following:

### 5.1 Purchase Order Line Fields
- [ ] Create a new purchase order
- [ ] Add products with prices and taxes
- [ ] Partially receive products
- [ ] Verify `sub_total_received` calculates correctly
- [ ] Verify `price_tax_received` shows correct tax amounts
- [ ] Verify `price_total_received` = subtotal + tax
- [ ] Check that `product_barcode` displays correctly

### 5.2 Purchase Order Totals
- [ ] Verify `amount_received_untaxed` sums all line subtotals
- [ ] Verify `amount_received_tax` sums all line taxes
- [ ] Verify `amount_received_total` sums all line totals

### 5.3 Stock Move Vendor Tracking
- [ ] Create a purchase order from a vendor
- [ ] Receive products
- [ ] Check stock move and stock move line records
- [ ] Verify `vendor_id` is populated correctly
- [ ] Test grouping by vendor in stock move line search view

### 5.4 Views
- [ ] Open purchase order form view - all fields visible
- [ ] Check purchase order tree/list view - received total appears
- [ ] Test stock move line search with vendor filter
- [ ] Verify optional fields can be hidden/shown

---

## 6. Common Issues and Solutions

### Issue 1: Module Won't Install
**Symptom:** Error about dependencies
**Solution:** Ensure `stock`, `sale`, and `purchase` modules are installed first

### Issue 2: Fields Not Computing
**Symptom:** Received amount fields show 0.00
**Solution:** 
```python
# Trigger recomputation
self.env['purchase.order.line'].search([])._compute_amount_received()
```

### Issue 3: Python Version Error
**Symptom:** "Python 3.10+ required"
**Solution:** Upgrade your Python installation

### Issue 4: Tax Computation Errors
**Symptom:** Tax amounts incorrect
**Solution:** Check that `taxes_id` is properly set on purchase order lines

---

## 7. API Changes Reference

### 7.1 Tax Computation (Unchanged - Compatible)
The `account.tax._compute_taxes()` API works the same way in Odoo 19:
```python
tax_results = self.env['account.tax']._compute_taxes([tax_line_dict])
```

### 7.2 Field Definitions
**Odoo 16:**
```python
fields.Many2one("res.partner", ...)
```

**Odoo 19:**
```python
fields.Many2one(comodel_name="res.partner", ...)
```

---

## 8. Performance Considerations

### 8.1 Computed Fields
All computed fields use `store=True` - this is correct and optimal for:
- Faster read performance
- Database indexing
- Reporting capabilities

### 8.2 Indexes
Vendor fields on stock moves have `index=True` for efficient filtering and grouping.

---

## 9. Post-Migration Optimization

### Optional Enhancements for Odoo 19:

1. **Add Security Rules** (if needed):
   ```xml
   <record id="access_purchase_order_line" model="ir.model.access">
       <field name="name">Purchase Order Line Access</field>
       ...
   </record>
   ```

2. **Add Translations**:
   Create `i18n/` folder with `.po` files for multi-language support

3. **Add Tests**:
   Create `tests/` folder with Python unit tests

---

## 10. Rollback Plan

If issues occur after migration:

1. **Restore Database Backup**
   ```bash
   pg_restore -d your_database your_backup.dump
   ```

2. **Downgrade Odoo**
   Return to Odoo 16 installation

3. **Report Issues**
   Document any unexpected behavior for troubleshooting

---

## 11. Success Criteria

Migration is successful when:
- ✅ Module installs without errors
- ✅ All views render correctly
- ✅ Computed fields calculate accurately
- ✅ No Python errors in logs
- ✅ Performance is acceptable
- ✅ All tests pass

---

## Additional Resources

- **Odoo 17 Release Notes:** https://www.odoo.com/odoo-17-release-notes
- **Odoo 18 Release Notes:** https://www.odoo.com/odoo-18-release-notes  
- **Odoo 19 Documentation:** https://www.odoo.com/documentation/19.0/
- **OCA Migration Guide:** https://github.com/OCA/maintainer-tools

---

## Support

For issues or questions:
- Check Odoo logs: `/var/log/odoo/odoo.log`
- Enable debug mode in Odoo
- Review Odoo community forums
- Contact Topaz Team support

---

**Migration Prepared By:** Claude AI Assistant  
**Date:** February 11, 2026  
**Module Version:** 19.0.1.0.0
