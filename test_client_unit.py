# Python 3.9+ | File: test_client_unit.py | Target: Mobile POS Client Logic Verification
"""
Pure unit test suite verifying client payload serialization, header handling,
and model conversions without requiring loopback network sockets.
"""

from mobile_pos_client import MobilePOSClient, TransactionItem, CreateTransactionRequest, APIError


def test_transaction_serialization():
    item = TransactionItem(
        productId=10,
        productName="Iced Latte",
        quantity=2,
        price=24000.0,
        subtotal=48000.0
    )
    assert item.to_dict() == {
        "productId": 10,
        "productName": "Iced Latte",
        "quantity": 2,
        "price": 24000.0,
        "subtotal": 48000.0
    }

    req = CreateTransactionRequest(
        items=[item],
        subtotal=48000.0,
        tax=4800.0,
        payment_method="CASH",
        cash_amount=100000.0,
        change_amount=47200.0,
        discount_id=None,
        additional_fee_id=None
    )
    serialized = req.to_dict()
    assert serialized["items"][0]["productId"] == 10
    assert serialized["subtotal"] == 48000.0
    assert serialized["tax"] == 4800.0
    assert serialized["payment_method"] == "CASH"
    print("[+] Model serialization: PASSED")


def test_client_headers_and_auth():
    client = MobilePOSClient(base_url="http://43.157.205.66:5000")
    assert "Authorization" not in client.headers
    assert client.headers["Content-Type"] == "application/json"
    assert client.headers["Accept"] == "application/json"

    client.set_token("sample_jwt_token_123")
    assert client.headers["Authorization"] == "Bearer sample_jwt_token_123"

    client.clear_token()
    assert "Authorization" not in client.headers
    print("[+] Header and Bearer token management: PASSED")


if __name__ == "__main__":
    test_transaction_serialization()
    test_client_headers_and_auth()
    print("[+] All unit tests passed successfully.")
