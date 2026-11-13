import re
import json

def extract_payload_details():
    libapp_path = "extracted/lib/arm64-v8a/libapp.so"
    with open(libapp_path, "rb") as f:
        data = f.read()

    pattern = re.compile(rb"[\x20-\x7e]{3,}")
    all_strings = [m.group(0).decode("latin1") for m in pattern.finditer(data)]

    # Search for validation messages and error responses to deduce required fields
    validation_messages = [
        s for s in all_strings if any(kw in s.lower() for kw in [
            "wajib diisi", "tidak boleh kosong", "harus diisi", "minimal", "tidak valid", 
            "tidak sesuai", "tidak ditemukan", "berhasil", "gagal"
        ])
    ]

    # Search for JSON envelope keys (e.g. data, message, statusCode, meta, etc.)
    envelope_candidates = ["success", "status", "statusCode", "message", "data", "meta", "errors", "token", "access_token", "refresh_token"]
    found_envelopes = [k for k in envelope_candidates if k in all_strings]

    # Map validation messages to likely fields
    field_rules = {}
    for msg in validation_messages:
        msg_clean = msg.strip()
        if len(msg_clean) > 4 and len(msg_clean) < 80:
            field_rules[msg_clean] = True

    # Identify specific request payload fields
    # Look for strings surrounding known model keys in the binary
    auth_fields = []
    transaction_fields = []
    product_fields = []

    for s in all_strings:
        s_low = s.lower()
        if s in ["email", "username", "password", "confirm_password", "phone_number", "role", "store_name", "business_type_id"]:
            auth_fields.append(s)
        elif s in ["total_amount", "subtotal", "tax", "discount_id", "additional_fee_id", "payment_method", "cash_amount", "change_amount", "items"]:
            transaction_fields.append(s)
        elif s in ["product_name", "category_id", "sku", "barcode", "buy_price", "sell_price", "stock"]:
            product_fields.append(s)

    results = {
        "api_response_envelope": found_envelopes,
        "auth_payload_fields": sorted(list(set(auth_fields))),
        "transaction_payload_fields": sorted(list(set(transaction_fields))),
        "product_payload_fields": sorted(list(set(product_fields))),
        "validation_rules_and_messages": sorted(list(field_rules.keys()))
    }

    with open("api_payload_contracts.json", "w", encoding="utf-8") as f_out:
        json.dump(results, f_out, indent=2)

    print(f"Extracted {len(results['validation_rules_and_messages'])} validation constraints.")
    print(f"Envelope keys: {results['api_response_envelope']}")

if __name__ == "__main__":
    extract_payload_details()
