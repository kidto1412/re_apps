# Python 3.9+ | File: pos_cli.py | Target: Mobile POS Interactive CLI Management Tool
"""
Interactive command-line tool for the Mobile POS system.
Supports querying inventory, simulating sales transactions, running stock opname, and viewing analytics.
Usage:
  /usr/bin/python3 pos_cli.py --help
  /usr/bin/python3 pos_cli.py --token <token> products
  /usr/bin/python3 pos_cli.py --token <token> report
"""

from __future__ import annotations
import argparse
import sys
from mobile_pos_client import MobilePOSClient, TransactionItem, CreateTransactionRequest, APIError
from receipt_generator import ReceiptFormatter


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(val)))
    
    header_str = " | ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
    separator = "-+-".join("-" * w for w in col_widths)
    row_strs = [" | ".join(f"{str(v):<{col_widths[i]}}" for i, v in enumerate(r)) for r in rows]
    return f"\n{header_str}\n{separator}\n" + "\n".join(row_strs) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Mobile POS Management CLI")
    parser.add_argument("--url", default="http://127.0.0.1:5000", help="Target backend URL")
    parser.add_argument("--token", default=None, help="Bearer authorization token")
    
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Auth login
    login_p = subparsers.add_parser("login", help="Authenticate with the backend")
    login_p.add_argument("-u", "--username", required=True)
    login_p.add_argument("-p", "--password", required=True)
    login_p.add_argument("--staff", action="store_true", help="Login as staff instead of owner")

    # Catalog & Config
    subparsers.add_parser("products", help="List product catalog and stock")
    subparsers.add_parser("categories", help="List catalog categories")
    subparsers.add_parser("discounts", help="List active store discounts")
    subparsers.add_parser("fees", help="List store fees and surcharges")
    subparsers.add_parser("customers", help="List registered customers")
    subparsers.add_parser("suppliers", help="List registered suppliers")
    subparsers.add_parser("purchases", help="List vendor purchasing history")
    subparsers.add_parser("employees", help="List store employees and staff")
    subparsers.add_parser("store-profile", help="View store profile and receipt branding")
    subparsers.add_parser("subscription", help="View SaaS subscription status")

    # Update Store
    st_p = subparsers.add_parser("update-store", help="Update store profile")
    st_p.add_argument("--name", required=True)
    st_p.add_argument("--type", default="F&B / Cafe")
    st_p.add_argument("--address", default="")
    st_p.add_argument("--phone", default="")
    st_p.add_argument("--email", default="")
    st_p.add_argument("--footer", default="Thank you for your visit!")

    # Employee Add
    emp_p = subparsers.add_parser("add-employee", help="Register a new employee/cashier (Owner only)")
    emp_p.add_argument("-u", "--username", required=True)
    emp_p.add_argument("-p", "--password", required=True)
    emp_p.add_argument("-n", "--name", required=True)
    emp_p.add_argument("--phone", default=None)
    emp_p.add_argument("--role", choices=["staff", "owner"], default="staff")

    # Change password
    cp_p = subparsers.add_parser("change-password", help="Change account password")
    cp_p.add_argument("--old", required=True, help="Current password")
    cp_p.add_argument("--new", required=True, help="New password")

    # Supplier Add
    supp_p = subparsers.add_parser("add-supplier", help="Register a new supplier")
    supp_p.add_argument("--name", required=True, help="Supplier business name")
    supp_p.add_argument("--phone", default=None)
    supp_p.add_argument("--email", default=None)
    supp_p.add_argument("--address", default=None)

    # Restock Purchase
    restock_p = subparsers.add_parser("restock", help="Record a purchase order to increase product stock")
    restock_p.add_argument("--product-id", type=int, required=True)
    restock_p.add_argument("--qty", type=int, required=True)
    restock_p.add_argument("--cost", type=float, required=True, help="Cost per unit")
    restock_p.add_argument("--supplier-id", type=int, default=None)
    restock_p.add_argument("--invoice", default=None)
    restock_p.add_argument("--notes", default="Restock purchase")

    # Customer Add
    cust_p = subparsers.add_parser("add-customer", help="Register a new customer")
    cust_p.add_argument("--name", required=True, help="Customer full name")
    cust_p.add_argument("--phone", default=None, help="Customer phone number")
    cust_p.add_argument("--email", default=None, help="Customer email address")
    cust_p.add_argument("--address", default=None, help="Customer address")

    # Transactions list
    subparsers.add_parser("transactions", help="View transaction history")

    # Checkout / Create transaction
    checkout_p = subparsers.add_parser("checkout", help="Create a transaction")
    checkout_p.add_argument("--product-id", type=int, required=True)
    checkout_p.add_argument("--name", default="POS Product")
    checkout_p.add_argument("--qty", type=int, default=1)
    checkout_p.add_argument("--price", type=float, required=True)
    checkout_p.add_argument("--cash", type=float, required=True)
    checkout_p.add_argument("--customer-id", type=int, default=None, help="Link transaction to customer ID")

    # Stock Opname
    opname_p = subparsers.add_parser("opname", help="Perform stock opname audit count")
    opname_p.add_argument("--product-id", type=int, required=True)
    opname_p.add_argument("--count", type=int, required=True, help="Physical counted quantity")
    opname_p.add_argument("--notes", default="Physical audit")

    # Opname History
    subparsers.add_parser("opname-history", help="View stock opname log")

    # Stock Movement Ledger
    mv_p = subparsers.add_parser("stock-history", help="View unified stock delta audit movements")
    mv_p.add_argument("--product-id", type=int, default=None, help="Filter movements by product ID")

    # Thermal Receipt Printing
    rc_p = subparsers.add_parser("receipt", help="Render formatted thermal receipt for a transaction")
    rc_p.add_argument("--tx-id", type=int, required=True, help="Transaction ID")
    rc_p.add_argument("--width", type=int, default=32, choices=[32, 48], help="Paper width (32=58mm, 48=80mm)")

    # Sales Report
    subparsers.add_parser("report", help="Generate store sales summary")

    args = parser.parse_args()
    client = MobilePOSClient(base_url=args.url, token=args.token)

    try:
        if args.command == "login":
            if args.staff:
                res = client.login_staff(args.username, args.password)
            else:
                res = client.login_owner(args.username, args.password)
            token = res.get("token")
            print(f"[+] Login successful.")
            print(f"    Role: {res.get('data', {}).get('role')}")
            print(f"    Token: {token}")
            print(f"\nTip: pass `--token {token}` in subsequent commands.")

        elif args.command == "products":
            res = client.list_products()
            items = res.get("data", [])
            if not items:
                print("No products found.")
                return
            headers = ["ID", "Name", "Barcode", "Price", "Stock", "Category"]
            rows = [
                [p.get("id"), p.get("name"), p.get("barcode") or "-", f"{p.get('price', 0):,.0f}", p.get("stock"), p.get("category_name") or "-"]
                for p in items
            ]
            print(format_table(headers, rows))

        elif args.command == "categories":
            res = client.list_categories()
            items = res.get("data", [])
            headers = ["ID", "Category Name"]
            rows = [[c.get("id"), c.get("name")] for c in items]
            print(format_table(headers, rows))

        elif args.command == "discounts":
            res = client.list_discounts()
            items = res.get("data", [])
            headers = ["ID", "Name", "Percentage", "Fixed Amount"]
            rows = [[d.get("id"), d.get("name"), f"{d.get('percentage', 0)}%", f"{d.get('fixed_amount', 0):,.0f}"] for d in items]
            print(format_table(headers, rows))

        elif args.command == "fees":
            res = client.list_additional_fees()
            items = res.get("data", [])
            headers = ["ID", "Name", "Percentage", "Fixed Amount"]
            rows = [[f.get("id"), f.get("name"), f"{f.get('percentage', 0)}%", f"{f.get('fixed_amount', 0):,.0f}"] for f in items]
            print(format_table(headers, rows))

        elif args.command == "customers":
            res = client.list_customers()
            items = res.get("data", [])
            headers = ["ID", "Name", "Phone", "Email", "Address"]
            rows = [[c.get("id"), c.get("name"), c.get("phone") or "-", c.get("email") or "-", c.get("address") or "-"] for c in items]
            print(format_table(headers, rows))

        elif args.command == "add-customer":
            res = client.create_customer(name=args.name, phone=args.phone, email=args.email, address=args.address)
            data = res.get("data", {})
            print(f"[+] Customer created successfully. ID: {data.get('id')}, Name: {data.get('name')}")

        elif args.command == "suppliers":
            res = client.list_suppliers()
            items = res.get("data", [])
            headers = ["ID", "Name", "Phone", "Email", "Address"]
            rows = [[s.get("id"), s.get("name"), s.get("phone") or "-", s.get("email") or "-", s.get("address") or "-"] for s in items]
            print(format_table(headers, rows))

        elif args.command == "add-supplier":
            res = client.create_supplier(name=args.name, phone=args.phone, email=args.email, address=args.address)
            data = res.get("data", {})
            print(f"[+] Supplier registered successfully. ID: {data.get('id')}, Name: {data.get('name')}")

        elif args.command == "employees":
            res = client.list_employees()
            items = res.get("data", [])
            headers = ["ID", "Username", "Role", "Name", "Phone", "Active"]
            rows = [[e.get("id"), e.get("username"), e.get("role"), e.get("name"), e.get("phone") or "-", "Yes" if e.get("is_active") else "No"] for e in items]
            print(format_table(headers, rows))

        elif args.command == "add-employee":
            res = client.create_employee(username=args.username, password=args.password, name=args.name, phone=args.phone, role=args.role)
            data = res.get("data", {})
            print(f"[+] Employee created successfully. ID: {data.get('id')}, Username: {data.get('username')}, Role: {data.get('role')}")

        elif args.command == "change-password":
            res = client.change_password(old_password=args.old, new_password=args.new)
            print(f"[+] {res.get('message', 'Password changed successfully')}")

        elif args.command == "store-profile":
            res = client.get_store_profile()
            data = res.get("data", {})
            print("====================================")
            print("           STORE PROFILE            ")
            print("====================================")
            print(f"Store Name    : {data.get('name')}")
            print(f"Business Type : {data.get('business_type')}")
            print(f"Address       : {data.get('address')}")
            print(f"Contact       : {data.get('phone')} | {data.get('email')}")
            print(f"Currency      : {data.get('currency')}")
            print(f"Receipt Note  : {data.get('receipt_footer')}")

        elif args.command == "update-store":
            res = client.update_store_profile(
                name=args.name,
                business_type=args.type,
                address=args.address,
                phone=args.phone,
                email=args.email,
                receipt_footer=args.footer
            )
            print(f"[+] {res.get('message', 'Store profile updated')}")

        elif args.command == "subscription":
            res = client.get_subscription_plan()
            data = res.get("data", {})
            print("====================================")
            print("        SUBSCRIPTION STATUS         ")
            print("====================================")
            print(f"Plan Name     : {data.get('plan_name')}")
            print(f"Status        : {data.get('status')}")
            print(f"Expires At    : {data.get('expires_at')}")
            print(f"Max Outlets   : {data.get('max_outlets')}")
            print(f"Max Staff     : {data.get('max_staff')}")
            print(f"Features      : {data.get('features_json')}")

        elif args.command == "receipt":
            store_res = client.get_store_profile()
            store = store_res.get("data", {})

            tx_res = client.list_transactions()
            tx_list = tx_res.get("data", [])
            target_tx = next((t for t in tx_list if t.get("id") == args.tx_id), None)
            if not target_tx:
                print(f"[-] Transaction ID #{args.tx_id} not found.")
                sys.exit(1)

            formatter = ReceiptFormatter(width=args.width)
            print(formatter.format_text(store, target_tx))

        elif args.command == "purchases":
            res = client.list_purchases()
            items = res.get("data", [])
            if not items:
                print("No purchase records found.")
                return
            headers = ["ID", "Invoice", "Supplier", "Total Cost", "Notes", "Date"]
            rows = [
                [p.get("id"), p.get("invoice_number"), p.get("supplier_name") or "-", f"{p.get('total_cost', 0):,.0f}", p.get("notes") or "-", p.get("created_at")]
                for p in items
            ]
            print(format_table(headers, rows))

        elif args.command == "restock":
            items = [{"product_id": args.product_id, "quantity": args.qty, "cost_per_unit": args.cost}]
            res = client.create_purchase(items=items, supplier_id=args.supplier_id, invoice_number=args.invoice, notes=args.notes)
            data = res.get("data", {})
            print(f"[+] Restock purchase registered.")
            print(f"    Purchase ID: {data.get('purchase_id')}")
            print(f"    Invoice: {data.get('invoice_number')}")

        elif args.command == "transactions":
            res = client.list_transactions()
            items = res.get("data", [])
            if not items:
                print("No transaction records found.")
                return
            headers = ["ID", "Subtotal", "Tax", "Total", "Payment", "Cash", "Change", "Created At"]
            rows = [
                [
                    t.get("id"),
                    f"{t.get('subtotal', 0):,.0f}",
                    f"{t.get('tax', 0):,.0f}",
                    f"{t.get('total_amount', 0):,.0f}",
                    t.get("payment_method"),
                    f"{t.get('cash_amount', 0):,.0f}",
                    f"{t.get('change_amount', 0):,.0f}",
                    t.get("created_at")
                ]
                for t in items
            ]
            print(format_table(headers, rows))

        elif args.command == "checkout":
            subtotal = args.qty * args.price
            tax = round(subtotal * 0.1, 2)
            total = subtotal + tax
            change = args.cash - total
            if change < 0:
                print(f"[-] Error: Insufficient cash provided. Total due: {total:,.0f}, Cash given: {args.cash:,.0f}")
                sys.exit(1)

            req = CreateTransactionRequest(
                items=[TransactionItem(productId=args.product_id, productName=args.name, quantity=args.qty, price=args.price, subtotal=subtotal)],
                subtotal=subtotal,
                tax=tax,
                payment_method="CASH",
                cash_amount=args.cash,
                change_amount=change,
                customer_id=args.customer_id
            )
            res = client.create_transaction(req)
            print("[+] Transaction committed successfully.")
            print(f"    Transaction ID: {res.get('data', {}).get('transaction_id')}")
            print(f"    Total: {total:,.0f} | Cash: {args.cash:,.0f} | Change: {change:,.0f}")

        elif args.command == "opname":
            res = client.create_stock_opname(args.product_id, args.count, args.notes)
            data = res.get("data", {})
            print("[+] Stock Opname recorded.")
            print(f"    Product: {data.get('product_name')} (ID: {data.get('product_id')})")
            print(f"    Previous: {data.get('previous_stock')} -> New: {data.get('new_stock')} (Diff: {data.get('difference')})")

        elif args.command == "opname-history":
            res = client.list_stock_opname()
            items = res.get("data", [])
            if not items:
                print("No stock opname history found.")
                return
            headers = ["ID", "Product", "Physical", "System", "Diff", "Notes", "Date"]
            rows = [
                [o.get("id"), o.get("product_name"), o.get("physical_count"), o.get("system_count"), o.get("difference"), o.get("notes") or "-", o.get("created_at")]
                for o in items
            ]
            print(format_table(headers, rows))

        elif args.command == "stock-history":
            res = client.list_stock_movements(product_id=args.product_id)
            items = res.get("data", [])
            if not items:
                print("No stock movements recorded.")
                return
            headers = ["ID", "Product", "Type", "Delta", "Ref ID", "Notes", "Date"]
            rows = [
                [
                    m.get("id"),
                    m.get("product_name"),
                    m.get("movement_type"),
                    f"+{m.get('quantity')}" if m.get("quantity", 0) > 0 else str(m.get("quantity")),
                    m.get("reference_id") or "-",
                    m.get("notes") or "-",
                    m.get("created_at")
                ]
                for m in items
            ]
            print(format_table(headers, rows))

        elif args.command == "report":
            res = client.get_sales_summary()
            summary = res.get("data", {})
            print("====================================")
            print("         SALES SUMMARY REPORT       ")
            print("====================================")
            print(f"Total Transactions : {summary.get('total_orders', 0)}")
            print(f"Gross Revenue      : IDR {summary.get('gross_revenue', 0):,.0f}")
            print(f"Total Tax Collected: IDR {summary.get('total_tax', 0):,.0f}")
            print(f"Total Discounts    : IDR {summary.get('total_discounts', 0):,.0f}")
            
            top_products = summary.get("top_products", [])
            if top_products:
                print("\n--- Top Performing Products ---")
                headers = ["Product Name", "Units Sold", "Total Sales"]
                rows = [[p.get("product_name"), p.get("units_sold"), f"IDR {p.get('total_sales', 0):,.0f}"] for p in top_products]
                print(format_table(headers, rows))

    except APIError as e:
        print(f"[-] API Error ({e.status_code}): {e.message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
