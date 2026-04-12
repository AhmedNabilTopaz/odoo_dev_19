# Complete Testing Guide: Subtotal Received PO Module
## Odoo 19 Migration Testing

---

## 🎯 Testing Overview

This guide walks you through testing your migrated module step-by-step, from installation to verifying all features work correctly.

**Time Required:** 30-45 minutes  
**Prerequisites:** Access to Odoo 19 test environment

---

## Part 1: Pre-Installation Testing

### Step 1: Verify Python Version

```bash
# Check Python version (must be 3.10 or higher)
python3 --version

# Expected output: Python 3.10.x or Python 3.11.x or higher
```

✅ **Pass if:** Version shows 3.10 or higher  
❌ **Fail if:** Version is 3.9 or lower → Upgrade Python first

---

### Step 2: Backup Your Database

**CRITICAL: Always test on a copy of your database!**

```bash
# Create a backup
pg_dump your_database > backup_before_migration_$(date +%Y%m%d).sql

# Or create a duplicate test database
createdb test_database
pg_dump your_database | psql test_database
```

✅ **Pass if:** Backup file created successfully

---

### Step 3: Verify Odoo 19 Installation

```bash
# Check Odoo version
./odoo-bin --version

# Expected output: Odoo Server 19.0
```

✅ **Pass if:** Shows version 19.0

---

## Part 2: Module Installation

### Step 4: Extract and Place Module

```bash
# Extract the archive
cd /path/to/downloads
tar -xzf subtotal_received_po_odoo19.tar.gz

# Move to Odoo addons directory
sudo mv subtotal_received_po_odoo19 /path/to/odoo/addons/
# Example: sudo mv subtotal_received_po_odoo19 /opt/odoo/addons/

# Set proper permissions
sudo chown -R odoo:odoo /path/to/odoo/addons/subtotal_received_po_odoo19
```

✅ **Pass if:** Files copied successfully with correct permissions

---

### Step 5: Update Apps List

**Method A: Command Line**
```bash
./odoo-bin -d test_database --stop-after-init
```

**Method B: Web Interface**
1. Login to Odoo
2. Go to Settings (⚙️)
3. Activate Developer Mode:
   - Settings → Developer Tools → Activate Developer Mode
4. Go to Apps
5. Click "Update Apps List"
6. Click "Update" in the dialog

✅ **Pass if:** No errors appear in terminal or interface

---

### Step 6: Install/Upgrade the Module

**For Fresh Installation:**

```bash
# Command line installation
./odoo-bin -d test_database -i subtotal_received_po --stop-after-init

# Check logs for errors
tail -f /var/log/odoo/odoo.log
```

**For Upgrading Existing Odoo 16 Module:**

```bash
# Upgrade command
./odoo-bin -d test_database -u subtotal_received_po --stop-after-init

# Check logs
tail -f /var/log/odoo/odoo.log
```

**Via Web Interface:**
1. Apps → Remove "Apps" filter
2. Search: "subtotal received"
3. Click "Install" or "Upgrade"

✅ **Pass if:** 
- Installation completes without errors
- Log shows: "Module subtotal_received_po: loading successful"
- No Python errors or warnings

❌ **Common Issues:**

**Error: "Module not found"**
- Solution: Check module is in addons path
- Run: `./odoo-bin --addons-path=/path/to/addons`

**Error: "Dependencies not met"**
- Solution: Install stock, sale, purchase modules first

---

## Part 3: Functional Testing

### Test Case 1: Purchase Order Line - Received Amounts

**Objective:** Verify that received amounts calculate correctly

**Steps:**

1. **Create a Purchase Order**
   - Go to: Purchase → Orders → Create
   - Select Vendor: (any vendor)
   - Click "Add a product"

2. **Add Product Line**
   - Product: Choose any stockable product
   - Quantity: 100
   - Unit Price: 50.00
   - Taxes: Select a 10% tax
   - Click "Save"

3. **Confirm the Order**
   - Click "Confirm Order"
   - Status should change to "Purchase Order"

4. **Partial Receipt**
   - Click "Receive Products" button
   - Set Quantity Done: 30 (instead of 100)
   - Click "Validate"

5. **Check Received Amounts**
   - Return to Purchase Order (click the PO reference)
   - Look at the order line
   - Verify these fields appear:

**Expected Results:**

| Field | Expected Value | Formula |
|-------|---------------|---------|
| Subtotal Received | 1,500.00 | 30 × 50.00 |
| Product Barcode | [Product's barcode] | Related field |

**At bottom of form, verify:**

| Field | Expected Value |
|-------|---------------|
| Untaxed Received | 1,500.00 |
| Taxes Received | 150.00 |
| Total Received | 1,650.00 |

✅ **Pass if:** All amounts match expected values  
❌ **Fail if:** Amounts are 0.00 or incorrect

**Troubleshooting:**
```python
# If amounts show 0.00, force recomputation
# In Odoo shell:
./odoo-bin shell -d test_database

# Run these commands:
po = self.env['purchase.order'].search([('name', '=', 'PO00001')])
po.order_line._compute_amount_received()
po._compute_amount_received_total()
print(f"Total Received: {po.amount_received_total}")
```

---

### Test Case 2: Tax Calculations

**Objective:** Verify tax computations are accurate

**Steps:**

1. **Create PO with Multiple Tax Rates**
   - Line 1: Qty 10, Price 100, Tax 10% (VAT 10%)
   - Line 2: Qty 20, Price 50, Tax 5% (Sales Tax 5%)
   - Confirm order

2. **Receive Different Quantities**
   - Line 1: Receive 5 (half)
   - Line 2: Receive 10 (half)
   - Validate

3. **Verify Calculations**

**Expected Results:**

| Line | Qty Recv | Price | Tax | Subtotal | Tax Amt | Total |
|------|----------|-------|-----|----------|---------|-------|
| 1 | 5 | 100 | 10% | 500.00 | 50.00 | 550.00 |
| 2 | 10 | 50 | 5% | 500.00 | 25.00 | 525.00 |

**Order Totals:**
- Untaxed Received: 1,000.00
- Taxes Received: 75.00
- Total Received: 1,075.00

✅ **Pass if:** All calculations correct  
❌ **Fail if:** Tax amounts wrong

---

### Test Case 3: Discount Handling

**Objective:** Verify discounts are applied correctly

**Steps:**

1. **Create PO with Discount**
   - Product: Any
   - Quantity: 100
   - Unit Price: 50.00
   - Discount: 10%
   - Tax: 10%
   - Confirm

2. **Receive Products**
   - Quantity Done: 40
   - Validate

3. **Verify Calculations**

**Expected Results:**
- Base amount: 40 × 50.00 = 2,000.00
- After discount: 2,000.00 × 0.90 = 1,800.00
- Tax (10%): 1,800.00 × 0.10 = 180.00
- Total: 1,980.00

**Check:**
- Subtotal Received: 1,800.00
- Tax Received: 180.00
- Total Received: 1,980.00

✅ **Pass if:** Discount applied before tax calculation

---

### Test Case 4: Vendor Tracking on Stock Moves

**Objective:** Verify vendor information flows to stock moves

**Steps:**

1. **Create and Confirm PO**
   - Vendor: "Azure Interior" (or any vendor)
   - Product: Any stockable product
   - Quantity: 50
   - Confirm order

2. **Receive Products**
   - Receive all 50 units
   - Validate

3. **Check Stock Move**
   - Go to: Inventory → Reporting → Moves History
   - Find the move for the product you received
   - Click to open details

**Expected Results:**
- Field "Vendor" should show: "Azure Interior"
- Vendor field should be read-only
- Vendor should be indexed for fast searching

4. **Test Grouping by Vendor**
   - In Moves History
   - Click "Group By" → "Vendor"
   - Should see moves grouped by vendor name

✅ **Pass if:** Vendor appears and grouping works

---

### Test Case 5: Product Barcode Display

**Objective:** Verify barcode shows in purchase order lines

**Steps:**

1. **Set Product Barcode**
   - Go to: Inventory → Products
   - Select a product
   - Set Barcode: "1234567890"
   - Save

2. **Create PO with This Product**
   - Add product to PO line
   - Look for "Barcode" column

**Expected Results:**
- Barcode column shows: "1234567890"
- Column is optional (can be hidden/shown)
- Barcode is read-only

✅ **Pass if:** Barcode displays correctly

---

### Test Case 6: KPI Tree View

**Objective:** Verify received totals in list view

**Steps:**

1. **Create Multiple POs**
   - PO1: Total Received = 1,000.00
   - PO2: Total Received = 2,500.00
   - PO3: Total Received = 750.00

2. **Go to KPI View**
   - Purchase → Orders
   - Switch to List view
   - Look for columns:
     - Amount Received Total
     - Date Approved
     - Effective Date

**Expected Results:**
- All three columns visible (may need to show optional columns)
- "Total Received" column shows correct amounts
- Bottom shows sum: 4,250.00

✅ **Pass if:** Amounts display and sum correctly

---

### Test Case 7: Multiple Receipts

**Objective:** Test incremental receiving

**Steps:**

1. **Create PO**
   - Quantity: 100
   - Price: 10.00
   - Tax: 10%

2. **First Receipt**
   - Receive: 30 units
   - Check Total Received: 330.00 (30 × 10 × 1.1)

3. **Second Receipt**
   - Receive: 25 more units
   - Check Total Received: 605.00 (55 × 10 × 1.1)

4. **Third Receipt**
   - Receive: 45 more units
   - Check Total Received: 1,100.00 (100 × 10 × 1.1)

**Expected Results:**
- Each receipt updates the amounts
- Final total matches full order with tax

✅ **Pass if:** Amounts accumulate correctly

---

## Part 4: Performance Testing

### Test Case 8: Large Order Performance

**Objective:** Verify performance with many lines

**Steps:**

1. **Create Large PO**
   - Add 50 product lines
   - Vary quantities and prices
   - Confirm order

2. **Receive All Products**
   - Receive products
   - Time the computation

**Expected Results:**
- Computation completes in < 5 seconds
- No lag in UI
- All amounts calculate correctly

✅ **Pass if:** Performance acceptable  
⚠️ **Warning if:** Takes > 10 seconds

---

### Test Case 9: Database Query Efficiency

**Objective:** Check for N+1 query issues

```bash
# Enable query logging
# In odoo.conf add:
# log_level = debug_sql

# Restart Odoo
./odoo-bin -c /etc/odoo.conf

# Open a purchase order
# Check logs for number of queries
grep "SELECT" /var/log/odoo/odoo.log | wc -l
```

✅ **Pass if:** Reasonable number of queries (< 100 for one PO)

---

## Part 5: Edge Cases Testing

### Test Case 10: Zero Quantities

**Steps:**
1. Create PO
2. Don't receive anything (qty_received = 0)
3. Check amounts

**Expected:**
- All received amounts = 0.00
- No errors

✅ **Pass if:** Handles gracefully

---

### Test Case 11: Returns/Negative Quantities

**Steps:**
1. Receive 100 units
2. Return 20 units
3. Check amounts

**Expected:**
- Received amounts reflect net quantity (80)

✅ **Pass if:** Correctly handles returns

---

### Test Case 12: No Tax Scenario

**Steps:**
1. Create PO with no taxes
2. Receive products
3. Check amounts

**Expected:**
- Subtotal = Total (no tax)
- Tax Received = 0.00

✅ **Pass if:** Works without taxes

---

### Test Case 13: Complex Tax (Multiple Taxes)

**Steps:**
1. Add product with 2 taxes (10% VAT + 5% Sales Tax)
2. Receive products
3. Check tax calculation

**Expected:**
- Both taxes calculated correctly
- Total tax = sum of both

✅ **Pass if:** Multiple taxes handled

---

## Part 6: UI/UX Testing

### Test Case 14: Field Visibility

**Checklist:**
- [ ] Fields visible in form view
- [ ] Fields visible in tree view
- [ ] Optional fields can be hidden
- [ ] Monetary widget displays correctly
- [ ] Currency symbols show properly

---

### Test Case 15: Responsive Layout

**Test on:**
- [ ] Desktop browser (Chrome, Firefox)
- [ ] Tablet view
- [ ] Mobile browser (if applicable)

---

## Part 7: Compatibility Testing

### Test Case 16: With Other Modules

**Test alongside:**
- [ ] Purchase module standard features
- [ ] Inventory management
- [ ] Accounting integration
- [ ] Any custom modules you use

**Verify:**
- No JavaScript errors
- No Python conflicts
- Views render correctly

---

## Part 8: Regression Testing

### Test Case 17: Standard PO Features Still Work

**Verify these standard features work:**
- [ ] Create RFQ
- [ ] Send by email
- [ ] Print PO
- [ ] Create invoice
- [ ] Stock picking
- [ ] Backorders
- [ ] Cancellation

✅ **Pass if:** All standard features functional

---

## Part 9: Automated Testing (Optional)

### Test Case 18: Unit Tests

Create test file: `tests/test_received_amounts.py`

```python
from odoo.tests.common import TransactionCase

class TestReceivedAmounts(TransactionCase):
    
    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({'name': 'Test Vendor'})
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
        })
        self.tax = self.env['account.tax'].create({
            'name': 'Test Tax 10%',
            'amount': 10,
            'type_tax_use': 'purchase',
        })
    
    def test_received_amount_calculation(self):
        """Test that received amounts calculate correctly"""
        po = self.env['purchase.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 100,
                'price_unit': 50.0,
                'taxes_id': [(6, 0, [self.tax.id])],
            })],
        })
        
        line = po.order_line[0]
        line.qty_received = 30
        
        self.assertEqual(line.sub_total_received, 1500.0)
        self.assertEqual(line.price_tax_received, 150.0)
        self.assertEqual(line.price_total_received, 1650.0)
```

**Run tests:**
```bash
./odoo-bin -d test_database -i subtotal_received_po --test-enable --stop-after-init
```

---

## Part 10: Documentation Verification

### Test Case 19: Documentation Accuracy

**Checklist:**
- [ ] README.md reflects actual functionality
- [ ] Migration guide steps are accurate
- [ ] All mentioned features exist
- [ ] Code comments are accurate

---

## Testing Summary Checklist

### Installation ✓
- [ ] Python 3.10+ verified
- [ ] Database backed up
- [ ] Module installed without errors
- [ ] No warnings in logs

### Core Functionality ✓
- [ ] Received amounts calculate correctly
- [ ] Taxes compute accurately
- [ ] Discounts apply properly
- [ ] Vendor tracking works
- [ ] Barcode displays

### Views & UI ✓
- [ ] Form view renders correctly
- [ ] Tree/list view shows fields
- [ ] Optional fields work
- [ ] Widgets display properly

### Performance ✓
- [ ] Fast computation (< 5 sec)
- [ ] No lag with 50+ lines
- [ ] Query efficiency acceptable

### Edge Cases ✓
- [ ] Zero quantities handled
- [ ] Returns processed correctly
- [ ] No tax scenario works
- [ ] Multiple taxes supported

### Compatibility ✓
- [ ] Standard PO features work
- [ ] No module conflicts
- [ ] Other modules compatible

---

## Quick Test Script

For a fast smoke test, run this in Odoo shell:

```python
# Quick smoke test
./odoo-bin shell -d test_database

# Paste this:
# Create test PO
partner = env['res.partner'].create({'name': 'Test Vendor'})
product = env['product.product'].create({'name': 'Test Product', 'type': 'product'})
tax = env['account.tax'].create({'name': 'Tax 10%', 'amount': 10, 'type_tax_use': 'purchase'})

po = env['purchase.order'].create({
    'partner_id': partner.id,
    'order_line': [(0, 0, {
        'product_id': product.id,
        'product_qty': 100,
        'price_unit': 50.0,
        'taxes_id': [(6, 0, [tax.id])],
    })],
})

# Simulate receipt
po.order_line[0].qty_received = 30

# Check results
line = po.order_line[0]
print(f"Subtotal Received: {line.sub_total_received}")
print(f"Tax Received: {line.price_tax_received}")
print(f"Total Received: {line.price_total_received}")

# Expected output:
# Subtotal Received: 1500.0
# Tax Received: 150.0
# Total Received: 1650.0

# If all match, basic test PASSED! ✅
```

---

## When to Consider Testing Complete

✅ **Testing is complete when:**

1. All critical test cases pass (1-7)
2. No Python errors in logs
3. Performance is acceptable (Test 8)
4. Edge cases handled (Tests 10-13)
5. Standard PO features work (Test 17)
6. Documentation matches reality (Test 19)

---

## Reporting Issues

If tests fail, collect this information:

```bash
# 1. Check logs
tail -n 100 /var/log/odoo/odoo.log > error_log.txt

# 2. Get module info
./odoo-bin shell -d test_database
module = env['ir.module.module'].search([('name', '=', 'subtotal_received_po')])
print(f"Version: {module.latest_version}")
print(f"State: {module.state}")

# 3. Check field definitions
po = env['purchase.order.line']
print(po.fields_get(['sub_total_received', 'price_tax_received']))
```

Share:
- Error logs
- Test case that failed
- Expected vs actual results
- Odoo version and Python version

---

## Post-Testing Actions

After successful testing:

1. **Document any custom configurations** needed
2. **Train users** on new fields
3. **Update reports** if needed to include received amounts
4. **Plan production deployment**
5. **Schedule production backup**

---

**Testing Guide Version:** 1.0  
**Last Updated:** February 11, 2026  
**Module Version:** 19.0.1.0.0