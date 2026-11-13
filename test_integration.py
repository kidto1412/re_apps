# Python 3.10+ | File: test_integration.py | Target: Mobile POS Client & Mock Backend Integration
"""
Self-contained integration test validating the client against the mock backend.
Spins up the mock server in a background thread, executes test sequences, and shuts down cleanly.
"""

import threading
import time
from http.server import HTTPServer
from mock_backend import MockPOSHandler
from mobile_pos_client import MobilePOSClient, TransactionItem, CreateTransactionRequest, APIError

TEST_PORT = 5055
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"


def start_test_server():
    server = HTTPServer(("127.0.0.1", TEST_PORT), MockPOSHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    return server


def run_tests():
    server = start_test_server()
    time.sleep(0.1)  # Allow socket to bind

    print("[1] Initializing client...")
    client = MobilePOSClient(base_url=BASE_URL)

    print("[2] Testing unauthenticated access to protected route...")
    try:
        client.list_products()
        assert False, "Should have thrown APIError 401"
    except APIError as e:
        print(f"    Expected rejection: {e.status_code} - {e.message}")
        assert e.status_code == 401

    print("[3] Testing login (/auth/login)...")
    login_resp = client.login_owner("admin", "secret123")
    print(f"    Login status: {login_resp.get('status')}, Token acquired: {login_resp.get('token')}")
    assert login_resp.get("token") == "mock-owner-token"

    print("[4] Testing authorized fetch (/product)...")
    products = client.list_products()
    print(f"    Fetched {len(products.get('data', []))} products.")
    assert len(products.get("data", [])) > 0

    print("[5] Testing authorized fetch (/category)...")
    categories = client.list_categories()
    print(f"    Fetched {len(categories.get('data', []))} categories.")
    assert len(categories.get("data", [])) > 0

    print("[6] Testing transaction creation (/transactions)...")
    req = CreateTransactionRequest(
        items=[
            TransactionItem(productId=1, productName="Espresso Single", quantity=2, price=18000, subtotal=36000)
        ],
        subtotal=36000,
        tax=3600,
        payment_method="CASH",
        cash_amount=50000,
        change_amount=10400
    )
    tx_resp = client.create_transaction(req)
    print(f"    Transaction status: {tx_resp.get('status')}, Record ID: {tx_resp.get('data', {}).get('id')}")
    assert tx_resp.get("status") is True

    print("[7] Testing transaction listing (/transactions)...")
    tx_list = client.list_transactions()
    records = tx_list.get("data", [])
    print(f"    Total recorded transactions: {len(records)}")
    assert len(records) == 1

    server.shutdown()
    print("\n[+] All integration tests passed cleanly.")


if __name__ == "__main__":
    run_tests()
