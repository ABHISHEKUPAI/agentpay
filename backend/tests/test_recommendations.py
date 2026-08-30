import os
import sys

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.services.shopping_service import (
    build_main_product_options,
    build_cross_sell_recommendations,
    build_checkout_bill,
    build_recommendation
)

def run_tests():
    db = SessionLocal()
    try:
        print("=== Test 1: Main Product Asked Options (Highest Cost First) ===")
        main_res = build_main_product_options(
            db=db,
            main_category="running_shoes",
            budget=5000.0
        )

        assert main_res["status"] == "main_selection"
        mains = main_res["main_products"]
        assert len(mains) > 0

        # Verify ordering: highest cost shoe first
        main_prices = [p["price"] for p in mains]
        assert main_prices == sorted(main_prices, reverse=True), f"Main shoes should start with highest cost first! Got: {main_prices}"
        print("PASS: Main asked products sorted highest cost first:", [f"{p['name']}: ₹{p['price']}" for p in mains])

        # Verify personalized need statement for main shoe
        for p in mains:
            assert "personalized_need" in p
            assert len(p["personalized_need"]) > 0
        print("PASS: Personalized need statement present for all main shoes.")

        msg_main = main_res["message"]
        print("\n--- Main Asked Items Display (Highest Cost First) ---")
        print(msg_main)
        print("----------------------------------------------------\n")

        print("=== Test 2: Cross-Sell Recommendations (Least Costly First) ===")
        chosen_main = mains[0]  # e.g., Ultra Pro Carbon Shoe (₹4899)
        cross_res = build_cross_sell_recommendations(
            db=db,
            chosen_main=chosen_main,
            related_categories=["running_socks", "running_shorts", "running_shirt"],
            budget=5000.0
        )

        assert cross_res["status"] == "recommendations_ready"
        recs = cross_res["recommended_products"]
        assert len(recs) > 0

        # Verify ordering: least costly recommended product first
        rec_prices = [p["price"] for p in recs]
        assert rec_prices == sorted(rec_prices), f"Recommendations must be sorted least cost first! Got: {rec_prices}"
        print("PASS: Recommended products sorted least cost first:", [f"{p['name']}: ₹{p['price']}" for p in recs])

        # Verify importance & social proof statement
        for p in recs:
            assert "personalized_reason" in p
            assert ("runners buy this" in p["personalized_reason"] or "Popular" in p["personalized_reason"])
        print("PASS: Importance & social proof reason present for recommendations.")

        msg_cross = cross_res["message"]
        print("\n--- Cross-Sell Recommendations Display (Least Cost First) ---")
        print(msg_cross)
        print("-------------------------------------------------------------\n")

        print("=== Test 3: Checkout Bill Generation ===")
        cart = [chosen_main] + recs
        bill_res = build_checkout_bill(cart)

        assert bill_res["status"] == "complete"
        assert bill_res["total"] > 0
        assert bill_res["total_savings"] > 0
        assert "OFFICIAL CHECKOUT BILL" in bill_res["message"]
        assert "Order Confirmed!" in bill_res["message"]

        print("\n--- Final Itemized Checkout Bill ---")
        print(bill_res["message"])
        print("------------------------------------\n")

        print("ALL FLOW TESTS PASSED SUCCESSFULLY!")

    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
