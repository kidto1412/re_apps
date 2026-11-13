import re
import json

def extract_detailed_domain_schemas():
    libapp_path = "extracted/lib/arm64-v8a/libapp.so"
    with open(libapp_path, "rb") as f:
        data = f.read()

    # Domain features we care about
    targets = [
        "auth",
        "product",
        "category",
        "transaction",
        "stock_opname",
        "subscription",
        "customer",
        "supplier",
        "additional_fee",
        "discount",
        "employee"
    ]

    pattern = re.compile(rb"[\x20-\x7e]{3,}")
    all_strings = [m.group(0).decode("latin1") for m in pattern.finditer(data)]

    # Extract all getter / setter field definitions from Dart
    getters = set()
    for s in all_strings:
        if s.startswith("dyn:get:"):
            getters.add(s[8:])

    # Domain-specific keyword matching
    domain_map = {}
    for t in targets:
        domain_map[t] = []

    # Map getters into domains
    domain_keywords = {
        "auth": ["token", "email", "password", "username", "role", "owner", "staff", "user", "profile", "jwt", "refresh", "auth"],
        "product": ["product", "sku", "barcode", "price", "stock", "cost", "unit", "image", "category_id", "sell_price"],
        "category": ["category", "category_id", "category_name", "icon"],
        "transaction": ["transaction", "cart", "total", "subtotal", "payment", "cash", "change", "invoice", "receipt", "item", "qty", "quantity", "order"],
        "stock_opname": ["stock_opname", "opname", "physical_stock", "difference", "system_stock", "adjust", "movement"],
        "subscription": ["subscription", "plan", "kaserapay", "billing", "expiry", "pro", "upgrade", "feature"],
        "customer": ["customer", "phone", "email", "address", "member"],
        "supplier": ["supplier", "supplier_name", "supplier_phone", "company"],
        "additional_fee": ["fee", "additional_fee", "percentage", "fixed"],
        "discount": ["discount", "percent", "nominal", "active", "discount_type", "promo"],
        "employee": ["employee", "staff", "pin", "role", "branch", "outlet"]
    }

    results = {}
    for domain, kws in domain_keywords.items():
        matched_getters = set()
        matched_json_keys = set()
        for g in getters:
            g_lower = g.lower()
            if any(k in g_lower for k in kws):
                matched_getters.add(g)

        # Look in general strings for camelCase / snake_case matches
        for s in all_strings:
            s_lower = s.lower()
            if any(k in s_lower for k in kws) and re.match(r"^[a-zA-Z0-9_]{3,30}$", s):
                if not s.startswith("package:") and not s.startswith("dart:"):
                    matched_json_keys.add(s)

        results[domain] = {
            "dart_getters": sorted(list(matched_getters)),
            "associated_keys": sorted(list(matched_json_keys))[:25]
        }

    with open("domain_schemas_extracted.json", "w", encoding="utf-8") as out:
        json.dump(results, out, indent=2)

    print("Extracted detailed domain schemas successfully.")

if __name__ == "__main__":
    extract_detailed_domain_schemas()
