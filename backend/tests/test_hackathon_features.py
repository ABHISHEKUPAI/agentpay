import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

def test_hackathon_flow():
    client = TestClient(app)

    print("=== 1. Testing Razorpay Checkout & Audit Trail ===")
    sample_cart = [
        {"name": "Ultra Pro Carbon Shoe", "price": 4899.0, "original_price": 5763.53, "savings": 864.53},
        {"name": "Pro Elite Compression Socks", "price": 499.0, "original_price": 587.06, "savings": 88.06}
    ]

    resp = client.post("/buyer/checkout", json={
        "cart": sample_cart
    })
    assert resp.status_code == 200, f"Checkout failed: {resp.text}"
    data = resp.json()
    assert data["status"] == "order_created"
    assert "order_id" in data
    assert "audit_trail" in data
    audit = data["audit_trail"]
    assert audit["policy_verification"]["bounded_money_action"] is True
    print("PASS: Razorpay Order created with Order ID:", data["order_id"])
    print("PASS: Bounded Audit Trail generated successfully.")

    print("\n=== 2. Testing AI Revenue Recovery Workflow & Stopping Rules ===")
    # Register abandoned cart
    session_id = "session_abandoned_999"
    reg_resp = client.post("/recovery/register-abandoned", json={
        "session_id": session_id,
        "cart": sample_cart,
        "user_goal": "marathon running"
    })
    assert reg_resp.status_code == 200
    print("PASS: Abandoned cart registered.")

    # Intervene once
    int_resp1 = client.post("/recovery/intervene", json={"session_id": session_id})
    assert int_resp1.status_code == 200
    int_data1 = int_resp1.json()
    assert int_data1["status"] == "intervention_sent"
    assert "Exclusive 5% Extra Flash Discount" in int_data1["message"]
    print("PASS: Recovery intervention #1 sent with flash discount.")

    # Intervene twice -> STOPPING RULE ENFORCED!
    int_resp2 = client.post("/recovery/intervene", json={"session_id": session_id})
    assert int_resp2.status_code == 200
    int_data2 = int_resp2.json()
    assert int_data2["status"] == "stopping_rule_triggered"
    assert int_data2["intervention_allowed"] is False
    print("PASS: Stopping rule enforced! (Max 1 intervention per session)")

    # Complete recovery
    comp_resp = client.post("/recovery/complete", json={"session_id": session_id})
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert comp_data["status"] == "recovered_successfully"
    print("PASS: Measured money recovered:", comp_data["recovered_amount_inr"])

    # Batch Analytics & Audit Logs
    ana_resp = client.get("/recovery/analytics")
    assert ana_resp.status_code == 200
    analytics = ana_resp.json()
    assert analytics["total_carts_recovered"] >= 1
    assert analytics["total_revenue_recovered_inr"] > 0
    print("PASS: Batch analytics & recovered revenue verified:", analytics["total_revenue_recovered_inr"])

    print("\nALL HACKATHON BACKEND FEATURE TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_hackathon_flow()
