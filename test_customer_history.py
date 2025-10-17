# Test Workflow - Customer History Update
# This script tests the complete workflow

import frappe
from frappe.utils import flt

def test_customer_history_workflow():
    """Test complete workflow"""
    
    print("\n" + "=" * 70)
    print("TESTING CUSTOMER HISTORY WORKFLOW")
    print("=" * 70)
    
    # Find a test customer with contract
    customer = "Asadbek"
    
    print(f"\n1. Customer: {customer}")
    
    # Get latest Sales Order
    so_list = frappe.get_all(
        "Sales Order",
        filters={"customer": customer, "docstatus": 1},
        fields=["name", "advance_paid", "custom_grand_total_with_interest"],
        order_by="creation desc",
        limit=1
    )
    
    if not so_list:
        print("   ❌ No Sales Order found!")
        return
    
    so = so_list[0]
    print(f"\n2. Sales Order: {so.name}")
    print(f"   Grand Total: ${flt(so.custom_grand_total_with_interest)}")
    print(f"   Advance Paid: ${flt(so.advance_paid)}")
    print(f"   Outstanding: ${flt(so.custom_grand_total_with_interest) - flt(so.advance_paid)}")
    
    # Get Payment Entries
    payments = frappe.get_all(
        "Payment Entry",
        filters={"party": customer, "docstatus": 1, "payment_type": "Receive"},
        fields=["name", "posting_date", "paid_amount", "custom_contract_reference"],
        order_by="posting_date desc",
        limit=5
    )
    
    print(f"\n3. Payment Entries ({len(payments)} submitted):")
    for p in payments:
        link_status = "✅ Linked" if p.custom_contract_reference else "❌ Not Linked"
        print(f"   - {p.name} | ${p.paid_amount} | {p.posting_date} | {link_status}")
    
    # Get Payment Schedule
    schedule = frappe.get_all(
        "Payment Schedule",
        filters={"parent": so.name, "parenttype": "Sales Order"},
        fields=["idx", "due_date", "payment_amount", "paid_amount"],
        order_by="idx"
    )
    
    print(f"\n4. Payment Schedule ({len(schedule)} rows):")
    for s in schedule:
        paid = flt(s.paid_amount)
        due = flt(s.payment_amount)
        status = "✅ Paid" if paid >= due else f"⏳ ${due - paid} remaining"
        print(f"   Row {s.idx}: Due {s.due_date} | ${due} | Paid: ${paid} | {status}")
    
    # Test API
    from cash_flow_app.cash_flow_management.api.customer_history import get_customer_contracts, get_payment_schedule_with_history
    
    print(f"\n5. Testing API:")
    contracts = get_customer_contracts(customer)
    if contracts:
        c = contracts[0]
        print(f"   ✅ get_customer_contracts() returned: {c.name}")
        print(f"      Paid: ${c.paid_amount} | Outstanding: ${c.outstanding_amount}")
    else:
        print(f"   ❌ get_customer_contracts() returned empty")
    
    schedule_api = get_payment_schedule_with_history(customer)
    if schedule_api:
        print(f"   ✅ get_payment_schedule_with_history() returned: {len(schedule_api)} rows")
        # Show status distribution
        statuses = {}
        for row in schedule_api:
            status = row.get('status', 'Unknown')
            statuses[status] = statuses.get(status, 0) + 1
        print(f"      Status distribution: {statuses}")
    else:
        print(f"   ❌ get_payment_schedule_with_history() returned empty")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETED!")
    print("=" * 70)
    print("\n✅ Customer History should now display in Customer form!")
    print("   Go to: http://your-site/app/customer/" + customer)
    print("\n")

if __name__ == "__main__":
    test_customer_history_workflow()
