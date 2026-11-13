import re
import json

def extract_model_data():
    libapp_path = "extracted/lib/arm64-v8a/libapp.so"
    with open(libapp_path, "rb") as f:
        data = f.read()

    # Find all printable strings of length >= 3
    pattern = re.compile(rb"[\x20-\x7e]{3,}")
    raw_strings = [m.group(0).decode("latin1") for m in pattern.finditer(data)]

    # Collect Dart package files
    package_files = [s for s in raw_strings if s.startswith("package:rn_mobile_pos_flutter/")]
    
    # Models, entities, requests
    model_files = [s for s in package_files if any(k in s for k in ["_model.dart", "_entity.dart", "_request.dart", "response.dart"])]

    # Search for JSON keys / field names (typically camelCase or snake_case, surrounded by getters/setters or JSON serialization)
    # Dart names often appear with dyn:get: or _name@hash
    fields = set()
    for s in raw_strings:
        if s.startswith("dyn:get:"):
            fields.add(s[8:])
        elif "@" in s and not s.startswith("http") and not "@email" in s:
            parts = s.split("@")
            if len(parts) == 2 and parts[1].isdigit() and len(parts[0]) > 2:
                fields.add(parts[0])

    # Filter standard dart internals
    dart_internals = {"_parent", "_value", "_index", "_root", "_name", "_key", "_length", "_data"}
    cleaned_fields = sorted([f for f in fields if f not in dart_internals and not f.startswith("__")])

    # Find JSON map keys: words matching common JSON patterns
    json_candidate_pattern = re.compile(r"^[a-z][a-zA-Z0-9_]{2,30}$")
    candidate_keys = sorted(set([s for s in raw_strings if json_candidate_pattern.match(s) and not s.startswith("dyn:")]))

    output = {
        "model_files": sorted(set(model_files)),
        "recovered_class_fields": cleaned_fields,
        "sample_json_keys": [k for k in candidate_keys if any(term in k.lower() for term in [
            "id", "name", "price", "stock", "qty", "quantity", "discount", "fee", "tax", 
            "token", "user", "role", "email", "phone", "address", "image", "status",
            "total", "subtotal", "payment", "method", "change", "cash", "note", "code"
        ])][:120]
    }

    with open("recovered_model_schemas.json", "w", encoding="utf-8") as out:
        json.dump(output, out, indent=2)

    print(f"Recovered {len(output['model_files'])} model/entity files.")
    print(f"Recovered {len(output['recovered_class_fields'])} internal class fields.")
    print(f"Extracted {len(output['sample_json_keys'])} business domain JSON keys.")

if __name__ == "__main__":
    extract_model_data()
