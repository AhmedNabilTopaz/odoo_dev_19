# Migration Guide: topaz_voo_editing
## Odoo 15 → Odoo 19

---

## Complete List of All Changes

---

### 1. `__manifest__.py`

| What | Before | After |
|------|--------|-------|
| Version | `16.0.0.0` | `19.0.1.0.0` |
| Added dependency | — | `auth_api_key`, `stock_account` |
| Category | `Sales` | `Inventory/Purchase` |

---

### 2. Python — Removed Unnecessary Imports

Files cleaned:

- `stock_move.py`
- `stock_picking.py`
- `stock_picking_type.py`
- `stock_quant.py`
- `account_move.py`

Removed unstable internal imports that may break on core refactors.

```python
# REMOVED ❌
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_datetime
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from ast import literal_eval
from itertools import groupby
from operator import attrgetter, itemgetter
from collections import defaultdict
import time
```

---

### 3. `models/stock_move.py`

- Moved `to_delete` field here from incorrect placement
- Added `readonly=True` to related field

---

### 4. `models/stock_move_line.py` — Naming Bug Fix

```python
# BEFORE ❌
vendor_id = fields.Many2one(...)
def _compute_vendor_id(self):
    line.vendor_ids = [(6, 0, partners.ids)]

# AFTER ✅
vendor_ids = fields.Many2many(comodel_name='res.partner', ...)
def _compute_vendor_ids(self):
    line.vendor_ids = [(6, 0, partners.ids)]
```

---

### 5. `models/stock_picking.py`

Removed deprecated `states=` parameter (Odoo 17+ removed support).

```python
# REMOVED ❌
expense_location_id = fields.Many2one(
    ...
    states={'done': [('readonly', True)]}
)
```

Readonly-on-done is now handled in XML via inline expressions.

---

### 6. `models/product.py`

#### Fix 1 — `taxes_id` → `tax_ids`

```python
# BEFORE ❌
taxes_id = fields.Many2many(related='product_tmpl_id.taxes_id')

# AFTER ✅
tax_ids = fields.Many2many(related='product_tmpl_id.taxes_id')
```

---

#### Fix 2 — Selection Field Setter Fix

```python
# BEFORE ❌
def set_status_True(self):
    product.status_topaz = True

# AFTER ✅
def set_status_enabled(self):
    product.status_topaz = 'enabled'

def set_status_disabled(self):
    product.status_topaz = 'disabled'
```

⚠ If any XML buttons reference `set_status_True` or `set_status_False`, update them.

---

### 7. `models/account_move.py`

#### Fix 1 — `@api.model_create_multi`

```python
# BEFORE ❌
@api.model
def create(self, vals):
    move = super().create(vals)

# AFTER ✅
@api.model_create_multi
def create(self, vals_list):
    moves = super().create(vals_list)
```

---

#### Fix 2 — `@api.onchange` → `@api.depends`

```python
# BEFORE ❌
@api.onchange('move_id')
def _compute_source_location(self): ...

# AFTER ✅
@api.depends('stock_move_id', 'stock_move_id.location_id')
def _compute_source_location(self): ...
```

---

#### Fix 3 — Removed `print()` Debug Statements

```python
# BEFORE ❌
print(move)

# AFTER ✅
_logger.debug("Move: %s", move.name)
```

---

### 8. `data/discuss_channel.xml`

```xml
<!-- BEFORE ❌ -->
<record model="mail.channel">

<!-- AFTER ✅ -->
<record model="discuss.channel">
```

---

### 9. XML Views — `attrs={}` → Inline Expressions (Odoo 17+)

```xml
<!-- BEFORE ❌ -->
attrs="{'invisible': [('is_expense','=',False)]}"

<!-- AFTER ✅ -->
invisible="not is_expense"
```

All conditional attributes updated accordingly.

---

### 10. XML Views — `<tree>` → `<list>` (Odoo 17+)

```xml
<!-- BEFORE ❌ -->
<tree>...</tree>
view_mode="tree,form"

<!-- AFTER ✅ -->
<list>...</list>
view_mode="list,form"
```

Updated in:

- `vending_machine_views.xml`
- `stock_valuation_layer_tree.xml`
- `account_move_views.xml`

---

### 11. Controllers — Full REST Refactor

Changes applied:

- `type='json'` → `type='http'`
- `save_session=False`
- Proper `request.env(user=id)`
- `request.httprequest.get_data(as_text=True)`
- Proper JSON `Response`
- Extracted shared helpers

---

### 12. `models/vending_machine.py`

```python
active = fields.Boolean(default=True)
```

---

## ⚠ 13. TODO (Post-Migration) — Stock Valuation Layer Review

### File:
`models/stock_valuation_layer.py`

### Status:
⚠ Functional validation required after migration

Although the module installs successfully, **stock valuation logic must be reviewed carefully** due to major internal changes in Odoo 17–19.

---

### Why This Needs Review

Odoo 17+ introduced:

- Refactored valuation posting logic
- Changes in FIFO handling
- Changes in Anglo-Saxon accounting flow
- Stronger integration with `stock_account`
- Refactoring of `_create_account_move_line()` and valuation helpers

Even if the code loads, behavior must be validated functionally.

---

### Required Post-Migration Checks

#### 1️⃣ Validate Related Fields

Confirm all related fields still correctly reference:

- `stock.move`
- `account.move`
- `product.product`
- `company_id`

Ensure no renamed or removed core fields.

---

#### 2️⃣ End-to-End Testing Scenarios

Test carefully:

- Incoming shipment (vendor receipt)
- Outgoing delivery
- Product return
- Inventory adjustment
- Vendor bill (Anglo-Saxon)
- Multi-company environment

Verify correct creation of valuation layers and accounting entries.

---

#### 3️⃣ Performance Review

If any computed fields:

- Avoid heavy `.search()` in compute
- Avoid unnecessary `store=True`
- Use batch computation

---

#### 4️⃣ Accounting Link Validation

Ensure:

- Proper linkage with `account.move.line`
- No orphan valuation layers
- No incorrect cost propagation

---

### IMPORTANT

Do NOT modify stock valuation logic blindly.

Incorrect changes can corrupt:

- Inventory valuation
- COGS
- Financial statements
- Balance sheet

All validation must be done on a staging copy of production DB.

---

## Final Status

| Area | Status |
|------|--------|
| Syntax Migration | ✅ Completed |
| XML Migration | ✅ Completed |
| Controller Refactor | ✅ Completed |
| Stock Valuation Logic | ⚠ Pending Functional Review |

---

End of Migration Guide.
