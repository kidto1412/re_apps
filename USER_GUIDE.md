# Kasera Mobile POS — Complete Operator & User Guide

Step-by-step documentation for running, interacting with, and testing the reconstructed Mobile POS stack.

---

## Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Workflow 1: Local Backend & Interactive API Docs](#2-workflow-1-local-backend--interactive-api-docs)
3. [Workflow 2: Terminal Operations (CLI)](#3-workflow-2-terminal-operations-cli)
   - [Authentication & Session Tokens](#a-authentication--session-tokens)
   - [Store Profile & Quotas](#b-store-profile--quotas)
   - [Product Catalog & Live Inventory](#c-product-catalog--live-inventory)
   - [Vendor Restocking (Purchases)](#d-vendor-restocking-purchases)
   - [Sales Checkout & Customer Binding](#e-sales-checkout--customer-binding)
   - [Thermal Receipt Printing](#f-thermal-receipt-printing)
   - [Physical Stock Opname (Audits)](#g-physical-stock-opname-audits)
   - [Unified Stock Audit Ledger](#h-unified-stock-audit-ledger)
   - [Sales Summary & Analytics](#i-sales-summary--analytics)
   - [Staff & Employee Management](#j-staff--employee-management)
4. [Workflow 3: Python Client SDK Integration](#4-workflow-3-python-client-sdk-integration)
5. [Workflow 4: Docker Container Deployment](#5-workflow-4-docker-container-deployment)
6. [Workflow 5: Live App Traffic Interception (Frida)](#6-workflow-5-live-app-traffic-interception-frida)
7. [Default Seed Credentials](#7-default-seed-credentials)

---

## 1. Prerequisites

- macOS / Linux with Python 3.9+ installed.
- No external Python libraries required (`urllib`, `sqlite3`, `json`, `hashlib` all use standard library).
- (Optional) Docker / Docker Compose for containerized execution.
- (Optional) Android device/emulator + `adb` + `frida-tools` for live APK traffic interception.

---

## 2. Workflow 1: Local Backend & Interactive API Docs

### Step 1: Start the Persistent Backend
Run the backend server in a terminal window:
```bash
cd /Users/user/python_project/reverse-engineer
/usr/bin/python3 mock_backend.py
```
* The server starts listening on `http://127.0.0.1:5000`.
* Database state is persisted automatically into `pos_database.db`.

### Step 2: Open Interactive API Documentation (Swagger UI)
In a second terminal window:
```bash
cd /Users/user/python_project/reverse-engineer
/usr/bin/python3 -m http.server 8080
```
Open your browser and navigate to:
```
http://localhost:8080/swagger_ui.html
```
You can view, search, and test all 17 reverse-engineered endpoints.

---

## 3. Workflow 2: Terminal Operations (CLI)

Use `pos_cli.py` to perform all store operations directly from your terminal.

### a. Authentication & Session Tokens
Login as the store owner to obtain a Bearer token:
```bash
/usr/bin/python3 pos_cli.py login -u admin -p password123
```
Export the token to your environment for subsequent commands:
```bash
export TOKEN="token-owner-admin"
```

To login as a staff/cashier member:
```bash
/usr/bin/python3 pos_cli.py login -u cashier1 -p password123 --staff
```

### b. Store Profile & Quotas
Inspect store branding details and SaaS tier:
```bash
/usr/bin/python3 pos_cli.py --token $TOKEN store-profile
/usr/bin/python3 pos_cli.py --token $TOKEN subscription
```

Update store profile metadata:
```bash
/usr/bin/python3 pos_cli.py --token $TOKEN update-store \
  --name "Kasera Specialty Coffee" \
  --type "Coffee & Eatery" \
  --address "Jl. Thamrin No. 8, Jakarta" \
  --phone "021-99887766" \
  --email "contact@kasera.id" \
  --footer "Terima kasih atas kunjungan Anda!"
```

### c. Product Catalog & Live Inventory
List all products, categories, active discounts, and fees:
```bash
/usr/bin/python3 pos_cli.py --token $TOKEN products
/usr/bin/python3 pos_cli.py --token $TOKEN categories
/usr/bin/python3 pos_cli.py --token $TOKEN discounts
/usr/bin/python3 pos_cli.py --token $TOKEN fees
```

### d. Vendor Restocking (Purchases)
List registered suppliers:
```bash
/usr/bin/python3 pos_cli.py --token $TOKEN suppliers
```

Register a new supplier:
```bash
/usr/bin/python3 pos_cli.py --token $TOKEN add-supplier \
  --name "CV Roastery Mandiri" \
  --phone "021-554433" \
  --email "order@roastery.id" \
  --address "Bandung, Jawa Barat"
```

Commit a vendor restock purchase order (automatically increments product stock):
```bash
/usr/bin/python3 pos_cli.py --token $TOKEN restock \
  --product-id 1 \
  --qty 50 \
  --cost 8000 \
  --supplier-id 1 \
  --invoice "INV-RESTOCK-001" \
  --notes "Restock Espresso Beans Grade A"
```

View restock purchase history:
```bash
/usr/bin/python3 pos_cli.py --token $TOKEN purchases
```

### e. Sales Checkout & Customer Binding
List registered CRM customers:
```bash
/usr/bin/python3 pos_cli.py --token $TOKEN customers
```

Register a new customer:
```bash
/usr/bin/python3 pos_cli.py --token $TOKEN add-customer \
  --name "Alice Kusuma" \
  --phone "081233445566" \
  --email "alice@pos.local" \
  --address "Jakarta Selatan"
```

Commit a sales transaction (automatically computes 10% tax, deducts inventory, and logs ledger):
```bash
/usr/bin/python3 pos_cli.py --token $TOKEN checkout \
  --product-id 1 \
  --name "Espresso Single" \
  --qty 2 \
  --price 18000 \
  --cash 50000 \
  --customer-id 1
```

View transaction history:
```bash
/usr/bin/python3 pos_cli.py --token $TOKEN transactions
```

### f. Thermal Receipt Printing
Render an ESC/POS 58mm (32-column) or 80mm (48-column) receipt for any transaction:
```bash
# 58mm standard mobile POS receipt
/usr/bin/python3 pos_cli.py --token $TOKEN receipt --tx-id 1 --width 32

# 80mm wide desk printer receipt
/usr/bin/python3 pos_cli.py --token $TOKEN receipt --tx-id 1 --width 48
```

### g. Physical Stock Opname (Audits)
Record a physical inventory count and calculate variance against system counts:
```bash
/usr/bin/python3 pos_cli.py --token $TOKEN opname \
  --product-id 1 \
  --count 48 \
  --notes "Shift 1 Audit Count"
```

View past stock opname audit history:
```bash
/usr/bin/python3 pos_cli.py --token $TOKEN opname-history
```

### h. Unified Stock Audit Ledger
Inspect chronological audit deltas (`SALE`, `RESTOCK`, `OPNAME_ADJUST`):
```bash
# All movements across the store
/usr/bin/python3 pos_cli.py --token $TOKEN stock-history

# Filter movements for Product ID 1
/usr/bin/python3 pos_cli.py --token $TOKEN stock-history --product-id 1
```

### i. Sales Summary & Analytics
View real-time gross revenue, tax collected, total orders, and top-performing products:
```bash
/usr/bin/python3 pos_cli.py --token $TOKEN report
```

### j. Staff & Employee Management
List all employees and active roles:
```bash
/usr/bin/python3 pos_cli.py --token $TOKEN employees
```

Register a new staff/cashier member (Owner only):
```bash
/usr/bin/python3 pos_cli.py --token $TOKEN add-employee \
  -u siti \
  -p secret123 \
  -n "Siti Rahma" \
  --phone "081987654321" \
  --role staff
```

Change password for current account:
```bash
/usr/bin/python3 pos_cli.py --token $TOKEN change-password \
  --old password123 \
  --new myNewSecurePassword456
```

---

## 4. Workflow 3: Python Client SDK Integration

Use `mobile_pos_client.py` directly in custom Python scripts or automation workflows:

```python
from mobile_pos_client import MobilePOSClient, TransactionItem, CreateTransactionRequest

# Initialize client
client = MobilePOSClient(base_url="http://127.0.0.1:5000")

# 1. Login
auth = client.login_owner("admin", "password123")
print("Logged in as:", auth["data"]["role"])

# 2. Query products
products = client.list_products()
print("Total products:", len(products["data"]))

# 3. Create a transaction
tx_req = CreateTransactionRequest(
    items=[
        TransactionItem(productId=1, productName="Espresso Single", quantity=1, price=18000, subtotal=18000)
    ],
    subtotal=18000,
    tax=1800,
    payment_method="CASH",
    cash_amount=20000,
    change_amount=200
)
res = client.create_transaction(tx_req)
print("Transaction ID:", res["data"]["transaction_id"])
```

---

## 5. Workflow 4: Docker Container Deployment

To run the entire backend and SQLite database inside a production-ready Docker container:

```bash
# Build and start container in background
docker compose up -d --build

# Inspect container status and health
docker compose ps

# View backend logs
docker compose logs -f

# Stop container
docker compose down
```
* The API will be available at `http://localhost:5000`.
* Database data is preserved across container restarts in the `pos_data` Docker volume.

---

## 6. Workflow 5: Live App Traffic Interception (Frida)

To capture live HTTP/HTTPS traffic between `app-release.apk` and its remote host (`http://43.157.205.66:5000`) using Burp Suite or Charles:

1. **Install APK on Android Device/Emulator**:
   ```bash
   adb install app-release.apk
   ```
2. **Configure Wi-Fi Proxy on Android**:
   - Set HTTP Proxy to your machine's IP (e.g., `192.168.1.50:8080`).
   - Install your Burp Suite CA Certificate on the Android device.
3. **Launch the Application with Frida**:
   ```bash
   frida -U -f com.kasircuy.app -l flutter_ssl_pinning_bypass.js --no-pause
   ```
   * The script automatically hooks `session_verify_cert_chain` in `libflutter.so`, forcing TLS verification success and allowing full interception in Burp Suite.

---

## 7. Default Seed Credentials

| Account Role | Username | Default Password | Permissions |
|---|---|---|---|
| **Store Owner** | `admin` | `password123` | Full access (Staff, Store Profile, Reports, Catalog, Inventory) |
| **Cashier / Staff** | `cashier1` | `password123` | Operational access (Checkout, Catalog, Stock Opname) |
