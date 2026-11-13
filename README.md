# Kasera Mobile POS — Reverse-Engineered Architecture & Stack

Reconstructed backend API, relational data layer, typed client SDK, thermal receipt engine, and operational CLI reverse-engineered from Flutter Android APK (`app-release.apk`).

---

## 1. System Architecture

```
                    ┌────────────────────────────┐
                    │    Flutter Mobile App      │
                    │   (Dart Native Client)     │
                    └─────────────┬──────────────┘
                                  │ HTTP / JSON (Bearer JWT)
                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Reconstructed Backend Engine                         │
│                           (Port 5000)                                  │
├────────────────────────────────────────────────────────────────────────┤
│  • Auth & RBAC (/auth/login, /employee)                                │
│  • Sales & Checkout (/transactions)                                    │
│  • Inventory & Movements (/purchase, /stock-opname, /stock-history)    │
│  • CRM & Supply Chain (/customer, /supplier)                           │
│  • Store Profile & SaaS Tier (/store/profile, /subscription/plan)      │
└─────────────────────────────────┬──────────────────────────────────────┘
                                  │ Direct SQLite Operations
                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Persistent SQLite Relational Layer                   │
│                          (pos_database.db)                             │
├────────────────────────────────────────────────────────────────────────┤
│  users · store_profiles · subscriptions · categories · products ·      │
│  customers · suppliers · purchases · transactions · stock_movements    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. API Endpoint Matrix (OpenAPI 3.0)

| Endpoint | Method | Role | Description |
|---|---|---|---|
| `/auth/login` | POST | Public | Owner authentication & JWT issuance |
| `/auth/staff/login` | POST | Public | Staff/Cashier authentication |
| `/auth/change-password` | POST | Auth | Update user account password |
| `/employee` | GET, POST | Owner | Roster inspection & employee registration |
| `/customer` | GET, POST | Auth | CRM customer directory & registration |
| `/supplier` | GET, POST | Auth | Supplier directory & registration |
| `/product` | GET | Auth | Catalog inventory & live stock lookup |
| `/category` | GET | Auth | Product categories |
| `/discount` | GET | Auth | Store discount rules |
| `/additional-fee` | GET | Auth | Tax / Service charges |
| `/transactions` | GET, POST | Auth | List transactions & commit sales checkout |
| `/purchase` | GET, POST | Auth | Record vendor restock (auto-increments stock) |
| `/stock-opname` | GET, POST | Auth | Record physical audit counts and compute variance |
| `/stock-movements/history` | GET | Auth | Unified audit ledger (SALE, RESTOCK, OPNAME) |
| `/report/sales-summary` | GET | Auth | Aggregated revenue, tax, and top-selling products |
| `/store/profile` | GET, PUT | Auth | Store details & receipt branding |
| `/subscription/plan` | GET | Auth | SaaS subscription quota & active tier |

Interactive contract documentation available in [swagger_ui.html](file:///Users/user/python_project/reverse-engineer/swagger_ui.html).

---

## 3. Database Entity Relationship

- **users** (`id`, `username`, `password_hash`, `role`, `name`, `phone`, `is_active`)
- **store_profiles** (`id`, `name`, `business_type`, `address`, `phone`, `email`, `currency`, `receipt_footer`)
- **subscriptions** (`id`, `plan_name`, `status`, `expires_at`, `max_outlets`, `max_staff`, `features_json`)
- **categories** (`id`, `name`, `icon`)
- **products** (`id`, `category_id`, `name`, `barcode`, `price`, `cost`, `stock`)
- **customers** (`id`, `name`, `phone`, `email`, `address`)
- **suppliers** (`id`, `name`, `phone`, `email`, `address`)
- **purchases** (`id`, `supplier_id`, `invoice_number`, `total_cost`, `notes`)
- **purchase_items** (`id`, `purchase_id`, `product_id`, `product_name`, `quantity`, `cost_per_unit`, `subtotal`)
- **transactions** (`id`, `user_id`, `customer_id`, `subtotal`, `tax`, `discount_amount`, `fee_amount`, `total_amount`, `payment_method`, `cash_amount`, `change_amount`)
- **transaction_items** (`id`, `transaction_id`, `product_id`, `product_name`, `quantity`, `price`, `subtotal`)
- **stock_opnames** (`id`, `product_id`, `physical_count`, `system_count`, `difference`, `notes`)
- **stock_movements** (`id`, `product_id`, `movement_type`, `quantity`, `reference_id`, `notes`)

---

## 4. Quick Start & Execution

### Running the Backend Locally
```bash
/usr/bin/python3 mock_backend.py
```

### CLI Command Reference
```bash
# 1. Login
/usr/bin/python3 pos_cli.py login -u admin -p password123

# 2. View Store & Subscription
/usr/bin/python3 pos_cli.py --token <token> store-profile
/usr/bin/python3 pos_cli.py --token <token> subscription

# 3. View Inventory & Restock
/usr/bin/python3 pos_cli.py --token <token> products
/usr/bin/python3 pos_cli.py --token <token> restock --product-id 1 --qty 50 --cost 8000 --supplier-id 1

# 4. Commit a Sale
/usr/bin/python3 pos_cli.py --token <token> checkout --product-id 1 --qty 2 --price 18000 --cash 50000 --customer-id 1

# 5. Print Thermal Receipt
/usr/bin/python3 pos_cli.py --token <token> receipt --tx-id 1 --width 32

# 6. Audit Stock Movement Ledger
/usr/bin/python3 pos_cli.py --token <token> stock-history

# 7. Generate Daily Sales Summary
/usr/bin/python3 pos_cli.py --token <token> report
```

### Docker Deployment
```bash
docker compose up -d --build
```
Access backend API at `http://localhost:5000`.
