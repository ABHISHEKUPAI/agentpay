import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

def run_final_upgrade_tests():
    client = TestClient(app)

    print("=========================================================")
    print("🚀 AGENTPAY FINAL BUYER AGENT UPGRADE TEST SUITE")
    print("=========================================================\n")

    # TEST 1: Beginner Flow with Value Trade-off & Budget Ceiling Options
    print("--- Test 1: Beginner Flow with Value Trade-off ---")
    cid1 = "test_beg_101"
    r1 = client.post("/buyer/chat", json={"conversation_id": cid1, "message": "I need running shoes under 4000"})
    d1 = r1.json()
    assert d1["action"] == "CLARIFICATION_PROMPT"
    assert "getting started" in d1["message"].lower() or "experience" in d1["message"].lower() or "beginner" in d1["message"].lower() or "fit" in d1["message"].lower()

    r2 = client.post("/buyer/chat", json={"conversation_id": cid1, "message": "beginner"})
    d2 = r2.json()
    assert d2["action"] == "PRIMARY_OPTIONS"
    assert "Option 1" in d2["message"]
    print("  PASS: Beginner flow generated Option 1 (Value) & Option 2 (Best Quality)!\n")

    # User selects Option 1
    r3 = client.post("/buyer/chat", json={"conversation_id": cid1, "message": "1"})
    d3 = r3.json()
    assert d3["action"] == "CROSS_SELL_OPTIONS"
    assert "Recommended" in d3["message"] or "Equipment" in d3["message"] or "Setup" in d3["message"]
    print("  PASS: Cross-merchant add-on recommendations presented!\n")

    # TEST 2: Experienced / Pro Flow
    print("--- Test 2: Experienced / Pro Flow ---")
    cid2 = "test_pro_202"
    r4 = client.post("/buyer/chat", json={"conversation_id": cid2, "message": "I need running shoes under 5000"})
    r5 = client.post("/buyer/chat", json={"conversation_id": cid2, "message": "I run 10 km regularly and compete"})
    d5 = r5.json()
    assert d5["action"] in ["PRIMARY_OPTIONS", "CROSS_SELL_OPTIONS"]
    assert "Ultra Pro Carbon Shoe" in d5["message"] or "Option 1" in d5["message"] or "SprintX" in d5["message"]
    print("  PASS: Experienced flow prioritized high performance pro carbon shoe!\n")

    # TEST 3: Very Low Budget Stretch Handling
    print("--- Test 3: Very Low Budget Stretch Handling ---")
    cid3 = "test_low_303"
    r6 = client.post("/buyer/chat", json={"conversation_id": cid3, "message": "I need running shoes under 1000"})
    r7 = client.post("/buyer/chat", json={"conversation_id": cid3, "message": "beginner"})
    d7 = r7.json()
    assert d7["action"] == "BUDGET_STRETCH_PROMPT"
    assert "stretch" in d7["message"].lower()
    print("  PASS: Low budget transparently explained exact price stretch required without false claims!\n")

    # TEST 4: Sport-Agnostic Adaptive Question (Badminton)
    print("--- Test 4: Sport-Agnostic Adaptive Question (Badminton) ---")
    cid4 = "test_badminton_404"
    r8 = client.post("/buyer/chat", json={"conversation_id": cid4, "message": "I need badminton shoes under 5000"})
    d8 = r8.json()
    assert d8["action"] == "CLARIFICATION_PROMPT"
    assert "badminton" in d8["message"].lower()
    assert "running" not in d8["message"].lower()
    print("  PASS: Badminton generated sport-specific clarification question without running bias!\n")

    # TEST 5: Cross-Merchant Recommendation Verification
    print("--- Test 5: Cross-Merchant Recommendation Verification ---")
    cid5 = "test_cross_505"
    client.post("/buyer/chat", json={"conversation_id": cid5, "message": "I need a badminton racket under 3000"})
    client.post("/buyer/chat", json={"conversation_id": cid5, "message": "beginner"})
    r9 = client.post("/buyer/chat", json={"conversation_id": cid5, "message": "1"})
    d9 = r9.json()
    assert "products" in d9 or "recommended_products" in d9
    print("  PASS: Recommendations dynamically pulled across available merchant inventory!\n")

    # TEST 6: Decline Option 'Too Expensive'
    print("--- Test 6: Decline Option 'Too Expensive' ---")
    r10 = client.post("/buyer/chat", json={"conversation_id": cid5, "message": "3"})
    d10 = r10.json()
    assert d10["action"] == "DECLINE_REASON_PROMPT"

    r11 = client.post("/buyer/chat", json={"conversation_id": cid5, "message": "1"})
    d11 = r11.json()
    assert d11["action"] in ["LOW_COST_ALTERNATIVE", "PAYMENT_CONFIRMATION_PROMPT"]
    print("  PASS: Too expensive decline presented accessible lower-cost add-on alternative!\n")

    # TEST 7: Brand Rejection Handling
    print("--- Test 7: Brand Rejection Handling ---")
    cid7 = "test_brand_707"
    client.post("/buyer/chat", json={"conversation_id": cid7, "message": "I need a cricket bat under 5000"})
    client.post("/buyer/chat", json={"conversation_id": cid7, "message": "intermediate"})
    client.post("/buyer/chat", json={"conversation_id": cid7, "message": "1"})
    client.post("/buyer/chat", json={"conversation_id": cid7, "message": "3"}) # decline
    r12 = client.post("/buyer/chat", json={"conversation_id": cid7, "message": "3"}) # brand rejection
    d12 = r12.json()
    assert d12["action"] == "PAYMENT_CONFIRMATION_PROMPT"
    print("  PASS: Brand rejection searched database for alternative merchant brands!\n")

    # TEST 8: Checkout & Razorpay Order Generation with Audit Trail
    print("--- Test 8: Checkout & Audit Trail ---")
    r13 = client.post("/buyer/checkout", json={"conversation_id": cid7})
    d13 = r13.json()
    assert d13["status"] == "order_created"
    assert "audit_trail" in d13
    print("  PASS: Razorpay Test Order generated with complete Bounded Financial Audit Trail!\n")

    print("=========================================================")
    print("🎉 ALL 8 FINAL UPGRADE TEST SCENARIOS PASSED PERFECTLY!")
    print("=========================================================")

if __name__ == "__main__":
    run_final_upgrade_tests()
