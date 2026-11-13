# Python 3.9+ | File: mock_backend.py | Target: Mobile POS Reconstructed Backend Mock
"""
Persistent mock server implementing the reconstructed Mobile POS REST API.
Backed by SQLite (schema_sqlite.py).
Run with: /usr/bin/python3 mock_backend.py
Default port: 5000
"""

from __future__ import annotations
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sqlite3
import time
from typing import Dict, Any, Optional, List
from schema_sqlite import Database

HOST = "127.0.0.1"
PORT = 5000

# Shared DB instance
db = Database("pos_database.db")
db.seed_defaults()

# Active in-memory session tokens mapping to user roles
ACTIVE_TOKENS: Dict[str, Dict[str, Any]] = {
    "mock-owner-token": {"user_id": 1, "username": "admin", "role": "owner"},
    "mock-staff-token": {"user_id": 2, "username": "staff1", "role": "staff"}
}


class MockPOSHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, data: Dict[str, Any]):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Dict[str, Any]:
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len == 0:
            return {}
        try:
            return json.loads(self.rfile.read(content_len).decode("utf-8"))
        except Exception:
            return {}

    def _get_auth_token(self) -> Optional[str]:
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        return None

    def _verify_auth(self) -> Optional[Dict[str, Any]]:
        token = self._get_auth_token()
        if not token:
            return None
        return ACTIVE_TOKENS.get(token)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.end_headers()

    def do_PUT(self):
        return self.do_POST()

    def do_GET(self):
        path = self.path.split("?")[0]

        protected_paths = [
            "/transactions", "/product", "/category", "/stock-opname",
            "/discount", "/additional-fee", "/report/sales-summary",
            "/customer", "/supplier", "/purchase", "/stock-movements/history", "/stock-history",
            "/employee", "/auth/change-password", "/store/profile", "/subscription/plan"
        ]

        if path in protected_paths:
            if not self._verify_auth():
                self._send_json(401, {"status": False, "message": "Unauthorized / Token tidak valid"})
                return

        if path == "/product":
            products = db.list_products()
            self._send_json(200, {"status": True, "data": products})

        elif path == "/category":
            categories = db.list_categories()
            self._send_json(200, {"status": True, "data": categories})

        elif path == "/discount":
            discounts = db.list_discounts()
            self._send_json(200, {"status": True, "data": discounts})

        elif path == "/additional-fee":
            fees = db.list_additional_fees()
            self._send_json(200, {"status": True, "data": fees})

        elif path == "/report/sales-summary":
            summary = db.get_sales_summary()
            self._send_json(200, {"status": True, "data": summary})

        elif path == "/customer":
            customers = db.list_customers()
            self._send_json(200, {"status": True, "data": customers})

        elif path == "/supplier":
            suppliers = db.list_suppliers()
            self._send_json(200, {"status": True, "data": suppliers})

        elif path == "/employee":
            employees = db.list_employees()
            self._send_json(200, {"status": True, "data": employees})

        elif path == "/store/profile":
            profile = db.get_store_profile()
            self._send_json(200, {"status": True, "data": profile})

        elif path == "/subscription/plan":
            sub = db.get_subscription()
            self._send_json(200, {"status": True, "data": sub})

        elif path == "/purchase":
            purchases = db.list_purchases()
            self._send_json(200, {"status": True, "data": purchases})

        elif path in ["/stock-movements/history", "/stock-history"]:
            # Check query params for product_id filter
            prod_id = None
            if "?" in self.path:
                query_str = self.path.split("?", 1)[1]
                for part in query_str.split("&"):
                    if part.startswith("product_id="):
                        try:
                            prod_id = int(part.split("=")[1])
                        except ValueError:
                            pass
            movements = db.list_stock_movements(product_id=prod_id)
            self._send_json(200, {"status": True, "data": movements})

        elif path == "/transactions":
            cur = db.conn.cursor()
            cur.execute("""
                SELECT t.id, t.user_id, t.customer_id, c.name as customer_name, t.subtotal, t.tax, 
                       t.discount_amount, t.fee_amount, t.total_amount, t.payment_method, 
                       t.cash_amount, t.change_amount, t.created_at
                FROM transactions t
                LEFT JOIN customers c ON t.customer_id = c.id
                ORDER BY t.id DESC
            """)
            transactions = [dict(row) for row in cur.fetchall()]
            for tx in transactions:
                cur.execute("""
                    SELECT product_id, product_name, quantity, price, subtotal
                    FROM transaction_items WHERE transaction_id = ?
                """, (tx["id"],))
                tx["items"] = [dict(item) for item in cur.fetchall()]
            self._send_json(200, {"status": True, "data": transactions})

        elif path == "/stock-opname":
            cur = db.conn.cursor()
            cur.execute("""
                SELECT s.id, s.product_id, p.name as product_name, s.physical_count, s.system_count, s.difference, s.notes, s.created_at
                FROM stock_opnames s
                JOIN products p ON s.product_id = p.id
                ORDER BY s.id DESC
            """)
            records = [dict(row) for row in cur.fetchall()]
            self._send_json(200, {"status": True, "data": records})

        else:
            self._send_json(404, {"status": False, "message": f"Route {path} not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        body = self._read_json()

        if path == "/auth/login":
            username = body.get("username")
            password = body.get("password")
            if not username or not password:
                self._send_json(400, {"status": False, "message": "Username dan password harus diisi"})
                return

            user = db.authenticate_user(username, password)
            if user:
                token = f"token-{user['role']}-{username}"
                ACTIVE_TOKENS[token] = {"user_id": user["id"], "username": username, "role": user["role"]}
                self._send_json(200, {
                    "status": True,
                    "message": "Login berhasil",
                    "token": token,
                    "data": user
                })
            else:
                self._send_json(401, {"status": False, "message": "Username atau password salah"})

        elif path == "/auth/staff/login":
            username = body.get("username")
            password = body.get("password")
            if not username or not password:
                self._send_json(400, {"status": False, "message": "Username dan password harus diisi"})
                return

            user = db.authenticate_user(username, password)
            if user and user["role"] in ["staff", "cashier"]:
                token = f"token-staff-{username}"
                ACTIVE_TOKENS[token] = {"user_id": user["id"], "username": username, "role": user["role"]}
                self._send_json(200, {
                    "status": True,
                    "message": "Login staff berhasil",
                    "token": token,
                    "data": user
                })
            else:
                self._send_json(401, {"status": False, "message": "Username atau password staff salah"})

        elif path == "/auth/change-password":
            user = self._verify_auth()
            if not user:
                self._send_json(401, {"status": False, "message": "Unauthorized / Token tidak valid"})
                return

            old_pass = body.get("old_password")
            new_pass = body.get("new_password")
            if not old_pass or not new_pass:
                self._send_json(400, {"status": False, "message": "Password lama dan baru harus diisi"})
                return

            ok = db.change_password(user["user_id"], old_pass, new_pass)
            if ok:
                self._send_json(200, {"status": True, "message": "Password berhasil diubah"})
            else:
                self._send_json(400, {"status": False, "message": "Password lama tidak sesuai"})

        elif path == "/employee":
            user = self._verify_auth()
            if not user:
                self._send_json(401, {"status": False, "message": "Unauthorized / Token tidak valid"})
                return
            if user.get("role") != "owner":
                self._send_json(403, {"status": False, "message": "Hanya owner yang dapat menambah karyawan"})
                return

            username = body.get("username")
            password = body.get("password")
            name = body.get("name")
            phone = body.get("phone")
            role = body.get("role", "staff")

            if not username or not password or not name:
                self._send_json(400, {"status": False, "message": "Username, password, dan nama wajib diisi saat tambah karyawan"})
                return

            try:
                emp_id = db.create_employee(username=username, password=password, name=name, phone=phone, role=role)
                self._send_json(200, {
                    "status": True,
                    "message": "Karyawan berhasil didaftarkan",
                    "data": {"id": emp_id, "username": username, "name": name, "role": role}
                })
            except Exception as e:
                self._send_json(400, {"status": False, "message": f"Gagal menambah karyawan: {str(e)}"})

        elif path == "/store/profile":
            user = self._verify_auth()
            if not user or user.get("role") != "owner":
                self._send_json(403, {"status": False, "message": "Hanya owner yang dapat mengubah profil toko"})
                return

            profile = db.update_store_profile(
                name=body.get("name", "Kasera Coffee"),
                business_type=body.get("business_type", "F&B"),
                address=body.get("address", ""),
                phone=body.get("phone", ""),
                email=body.get("email", ""),
                receipt_footer=body.get("receipt_footer", "")
            )
            self._send_json(200, {"status": True, "message": "Profil toko berhasil diperbarui", "data": profile})

        elif path == "/transactions":
            user = self._verify_auth()
            if not user:
                self._send_json(401, {"status": False, "message": "Unauthorized / Token tidak valid"})
                return

            items = body.get("items", [])
            subtotal = float(body.get("subtotal", 0.0))
            tax = float(body.get("tax", 0.0))
            discount = float(body.get("discount_amount", 0.0))
            fee = float(body.get("fee_amount", 0.0))
            total = float(body.get("total_amount", (subtotal + tax + fee) - discount))
            payment_method = str(body.get("payment_method", "CASH"))
            cash_amount = float(body.get("cash_amount", 0.0))
            change_amount = float(body.get("change_amount", 0.0))
            customer_id = body.get("customer_id")
            if customer_id is not None:
                customer_id = int(customer_id)

            tx_id = db.record_transaction(
                subtotal=subtotal,
                tax=tax,
                discount_amount=discount,
                fee_amount=fee,
                total_amount=total,
                payment_method=payment_method,
                cash_amount=cash_amount,
                change_amount=change_amount,
                items=items,
                user_id=user["user_id"],
                customer_id=customer_id
            )

            self._send_json(200, {
                "status": True,
                "message": "Transaksi berhasil disimpan",
                "data": {"transaction_id": tx_id, "customer_id": customer_id, "total_amount": total, "status": "COMPLETED"}
            })

        elif path == "/customer":
            user = self._verify_auth()
            if not user:
                self._send_json(401, {"status": False, "message": "Unauthorized / Token tidak valid"})
                return

            name = body.get("name")
            if not name:
                self._send_json(400, {"status": False, "message": "Nama customer wajib diisi"})
                return

            phone = body.get("phone")
            email = body.get("email")
            address = body.get("address")
            cust_id = db.create_customer(name=name, phone=phone, email=email, address=address)
            self._send_json(200, {
                "status": True,
                "message": "Customer berhasil didaftarkan",
                "data": {"id": cust_id, "name": name, "phone": phone, "email": email}
            })

        elif path == "/supplier":
            user = self._verify_auth()
            if not user:
                self._send_json(401, {"status": False, "message": "Unauthorized / Token tidak valid"})
                return

            name = body.get("name")
            if not name:
                self._send_json(400, {"status": False, "message": "Nama supplier wajib diisi"})
                return

            phone = body.get("phone")
            email = body.get("email")
            address = body.get("address")
            supp_id = db.create_supplier(name=name, phone=phone, email=email, address=address)
            self._send_json(200, {
                "status": True,
                "message": "Supplier berhasil didaftarkan",
                "data": {"id": supp_id, "name": name, "phone": phone, "email": email}
            })

        elif path == "/purchase":
            user = self._verify_auth()
            if not user:
                self._send_json(401, {"status": False, "message": "Unauthorized / Token tidak valid"})
                return

            items = body.get("items", [])
            if not items:
                self._send_json(400, {"status": False, "message": "Item pembelian tidak boleh kosong"})
                return

            supplier_id = body.get("supplier_id")
            invoice_number = body.get("invoice_number", f"INV-{int(time.time())}")
            notes = body.get("notes", "")

            try:
                purchase_id = db.record_purchase(
                    supplier_id=supplier_id,
                    invoice_number=invoice_number,
                    notes=notes,
                    items=items
                )
                self._send_json(200, {
                    "status": True,
                    "message": "Pembelian berhasil dicatat dan stok bertambah",
                    "data": {"purchase_id": purchase_id, "invoice_number": invoice_number}
                })
            except Exception as e:
                self._send_json(400, {"status": False, "message": str(e)})

        elif path == "/stock-opname":
            user = self._verify_auth()
            if not user:
                self._send_json(401, {"status": False, "message": "Unauthorized / Token tidak valid"})
                return

            try:
                product_id = int(body["product_id"])
                physical_count = int(body["physical_count"])
                notes = str(body.get("notes", ""))
                res = db.perform_stock_opname(product_id, physical_count, notes)
                self._send_json(200, {
                    "status": True,
                    "message": "Stock opname berhasil dicatat",
                    "data": res
                })
            except Exception as e:
                self._send_json(400, {"status": False, "message": str(e)})

        else:
            self._send_json(404, {"status": False, "message": f"Route {path} not found"})


def run():
    server = HTTPServer((HOST, PORT), MockPOSHandler)
    print(f"[*] Persistent Mock Backend running at http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down server.")
        server.server_close()


if __name__ == "__main__":
    run()
