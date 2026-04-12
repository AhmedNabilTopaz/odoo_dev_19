# Subtotal Received PO - Odoo 19

## Overview

This module extends Odoo's Purchase Order functionality to track and display received amounts with tax calculations based on `qty_received` instead of `product_qty`.

**Version:** 19.0.1.0.0  
**Odoo Version:** 19.0  
**License:** OPL-1  
**Author:** Topaz Team

---

## Features

### 1. Purchase Order Line Enhancements
- **Subtotal Received:** Calculates the subtotal for received quantities only
- **Tax Received:** Computes tax amounts on received quantities
- **Total Received:** Shows the total (subtotal + tax) for received items
- **Product Barcode:** Displays product barcode directly in order lines

### 2. Purchase Order Totals
- **Untaxed Received:** Sum of all received line subtotals
- **Taxes Received:** Sum of all received line taxes  
- **Total Received (Incl. Taxes):** Complete received amount with taxes

### 3. Stock Move Vendor Tracking
- Adds vendor information to stock moves and stock move lines
- Enables filtering and grouping stock movements by vendor
- Useful for vendor performance analysis

---

## Installation

### Requirements
- Odoo 19.0
- Python 3.10 or higher
- Modules: `stock`, `sale`, `purchase`

### Install Steps

1. Copy this module to your Odoo addons directory:
   ```bash
   cp -r subtotal_received_po /path/to/odoo/addons/
   ```

2. Update the apps list:
   - Activate Developer Mode
   - Go to Apps → Update Apps List

3. Install the module:
   - Search for "Subtotal Received PO"
   - Click Install

Or via command line:
```bash
./odoo-bin -d your_database -i subtotal_received_po --stop-after-init
```

---

## Usage

### Creating a Purchase Order with Partial Receipts

1. **Create Purchase Order:**
   - Go to Purchase → Orders → Create
   - Add products with quantities and prices
   - Confirm the order

2. **Receive Products Partially:**
   - Click "Receive Products"
   - Set received quantities (less than ordered)
   - Validate the receipt

3. **View Received Amounts:**
   - Return to the purchase order
   - See computed received amounts in the order lines
   - Check total received amounts at the bottom

### Using Vendor Filters in Stock Moves

1. Go to Inventory → Reporting → Moves History
2. Click "Group By" → "Vendor"
3. Analyze stock movements by supplier

---

## Technical Details

### Models Extended

#### `purchase.order.line`
- `sub_total_received` (Monetary): Computed subtotal for received qty
- `price_tax_received` (Monetary): Computed tax for received qty
- `price_total_received` (Monetary): Computed total for received qty
- `product_barcode` (Char): Related field from product

#### `purchase.order`
- `amount_received_untaxed` (Monetary): Sum of line subtotals
- `amount_received_tax` (Monetary): Sum of line taxes
- `amount_received_total` (Monetary): Sum of line totals

#### `stock.move` & `stock.move.line`
- `vendor_id` (Many2one res.partner): Related vendor from purchase order

### Computation Logic

The module uses Odoo's standard tax computation engine (`account.tax._compute_taxes`) to ensure accurate tax calculations that respect:
- Tax configurations (included/excluded)
- Fiscal positions
- Multi-tax scenarios
- Discounts

---

## Views Modified

### Purchase Order Form
- Added received amount fields in order lines
- Added received total fields below standard totals

### Purchase Order Tree (KPIs)
- Added `amount_received_total` column
- Added approval and effective dates

### Stock Move Line Search
- Added "Vendor" grouping option

---

## Compatibility

### Migrated From
- Odoo 16 version 16.0.0.0

### Breaking Changes from Odoo 16
- Python 3.10+ required (was 3.8+)
- Uses explicit `comodel_name` parameters in Many2one fields
- Enhanced field documentation and code structure

### Database Migration
- **Not required** - all field names unchanged
- Computed fields recalculate automatically on upgrade

---

## Testing

Run automated tests (if available):
```bash
./odoo-bin -d test_database -i subtotal_received_po --test-enable --stop-after-init
```

Manual testing checklist:
- [ ] Create PO with multiple lines
- [ ] Partially receive products
- [ ] Verify subtotals calculate correctly
- [ ] Check tax computations with multiple tax rates
- [ ] Test with discounts
- [ ] Verify vendor grouping in stock moves

---

## Troubleshooting

### Received Amounts Show 0.00
**Cause:** Computation hasn't triggered  
**Solution:** Modify a field that triggers recomputation (qty_received, price_unit, taxes_id)

### Module Won't Install
**Cause:** Missing dependencies  
**Solution:** Install `stock`, `sale`, and `purchase` modules first

### Tax Amounts Incorrect
**Cause:** Tax configuration issue  
**Solution:** Verify tax settings in Accounting → Configuration → Taxes

---

## Support

For issues, questions, or feature requests:
- **Website:** https://www.topazsmart.com
- **Email:** Contact Topaz Team support

---

## License

This module is licensed under OPL-1 (Odoo Proprietary License v1.0).

---

## Credits

**Authors:**
- Topaz Team

**Maintainer:**
- Topaz Smart

---

## Changelog

### Version 19.0.1.0.0 (2026-02-11)
- Migrated from Odoo 16 to Odoo 19
- Updated Python compatibility (3.10+)
- Enhanced code documentation
- Improved field definitions with explicit parameters
- Reorganized file structure for better maintainability
- Added comprehensive migration guide

### Version 16.0.0.0 (Original)
- Initial release for Odoo 16
- Basic received amount calculations
- Vendor tracking on stock moves
