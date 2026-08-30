import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

def test_api():
    client = TestClient(app)
    
    print("Testing GET /health...")
    resp = client.get("/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    print("PASS: Health check ok")

    print("Testing POST /buyer/recommend...")
    resp = client.post("/buyer/recommend", json={"message": "I need running shoes for budget 5000"})
    assert resp.status_code == 200, f"Recommend endpoint failed: {resp.text}"
    data = resp.json()
    assert data["status"] == "complete"
    assert "Top Running Shoes Handpicked" in data["message"]
    print("PASS: /buyer/recommend endpoint working correctly")

    print("Testing POST /buyer/chat multi-turn conversational flow...")
    conv_id = "test_conv_flow_99"

    # Turn 1: Search shoes with budget 5000
    r1 = client.post("/buyer/chat", json={"conversation_id": conv_id, "message": "I need running shoes for budget 5000"})
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["status"] == "main_selection"
    assert "Ultra Pro Carbon Shoe" in d1["message"]
    print("PASS: Turn 1 displays main shoes highest cost first.")

    # Turn 2: User selects option 1
    r2 = client.post("/buyer/chat", json={"conversation_id": conv_id, "message": "1"})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["status"] == "recommendations_ready"
    assert "Ultra Pro Carbon Shoe (₹4899) has been added to your cart" in d2["message"]
    assert "Pro Elite Compression Socks" in d2["message"]
    print("PASS: Turn 2 displays added item success message and recommendations least cost first.")

    # Turn 3: User hits checkout
    r3 = client.post("/buyer/chat", json={"conversation_id": conv_id, "message": "checkout"})
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["status"] == "complete"
    assert "OFFICIAL CHECKOUT BILL" in d3["message"]
    print("PASS: Turn 3 displays official itemized checkout bill.")

    print("ALL API TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_api()
