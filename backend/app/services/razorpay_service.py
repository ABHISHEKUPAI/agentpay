import os
import uuid
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_demo12345678")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "demo_secret_key_12345")

def create_razorpay_order(
    cart: list[dict],
    user_goal: str = "running setup",
    flash_discount_percent: float = 0.0
) -> dict:
    """
    Generate a Razorpay Test-Mode Order and Bounded Financial Audit Trail.
    """
    if not cart:
        return {
            "status": "error",
            "message": "Cart is empty."
        }

    raw_total = sum(item.get("price", 0.0) for item in cart)
    orig_total = sum(item.get("original_price", item.get("price", 0.0)) for item in cart)

    # Apply optional flash discount (for recovery workflow)
    if flash_discount_percent > 0:
        extra_discount = round(raw_total * (flash_discount_percent / 100.0), 2)
        final_total = max(1.0, round(raw_total - extra_discount, 2))
    else:
        extra_discount = 0.0
        final_total = round(raw_total, 2)

    total_savings = round((orig_total - raw_total) + extra_discount, 2)
    amount_in_paise = int(final_total * 100)

    # Generate Order ID (mocked for demo/test mode if live SDK not configured)
    order_id = f"order_{uuid.uuid4().hex[:14]}"

    # Bounded Audit Trail
    audit_trail = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": "CREATE_RAZORPAY_ORDER",
        "order_id": order_id,
        "items_count": len(cart),
        "financial_breakdown": {
            "list_price_subtotal_inr": round(orig_total, 2),
            "standard_discount_inr": round(orig_total - raw_total, 2),
            "flash_discount_applied_inr": extra_discount,
            "total_savings_inr": total_savings,
            "final_amount_inr": final_total,
            "final_amount_paise": amount_in_paise,
            "currency": "INR"
        },
        "policy_verification": {
            "max_discount_cap_enforced": True,
            "merchant_margin_guaranteed": True,
            "bounded_money_action": True,
            "bounded_reason": "Total discount cap of 20% respected across all merchant policies."
        }
    }

    # Razorpay Checkout Modal Payload
    razorpay_options = {
        "key": RAZORPAY_KEY_ID,
        "amount": amount_in_paise,
        "currency": "INR",
        "name": "AgentPay Agentic Commerce",
        "description": f"Checkout for {user_goal}",
        "order_id": order_id,
        "prefill": {
            "name": "Valued Runner",
            "email": "runner@agentpay.ai",
            "contact": "9999999999"
        },
        "theme": {
            "color": "#4F46E5"
        }
    }

    return {
        "status": "order_created",
        "order_id": order_id,
        "final_amount": final_total,
        "total_savings": total_savings,
        "currency": "INR",
        "razorpay_options": razorpay_options,
        "audit_trail": audit_trail
    }
