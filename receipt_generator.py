# Python 3.9+ | File: receipt_generator.py | Target: Mobile POS Thermal Receipt Formatter
"""
ESC/POS and Plaintext receipt layout generator for 58mm (32 cols) and 80mm (48 cols) thermal printers.
Supports formatting store metadata, items, tax, discounts, payments, and ESC/POS command sequences.
"""

from __future__ import annotations
from typing import Dict, Any, List


class ESCPOSCommand:
    """Standard ESC/POS thermal printer control bytes."""
    INIT = b"\x1b\x40"             # ESC @ - Initialize printer
    ALIGN_LEFT = b"\x1b\x61\x00"   # ESC a 0
    ALIGN_CENTER = b"\x1b\x61\x01" # ESC a 1
    ALIGN_RIGHT = b"\x1b\x61\x02"  # ESC a 2
    BOLD_ON = b"\x1b\x45\x01"      # ESC E 1
    BOLD_OFF = b"\x1b\x45\x00"     # ESC E 0
    FEED_CUT = b"\x1d\x56\x41\x03" # GS V A 3 - Feed and partial cut


class ReceiptFormatter:
    def __init__(self, width: int = 32):  # Default 32 chars for 58mm paper (standard mobile POS)
        self.width = width

    def _divider(self, char: str = "-") -> str:
        return char * self.width

    def _two_col(self, left: str, right: str) -> str:
        space = self.width - len(left) - len(right)
        if space < 1:
            space = 1
        return f"{left}{' ' * space}{right}"

    def format_text(self, store: Dict[str, Any], transaction: Dict[str, Any]) -> str:
        lines: List[str] = []

        # Header / Branding
        store_name = store.get("name", "KASERA POS").upper()
        lines.append(store_name.center(self.width))
        if store.get("address"):
            lines.append(store["address"][:self.width].center(self.width))
        if store.get("phone"):
            lines.append(f"Telp: {store['phone']}".center(self.width))

        lines.append(self._divider("="))

        # Metadata
        tx_id = transaction.get("id") or transaction.get("transaction_id", "N/A")
        lines.append(self._two_col(f"Order: #{tx_id}", transaction.get("created_at", "")[:16]))
        if transaction.get("customer_name"):
            lines.append(f"Pelanggan: {transaction['customer_name'][:self.width - 11]}")

        lines.append(self._divider("-"))

        # Items
        items = transaction.get("items", [])
        for item in items:
            name = item.get("product_name") or item.get("name", "Item")
            qty = item.get("quantity", 1)
            price = float(item.get("price", 0))
            subtotal = float(item.get("subtotal", qty * price))

            lines.append(name[:self.width])
            lines.append(self._two_col(f"  {qty} x {price:,.0f}", f"{subtotal:,.0f}"))

        lines.append(self._divider("-"))

        # Totals
        subtotal = float(transaction.get("subtotal", 0))
        tax = float(transaction.get("tax", 0))
        discount = float(transaction.get("discount_amount", 0))
        fee = float(transaction.get("fee_amount", 0))
        total = float(transaction.get("total_amount", (subtotal + tax + fee) - discount))

        lines.append(self._two_col("Subtotal:", f"{subtotal:,.0f}"))
        if tax > 0:
            lines.append(self._two_col("Pajak (PB1 10%):", f"{tax:,.0f}"))
        if discount > 0:
            lines.append(self._two_col("Diskon:", f"-{discount:,.0f}"))
        if fee > 0:
            lines.append(self._two_col("Biaya Lain:", f"{fee:,.0f}"))

        lines.append(self._divider("="))
        lines.append(self._two_col("TOTAL:", f"IDR {total:,.0f}"))
        lines.append(self._divider("-"))

        # Payment details
        pay_method = transaction.get("payment_method", "CASH")
        cash = float(transaction.get("cash_amount", total))
        change = float(transaction.get("change_amount", 0))

        lines.append(self._two_col(f"Bayar ({pay_method}):", f"{cash:,.0f}"))
        if pay_method == "CASH":
            lines.append(self._two_col("Kembali:", f"{change:,.0f}"))

        # Footer
        lines.append(self._divider("="))
        footer = store.get("receipt_footer", "Terima kasih atas kunjungan Anda!")
        lines.append(footer[:self.width].center(self.width))
        lines.append("Powered by Kasera POS".center(self.width))

        return "\n".join(lines) + "\n"

    def format_escpos(self, store: Dict[str, Any], transaction: Dict[str, Any]) -> bytes:
        """Converts receipt to raw ESC/POS binary stream for thermal printer delivery."""
        text = self.format_text(store, transaction)
        stream = bytearray()
        stream.extend(ESCPOSCommand.INIT)
        stream.extend(text.encode("latin-1", errors="replace"))
        stream.extend(ESCPOSCommand.FEED_CUT)
        return bytes(stream)


if __name__ == "__main__":
    formatter = ReceiptFormatter(width=32)
    sample_store = {
        "name": "Kasera Coffee & Bakery",
        "address": "Jl. Thamrin No. 8, Jakarta Pusat",
        "phone": "021-2345678",
        "receipt_footer": "Simpan struk sebagai bukti pembayaran"
    }
    sample_tx = {
        "id": 1042,
        "created_at": "2026-11-13 11:20:00",
        "customer_name": "Budi Santoso",
        "items": [
            {"product_name": "Espresso Single", "quantity": 2, "price": 18000, "subtotal": 36000},
            {"product_name": "Butter Croissant", "quantity": 1, "price": 22000, "subtotal": 22000}
        ],
        "subtotal": 58000,
        "tax": 5800,
        "discount_amount": 0,
        "fee_amount": 0,
        "total_amount": 63800,
        "payment_method": "CASH",
        "cash_amount": 100000,
        "change_amount": 36200
    }
    print(formatter.format_text(sample_store, sample_tx))
