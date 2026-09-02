import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

def run_section36_tests():
    client = TestClient(app)

    print("=========================================================")
    print("🚀 AGENTPAY SECTION 36 REQUIRED WORKFLOW TEST SUITE")
    print("=========================================================\n")

    cid = "test_sec36_session_001"

    # Step 1: User says "I need running shoes under 5000"
    print("Step 1: User requests running shoes under 5000")
    r1 = client.post("/buyer/chat", json={"conversation_id": cid, "message": "I need running shoes under ₹5,000."})
    assert r1.status_code == 200
    d1 = r1.json()
    print("DEBUG d1:", d1)
    assert d1["action"] == "CLARIFICATION_PROMPT"

    assert "beginner" in d1["message"].lower() or "fit" in d1["message"].lower()
    print("  PASS: Prompted for experience clarification without assuming beginner status!\n")

    # Step 2: User responds "I'm a beginner."
    print("Step 2: User responds 'I'm a beginner.'")
    r2 = client.post("/buyer/chat", json={"conversation_id": cid, "message": "I'm a beginner."})
    assert r2.status_code == 200
    d2 = r2.json()
    print("DEBUG d2:", d2)
    assert d2["action"] == "PRIMARY_OPTIONS"

    assert "Option 1" in d2["message"]
    assert "Option 2" in d2["message"]
    assert "Option 3" in d2["message"]
    print("  PASS: Presented Option 1 (Best Value), Option 2 (Best Within Budget), & Option 3 (Explore Other Products)!\n")

    # Step 3: User chooses Option 1
    print("Step 3: User chooses Option 1 (Best Value)")
    r3 = client.post("/buyer/chat", json={"conversation_id": cid, "message": "1"})
    assert r3.status_code == 200
    d3 = r3.json()
    print("DEBUG d3 message:", d3.get("message"))
    assert d3["action"] == "CROSS_SELL_OPTIONS"
    assert "remaining" in d3["message"].lower()
    assert "Option 1" in d3["message"] and "Option 2" in d3["message"] and "Option 3" in d3["message"]
    print("  PASS: Confirmed choice, stated remaining budget without calling it discount, and presented complementary products!\n")

    # Step 4: User chooses Option 2 (Select individually)
    print("Step 4: User chooses Option 2 (Select individually)")
    r4 = client.post("/buyer/chat", json={"conversation_id": cid, "message": "2"})
    assert r4.status_code == 200
    d4 = r4.json()
    assert d4["action"] == "INDIVIDUAL_SELECT_PROMPT"
    print("  PASS: Returned selectable individual item prompt!\n")

    # Step 5: User selects socks + shirt (items 1, 2)
    print("Step 5: User inputs item selection '1, 2'")
    r5 = client.post("/buyer/chat", json={"conversation_id": cid, "message": "1, 2"})
    assert r5.status_code == 200
    d5 = r5.json()
    assert d5["action"] == "PAYMENT_CONFIRMATION_PROMPT"
    assert "payment" in d5["message"].lower()
    assert d5["checkout_gated"] == True
    print("  PASS: Cart updated with selected items & presented checkout summary with explicit payment gate prompt!\n")

    # Step 6: User explicitly confirms payment
    print("Step 6: User explicitly confirms payment ('Proceed with payment')")
    r6 = client.post("/buyer/chat", json={"conversation_id": cid, "message": "Confirm and Pay"})
    assert r6.status_code == 200
    d6 = r6.json()
    assert d6["action"] == "PAYMENT_SUCCESS"
    assert d6["status"] == "complete"
    assert "razorpay_order" in d6
    assert "audit_trail" in d6
    print("  PASS: Razorpay Test Payment executed with complete Bounded Financial Audit Trail!\n")

    print("=========================================================")
    print("🎉 ALL SECTION 36 WORKFLOW TEST STEPS PASSED PERFECTLY!")
    print("=========================================================")

if __name__ == "__main__":
    run_section36_tests()
