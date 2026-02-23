# Encopedia RSMS API
### Odoo 19 — Revenue Share Management System

---

## Overview

A REST API module that exposes posted customer invoices filtered by analytic location accounts, used by the Encopedia Revenue Share Management System (RSMS).

**Version:** 19.0.1.0.0  
**Author:** Topaz Smart  
**License:** OPL-1

---

## Dependencies

- `account`
- `account_accountant`
- `stock`
- `auth_api_key`

---

## API Reference

### `POST /api/rsms/invoices`

Returns posted customer invoices within a date range, filtered to only include invoices with lines assigned to analytic accounts whose names start with `9` (location accounts).

#### Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | ✅ | Your API key (raw, no "Bearer" prefix) |
| `Content-Type` | ✅ | Must be `application/json` |

#### Request Body

```json
{
    "date_from": "2024-01-01",
    "date_to":   "2024-12-31"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `date_from` | string (YYYY-MM-DD) | ✅ | Start of date range |
| `date_to` | string (YYYY-MM-DD) | ✅ | End of date range |

#### Success Response

```json
{
    "success": true,
    "application": "Encopedia RSMS",
    "count": 2,
    "invoices": [
        {
            "invoice_number": "INV/2024/00001",
            "invoice_type":   "invoice",
            "invoice_date":   "2024-03-15",
            "total_discount": 100.00,
            "subtotal":       900.00,
            "tax_total":      135.00,
            "total":          1035.00
        }
    ]
}
```

#### Error Response

```json
{
    "success": false,
    "error": {
        "code":    "AUT002",
        "message": "Invalid or unknown API key"
    }
}
```

#### Error Codes

| Code | Meaning |
|------|---------|
| `AUT001` | Missing `Authorization` header |
| `AUT002` | Invalid API key |
| `REQ001` | Empty / invalid JSON body |
| `REQ002` | Missing `date_from` or `date_to` |
| `ANA001` | No analytic accounts starting with `9` |
| `DAT001` | No posted invoices in range |
| `DAT002` | Invoices found but none matched location rules |
| `SRV001` | Unexpected server error |

---

## How the Location Filter Works

The API only returns invoices where at least one line has an **analytic distribution** pointing to an analytic account whose **name starts with `9`**.

These accounts represent physical locations in the revenue-sharing setup. Lines without such an account are ignored, and invoices with no valid lines are excluded entirely.

---

## Installation

1. Copy the `encopedia_rsms_api` folder into your Odoo custom addons directory
2. Restart the Odoo server
3. Go to **Apps → Update Apps List**
4. Search for **"Encopedia RSMS API"** and click **Install**

Or via command line:
```bash
./odoo-bin -d your_database -i encopedia_rsms_api --stop-after-init
```

---

## Creating an API Key in Odoo

1. Go to **Settings → Technical → API Keys**  
   *(requires developer mode)*
2. Click **Create**
3. Set a name, assign a user
4. Copy the generated key
5. Use that key as the `Authorization` header value in Postman

---

## Postman Quick Start

1. **Method:** `POST`
2. **URL:** `http://your-odoo-server/api/rsms/invoices`
3. **Headers:**
   - `Authorization`: `paste-your-api-key-here`
   - `Content-Type`: `application/json`
4. **Body → raw → JSON:**
```json
{
    "date_from": "2024-01-01",
    "date_to": "2024-12-31"
}
```
5. Click **Send**

---

## Changelog

### 19.0.1.0.0
- Migrated from Odoo 16 to Odoo 19
- Changed route type from `json` to `http` (fixes 404 in Postman)
- Replaced `request.update_env()` with scoped `env` variable
- Replaced dict returns with proper `Response` objects
- Added `save_session=False` to route decorator
- Manual JSON body parsing for `type='http'` routes