# Python 3.9+ | File: mobile_pos_client.py | Target: Mobile POS API Backend
"""
Zero-dependency typed client SDK reconstructed from Mobile POS API contracts.
Base URL: http://43.157.205.66:5000
Uses standard library `urllib.request` for universal compatibility.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any, Union
import urllib.request
import urllib.error
import urllib.parse
import json


class APIError(Exception):
    """Raised when an API endpoint returns an error or non-200 response."""
    def __init__(self, status_code: int, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(f"API Error {status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.payload = payload or {}


@dataclass
class TransactionItem:
    productId: int
    productName: str
    quantity: int
    price: float
    subtotal: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CreateTransactionRequest:
    items: List[TransactionItem]
    subtotal: float
    tax: float
    payment_method: str = "CASH"
    cash_amount: float = 0.0
    change_amount: float = 0.0
    discount_id: Optional[int] = None
    additional_fee_id: Optional[int] = None
    customer_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["items"] = [item.to_dict() if isinstance(item, TransactionItem) else item for item in self.items]
        return data


class MobilePOSClient:
    """Synchronous HTTP client for Mobile POS API endpoints using urllib."""

    def __init__(self, base_url: str = "http://43.157.205.66:5000", token: Optional[str] = None, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "MobilePOS/1.0.0 (Dart/Flutter)"
        }
        if token:
            self.set_token(token)

    def set_token(self, token: str) -> None:
        """Sets the Bearer token for authenticated requests."""
        self.headers["Authorization"] = f"Bearer {token}"

    def clear_token(self) -> None:
        """Clears authorization headers."""
        self.headers.pop("Authorization", None)

    def _request(self, method: str, path: str, json_body: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if params:
            query = urllib.parse.urlencode({k: str(v) for k, v in params.items() if v is not None})
            url = f"{url}?{query}"

        data_bytes = None
        if json_body is not None:
            data_bytes = json.dumps(json_body).encode("utf-8")

        req = urllib.request.Request(url, data=data_bytes, headers=self.headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                try:
                    return json.loads(body)
                except ValueError:
                    return {"raw": body}
        except urllib.error.HTTPError as e:
            raw_err = e.read().decode("utf-8", errors="replace")
            try:
                err_data = json.loads(raw_err)
                msg = err_data.get("message", raw_err)
            except ValueError:
                err_data = {"raw": raw_err}
                msg = raw_err
            raise APIError(e.code, msg, err_data) from e
        except urllib.error.URLError as e:
            raise APIError(0, f"Transport failure: {e.reason}") from e

    # ---------------- Auth Endpoints ---------------- #

    def login_owner(self, username: str, password: str) -> Dict[str, Any]:
        """POST /auth/login - Authenticate store owner."""
        payload = {"username": username, "password": password}
        res = self._request("POST", "/auth/login", json_body=payload)
        token = res.get("token") or (res.get("data") or {}).get("token")
        if token:
            self.set_token(token)
        return res

    def login_staff(self, username: str, password: str) -> Dict[str, Any]:
        """POST /auth/staff/login - Authenticate staff user."""
        payload = {"username": username, "password": password}
        res = self._request("POST", "/auth/staff/login", json_body=payload)
        token = res.get("token") or (res.get("data") or {}).get("token")
        if token:
            self.set_token(token)
        return res

    def change_password(self, old_password: str, new_password: str) -> Dict[str, Any]:
        """POST /auth/change-password - Change current user's password."""
        payload = {"old_password": old_password, "new_password": new_password}
        return self._request("POST", "/auth/change-password", json_body=payload)

    # ---------------- Transaction Endpoints ---------------- #

    def list_transactions(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET /transactions - Retrieve transaction history."""
        return self._request("GET", "/transactions", params=params)

    def create_transaction(self, request_data: Union[CreateTransactionRequest, Dict[str, Any]]) -> Dict[str, Any]:
        """POST /transactions - Commit a new POS transaction."""
        body = request_data.to_dict() if isinstance(request_data, CreateTransactionRequest) else request_data
        return self._request("POST", "/transactions", json_body=body)

    # ---------------- Catalog & Inventory Endpoints ---------------- #

    def list_products(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET /product - Fetch product inventory list."""
        return self._request("GET", "/product", params=params)

    def list_categories(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET /category - Fetch catalog categories."""
        return self._request("GET", "/category", params=params)

    # ---------------- Customer CRM Endpoints ---------------- #

    def list_customers(self) -> Dict[str, Any]:
        """GET /customer - Fetch registered customers."""
        return self._request("GET", "/customer")

    def create_customer(self, name: str, phone: Optional[str] = None, email: Optional[str] = None, address: Optional[str] = None) -> Dict[str, Any]:
        """POST /customer - Register a new customer."""
        payload = {"name": name, "phone": phone, "email": email, "address": address}
        return self._request("POST", "/customer", json_body=payload)

    # ---------------- Employee / Staff Endpoints ---------------- #

    def list_employees(self) -> Dict[str, Any]:
        """GET /employee - Fetch list of employees and cashiers."""
        return self._request("GET", "/employee")

    def create_employee(self, username: str, password: str, name: str, phone: Optional[str] = None, role: str = "staff") -> Dict[str, Any]:
        """POST /employee - Register a new employee/cashier (Owner only)."""
        payload = {"username": username, "password": password, "name": name, "phone": phone, "role": role}
        return self._request("POST", "/employee", json_body=payload)

    # ---------------- Store Profile & SaaS Subscription ---------------- #

    def get_store_profile(self) -> Dict[str, Any]:
        """GET /store/profile - Fetch business details and receipt branding."""
        return self._request("GET", "/store/profile")

    def update_store_profile(self, name: str, business_type: str, address: str = "", phone: str = "", email: str = "", receipt_footer: str = "") -> Dict[str, Any]:
        """POST /store/profile - Update store branding and information."""
        payload = {
            "name": name,
            "business_type": business_type,
            "address": address,
            "phone": phone,
            "email": email,
            "receipt_footer": receipt_footer
        }
        return self._request("POST", "/store/profile", json_body=payload)

    def get_subscription_plan(self) -> Dict[str, Any]:
        """GET /subscription/plan - Fetch current SaaS tier and quota limits."""
        return self._request("GET", "/subscription/plan")

    # ---------------- Supplier & Purchasing Endpoints ---------------- #

    def list_suppliers(self) -> Dict[str, Any]:
        """GET /supplier - Fetch list of suppliers."""
        return self._request("GET", "/supplier")

    def create_supplier(self, name: str, phone: Optional[str] = None, email: Optional[str] = None, address: Optional[str] = None) -> Dict[str, Any]:
        """POST /supplier - Register a new supplier."""
        payload = {"name": name, "phone": phone, "email": email, "address": address}
        return self._request("POST", "/supplier", json_body=payload)

    def list_purchases(self) -> Dict[str, Any]:
        """GET /purchase - Fetch vendor restock history."""
        return self._request("GET", "/purchase")

    def create_purchase(self, items: List[Dict[str, Any]], supplier_id: Optional[int] = None, invoice_number: Optional[str] = None, notes: str = "") -> Dict[str, Any]:
        """POST /purchase - Commit vendor purchase and auto-increment product inventory."""
        payload: Dict[str, Any] = {"items": items, "supplier_id": supplier_id, "notes": notes}
        if invoice_number:
            payload["invoice_number"] = invoice_number
        return self._request("POST", "/purchase", json_body=payload)

    def list_discounts(self) -> Dict[str, Any]:
        """GET /discount - Fetch active store discounts."""
        return self._request("GET", "/discount")

    def list_additional_fees(self) -> Dict[str, Any]:
        """GET /additional-fee - Fetch active store surcharges."""
        return self._request("GET", "/additional-fee")

    def list_stock_opname(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET /stock-opname - Retrieve stock opname audit logs."""
        return self._request("GET", "/stock-opname", params=params)

    def list_stock_movements(self, product_id: Optional[int] = None) -> Dict[str, Any]:
        """GET /stock-movements/history - Retrieve unified stock audit movements."""
        params = {"product_id": product_id} if product_id is not None else None
        return self._request("GET", "/stock-movements/history", params=params)

    def create_stock_opname(self, product_id: int, physical_count: int, notes: str = "") -> Dict[str, Any]:
        """POST /stock-opname - Commit physical stock adjustment."""
        payload = {"product_id": product_id, "physical_count": physical_count, "notes": notes}
        return self._request("POST", "/stock-opname", json_body=payload)

    def get_sales_summary(self) -> Dict[str, Any]:
        """GET /report/sales-summary - Aggregate sales metrics & top performers."""
        return self._request("GET", "/report/sales-summary")


if __name__ == "__main__":
    client = MobilePOSClient(base_url="http://127.0.0.1:5000")
    print(f"Initialized client pointing to {client.base_url}")
