# Migration Guide: Encopedia RSMS API
## Odoo 16 → Odoo 19

---

## Summary of All Changes

This module had **3 breaking changes** when moving from Odoo 16 to Odoo 19.

---

## Change 1 — Route Type: `type='json'` → `type='http'` ⚠️ CRITICAL

**This was the root cause of the 404 error in Postman.**

### Before (Odoo 16)
```python
@http.route('/api/rsms/invoices', type='json', auth='public', methods=['POST'], csrf=False)
```

### After (Odoo 19)
```python
@http.route(
    '/api/rsms/invoices',
    type='http',
    auth='public',
    methods=['POST'],
    csrf=False,
    save_session=False,  # ← also added
)
```

### Why?
In Odoo 19, `type='json'` routes **only** accept the full JSON-RPC 2.0 envelope format:
```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "date_from": "2024-01-01",
    "date_to": "2024-12-31"
  }
}
```
When a plain REST body is sent (as Postman does), Odoo cannot match the route and forwards
the request to the `website` module's 404 handler — returning an HTML error page instead of JSON.

Using `type='http'` allows us to handle the raw request body ourselves, which is correct
for any REST API consumed by external clients.

`save_session=False` prevents Odoo from trying to write a session cookie for a
stateless public API request, avoiding silent failures.

---

## Change 2 — Reading the Request Body

When switching from `type='json'` to `type='http'`, Odoo no longer parses the body
automatically. We must read and parse it manually.

### Before (Odoo 16 — auto-parsed by type='json')
```python
# Body was available via kwargs or request.jsonrequest
data = request.jsonrequest
```

### After (Odoo 19 — manual read required for type='http')
```python
raw_body = request.httprequest.get_data(as_text=True)
data = json.loads(raw_body) if raw_body else {}
```

---

## Change 3 — Switching User Environment

### Before (Odoo 16)
```python
request.update_env(user=key_record.user_id)
```

### After (Odoo 19)
```python
# Create a scoped env — do NOT mutate request.env directly
env = request.env(user=key_record.user_id.id)
```

### Why?
- `request.update_env()` was removed in Odoo 17+
- Directly assigning `request.env = ...` is dangerous as it mutates a global object
- The correct pattern is to create a local `env` variable scoped to the request

---

## Change 4 — Response Format

Since we switched to `type='http'`, we can no longer return plain dicts.
We must return a proper `Response` object.

### Before (Odoo 16 — dict returned directly)
```python
return {"success": True, "invoices": [...]}
return api_error("AUT001", "Missing key")
```

### After (Odoo 19 — Response object required)
```python
from odoo.http import Response
import json

def api_error(code, message, status=200):
    body = json.dumps({"success": False, "error": {"code": code, "message": message}})
    return Response(body, status=status, mimetype='application/json')

def api_success(data):
    return Response(json.dumps(data), status=200, mimetype='application/json')
```

---

## What Did NOT Change

| Item | Status |
|------|--------|
| Route path `/api/rsms/invoices` | ✅ Unchanged |
| API key authentication logic | ✅ Unchanged |
| Invoice search domain | ✅ Unchanged |
| Analytic distribution filtering | ✅ Unchanged |
| Response JSON structure | ✅ Unchanged |
| `auth_api_key` dependency | ✅ Unchanged |

---

## File Structure

```
encopedia_rsms_api/
├── __init__.py               → from . import controllers
├── __manifest__.py           → version bumped to 19.0.1.0.0
└── controllers/
    ├── __init__.py           → from . import main
    └── main.py               → all fixes applied here
```

---

## Installation

```bash
# 1. Copy module to your addons folder
# 2. Restart Odoo
# 3. Install from Apps menu (search "Encopedia RSMS API")
# OR via command line:
./odoo-bin -d your_database -i encopedia_rsms_api --stop-after-init
```

---

## Postman Setup

| Setting | Value |
|---------|-------|
| Method | `POST` |
| URL | `http://localhost:8080/api/rsms/invoices` |
| Header: `Authorization` | `your_api_key_here` |
| Header: `Content-Type` | `application/json` |
| Body (raw JSON) | `{"date_from": "2024-01-01", "date_to": "2024-12-31"}` |

### Expected Response
```json
{
    "success": true,
    "application": "Encopedia RSMS",
    "count": 3,
    "invoices": [
        {
            "invoice_number": "INV/2024/00001",
            "invoice_type": "invoice",
            "invoice_date": "2024-01-15",
            "total_discount": 50.00,
            "subtotal": 1000.00,
            "tax_total": 150.00,
            "total": 1150.00
        }
    ]
}
```

### Error Response Format
```json
{
    "success": false,
    "error": {
        "code": "AUT001",
        "message": "Missing Authorization header"
    }
}
```

---

## Error Code Reference

| Code | Meaning | HTTP Status |
|------|---------|-------------|
| `AUT001` | Missing Authorization header | 401 |
| `AUT002` | Invalid or unknown API key | 401 |
| `REQ001` | Empty or invalid JSON body | 400 |
| `REQ002` | Missing date_from or date_to | 400 |
| `ANA001` | No analytic accounts found starting with '9' | 200 |
| `DAT001` | No posted invoices in date range | 200 |
| `DAT002` | Invoices found but none matched analytic rules | 200 |
| `SRV001` | Unexpected server error | 500 |