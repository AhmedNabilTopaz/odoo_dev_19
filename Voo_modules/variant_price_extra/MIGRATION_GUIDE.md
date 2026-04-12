# Migration & Module Guide: variant_price_extra
## Odoo 16 → Odoo 19

---

## Complete List of All Changes

---

### 1. `__manifest__.py`
| What | Before     | After |
|------|------------|-------|
| Version | `16.0.0.0` | `19.0.1.0.0` |
| Category | `Sales/Sales` | `Sales/Sales` |
| No dependencies | — | Still only depends on `product` |

---

### 2. Python — `models/product_product.py`
- Added fields:
  - `wk_extra_price` — manually set extra price for the variant.
  - `attr_price_extra` — computed sum of all attribute price extras.
  - `price_extra` — computed sum of `attr_price_extra + wk_extra_price`.
- `@api.depends` used on `_compute_product_price_extra`:
```python
@api.depends('product_template_attribute_value_ids.price_extra', 'wk_extra_price')
def _compute_product_price_extra(self):
    for product in self:
        price_extra = sum(product.product_template_attribute_value_ids.mapped('price_extra'))
        product.attr_price_extra = price_extra
        product.price_extra = price_extra + product.wk_extra_price
