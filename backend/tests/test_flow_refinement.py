import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

def run_flow_refinement_tests():
    client = TestClient(app)

    print("=========================================================")
    print("🚀 REFINED MULTI-STAGE SALES FLOW & UPSELL TEST SUITE")
    print("=========================================================\n")

    cid = "test_conv_refinement_999"

    # Step 1: Request badminton racket -> Loads 1 main product
    print("Step 1: Load Single Main Product (Option 1: Checkout, Option 2: Show Next)")
    r1 = client.post("/buyer/chat", json={
        "conversation_id": cid,
        "message": "I need a badminton racket for budget 3000 as a beginner"
    })
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["status"] == "main_product"
    assert "Option 1" in d1["message"] and "Option 2" in d1["message"]
    assert "Yonex Muscle Power 29" in d1["message"]
    print("  PASS: Single main product displayed with Option 1 (Checkout) & Option 2 (Show Next)!\n")

    # Step 2: Select Option 2 -> Show Next Product
    print("Step 2: User selects Option 2 (Show Next Product)")
    r2 = client.post("/buyer/chat", json={
        "conversation_id": cid,
        "message": "2"
    })
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["status"] == "main_product"
    assert "Li-Ning G-Force Superlite" in d2["message"] or "Option 2 of" in d2["message"]
    print("  PASS: Loaded next main product from catalog!\n")

    # Step 3: Select Option 1 (Checkout) -> Triggers "Crazy Deals" Upsell
    print("Step 3: User selects Option 1 (Checkout) -> Triggers Crazy Deals Upsell")
    r3 = client.post("/buyer/chat", json={
        "conversation_id": cid,
        "message": "1"
    })
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["status"] == "crazy_deals"
    assert "We have got crazy deals just for you!" in d3["message"]
    assert "Option 1" in d3["message"] and "Option 2" in d3["message"] and "Option 3" in d3["message"]
    print("  PASS: Crazy deals upsell presented with 3 options!\n")

    # Step 4: User selects Option 3 (Checkout without recommendations) -> Asks Reason
    print("Step 4: User selects Option 3 -> Asks for Decline Reason")
    r4 = client.post("/buyer/chat", json={
        "conversation_id": cid,
        "message": "3"
    })
    assert r4.status_code == 200
    d4 = r4.json()
    assert d4["status"] == "decline_reason"
    assert "reason" in d4["message"].lower()
    print("  PASS: Agent asks for the reason before proceeding!\n")

    # Step 5: User gives reason -> Presents Special Lower-Priced Add-on Deal
    print("Step 5: User gives reason -> Presents One-Time Lower-Priced Deal")
    r5 = client.post("/buyer/chat", json={
        "conversation_id": cid,
        "message": "Budget is slightly tight for extra items today"
    })
    assert r5.status_code == 200
    d5 = r5.json()
    assert d5["status"] == "discounted_deals"
    assert "EXCLUSIVE ONE-TIME DISCOUNT UNLOCKED FOR YOU" in d5["message"]
    assert "Option 1" in d5["message"] and "Option 2" in d5["message"] and "Option 3" in d5["message"]
    print("  PASS: One-time lower-priced deal presented with 3 final options!\n")

    # Step 6: User selects Option 2 (Select items '1, 2') -> Final Checkout & Razorpay Order
    print("Step 6: User selects items '1, 2' -> Final Checkout & Razorpay Test Order")
    r6 = client.post("/buyer/chat", json={
        "conversation_id": cid,
        "message": "1, 2"
    })
    assert r6.status_code == 200
    d6 = r6.json()
    assert d6["status"] == "complete"
    assert len(d6["cart"]) >= 2
    assert "razorpay_order" in d6
    assert "audit_trail" in d6
    assert "OFFICIAL CHECKOUT BILL" in d6["message"]
    print("  PASS: Selected add-ons added to cart and Razorpay Test Order generated with Audit Trail!\n")

    print("=========================================================")
    print("🎉 ALL REFINED MULTI-STAGE SALES FLOW TESTS PASSED!")
    print("=========================================================")

if __name__ == "__main__":
    run_flow_refinement_tests()
