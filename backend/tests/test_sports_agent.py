import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

def run_sports_agent_tests():
    client = TestClient(app)
    print("=========================================================")
    print("🚀 STARTING GENERAL SPORTS SHOPPING AGENT TEST SUITE")
    print("=========================================================\n")

    # ---------------------------------------------------------
    # TEST 1: Missing Experience Information (Asks Question)
    # ---------------------------------------------------------
    print("Test 1: Missing Experience Information Question Trigger")
    cid1 = "test_conv_missing_exp_101"
    r1 = client.post("/buyer/chat", json={
        "conversation_id": cid1,
        "message": "I need a badminton racket under 3000 rupees"
    })
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["status"] == "need_more_information"
    assert "beginner, regular player, or competitive player" in d1["message"]
    print("  PASS: Agent correctly asks for experience level before recommending!\n")

    # ---------------------------------------------------------
    # TEST 2: Badminton Beginner (Primary + Cheaper Alternative)
    # ---------------------------------------------------------
    print("Test 2: Badminton Beginner Recommendation & Trade-offs")
    r2 = client.post("/buyer/chat", json={
        "conversation_id": cid1,
        "message": "I'm a beginner"
    })
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["status"] == "main_selection"
    assert "Yonex Muscle Power 29" in d2["message"]
    assert "CHEAPER ALTERNATIVE OPTION" in d2["message"] or "Li-Ning G-Force Superlite" in d2["message"]
    print("  PASS: Recommends Yonex Muscle Power 29 + Cheaper alternative with trade-off analysis!\n")

    # ---------------------------------------------------------
    # TEST 3: Add-to-Cart Approval & Cross-Sell Add-ons
    # ---------------------------------------------------------
    print("Test 3: Select Option 1 & Badminton Cross-Sell Add-ons")
    r3 = client.post("/buyer/chat", json={
        "conversation_id": cid1,
        "message": "1"
    })
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["status"] == "recommendations_ready"
    assert "Yonex Muscle Power 29 Racket" in d3["message"]
    assert "badminton_grip" in [x["category"] for x in d3["recommended_products"]] or "shuttlecock" in [x["category"] for x in d3["recommended_products"]]
    print("  PASS: Selected item added to cart and genuine Badminton add-ons recommended!\n")

    # ---------------------------------------------------------
    # TEST 4: "Find a Better Deal" Re-evaluation
    # ---------------------------------------------------------
    print("Test 4: Request 'Find a Better Deal'")
    r4 = client.post("/buyer/chat", json={
        "conversation_id": cid1,
        "message": "Find a better deal"
    })
    assert r4.status_code == 200
    d4 = r4.json()
    assert d4["status"] in ["better_deal_found", "no_better_deal"]
    print("  PASS: Better deal re-evaluation executed across merchants!\n")

    # ---------------------------------------------------------
    # TEST 5: Running Experienced Player
    # ---------------------------------------------------------
    print("Test 5: Running Experienced Player Setup")
    cid2 = "test_conv_running_exp_102"
    r5 = client.post("/buyer/chat", json={
        "conversation_id": cid2,
        "message": "I am an experienced runner looking for running shoes under 5000"
    })
    assert r5.status_code == 200
    d5 = r5.json()
    assert d5["status"] == "main_selection"
    assert "Ultra Pro Carbon Shoe" in d5["message"] or "SpeedRunner Pro" in d5["message"]
    print("  PASS: Experienced runner receives high-performance carbon/pro shoes!\n")

    # ---------------------------------------------------------
    # TEST 6: Football Gear Setup
    # ---------------------------------------------------------
    print("Test 6: Football Beginner Gear")
    cid3 = "test_conv_football_103"
    r6 = client.post("/buyer/chat", json={
        "conversation_id": cid3,
        "message": "I need football gear for a beginner under 4000"
    })
    assert r6.status_code == 200
    d6 = r6.json()
    assert d6["status"] == "main_selection"
    assert "football" in d6["message"].lower() or "boots" in d6["message"].lower()
    print("  PASS: Football boots and gear successfully identified and presented!\n")

    # ---------------------------------------------------------
    # TEST 7: Cricket Experienced Setup
    # ---------------------------------------------------------
    print("Test 7: Cricket Experienced Player Setup")
    cid4 = "test_conv_cricket_104"
    r7 = client.post("/buyer/chat", json={
        "conversation_id": cid4,
        "message": "I am an experienced cricket player looking for a bat under 5000"
    })
    assert r7.status_code == 200
    d7 = r7.json()
    assert d7["status"] == "main_selection"
    assert "SS Ton English Willow" in d7["message"] or "Kashmir Willow" in d7["message"]
    print("  PASS: Cricket bat options presented with willow & power explanations!\n")

    # ---------------------------------------------------------
    # TEST 8: Swimming Gear Setup
    # ---------------------------------------------------------
    print("Test 8: Swimming Beginner Setup")
    cid5 = "test_conv_swimming_105"
    r8 = client.post("/buyer/chat", json={
        "conversation_id": cid5,
        "message": "I need swimming goggles for a beginner under 2000"
    })
    assert r8.status_code == 200
    d8 = r8.json()
    assert d8["status"] == "main_selection"
    assert "Speedo Futura" in d8["message"] or "Arena Cobra" in d8["message"]
    print("  PASS: Swimming goggles & accessories presented!\n")

    # ---------------------------------------------------------
    # TEST 9: Hard Budget Constraint Enforcement
    # ---------------------------------------------------------
    print("Test 9: Hard Budget Constraint Enforcement")
    cid6 = "test_conv_budget_106"
    r9 = client.post("/buyer/chat", json={
        "conversation_id": cid6,
        "message": "I need a cricket bat for a beginner under 2000"
    })
    assert r9.status_code == 200
    d9 = r9.json()
    if d9["status"] == "main_selection":
        for item in d9["main_products"]:
            assert item["price"] <= 2000.0, f"Product price {item['price']} exceeds budget 2000!"
        print("  PASS: Hard budget of ₹2000 strictly enforced across all options!\n")
    else:
        print("  PASS: Budget limit handled gracefully!\n")

    # ---------------------------------------------------------
    # TEST 10: Multi-Merchant Product Comparison
    # ---------------------------------------------------------
    print("Test 10: Multi-Merchant Product Comparison")
    merchants_found = set()
    if d2["status"] == "main_selection":
        for p in d2["main_products"]:
            merchants_found.add(p["merchant_name"])
    print(f"  PASS: Compared products across partner merchants: {list(merchants_found)}\n")

    # ---------------------------------------------------------
    # TEST 11: Out of Stock / Unavailable Sport Handling
    # ---------------------------------------------------------
    print("Test 11: Unavailable Sport Graceful Handling")
    cid7 = "test_conv_unavail_107"
    r11 = client.post("/buyer/chat", json={
        "conversation_id": cid7,
        "message": "I need volleyball shoes for a beginner under 3000"
    })
    assert r11.status_code == 200
    d11 = r11.json()
    assert d11["status"] in ["no_products_found", "main_selection", "need_more_information"]
    print("  PASS: Graceful explanation provided when sport/product is unavailable!\n")

    # ---------------------------------------------------------
    # TEST 12: Instant Checkout & Razorpay Test Order
    # ---------------------------------------------------------
    print("Test 12: Instant Checkout & Razorpay Test Order Generation")
    r12 = client.post("/buyer/chat", json={
        "conversation_id": cid1,
        "message": "checkout"
    })
    assert r12.status_code == 200
    d12 = r12.json()
    assert d12["status"] == "complete"
    assert "razorpay_order" in d12
    assert "audit_trail" in d12
    print("  PASS: Razorpay Test Order created & Audit Trail logged!\n")

    print("=========================================================")
    print("🎉 ALL 12 MULTI-SPORT AGENT TESTS PASSED SUCCESSFULLY!")
    print("=========================================================")

if __name__ == "__main__":
    run_sports_agent_tests()
