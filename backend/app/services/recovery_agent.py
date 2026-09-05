from datetime import datetime
from typing import Optional

class AbandonedCartSession:
    def __init__(self, session_id: str, cart: list[dict], user_goal: str = "running"):
        self.session_id: str = session_id
        self.cart: list[dict] = cart
        self.user_goal: str = user_goal
        self.status: str = "abandoned"  # "abandoned", "intervened", "recovered", "failed"
        self.created_at: str = datetime.utcnow().isoformat() + "Z"
        self.intervention_count: int = 0
        self.recovered_amount: float = 0.0
        self.flash_discount_percent: float = 0.0
        self.audit_history: list[dict] = []

    def get_totals(self):
        raw_total = round(sum(item.get("price", 0.0) for item in self.cart), 2)
        orig_total = round(sum(item.get("original_price", item.get("price", 0.0)) for item in self.cart), 2)
        savings = round(orig_total - raw_total, 2)
        return raw_total, orig_total, savings


# In-memory store for abandoned cart sessions & recovery analytics
abandoned_sessions: dict[str, AbandonedCartSession] = {}
recovered_history: list[dict] = []


def seed_initial_sessions():
    if not abandoned_sessions:
        # Session 1: Abandoned Badminton setup
        s1 = AbandonedCartSession(
            session_id="sess_badminton_pro_991",
            cart=[
                {"id": 1, "name": "Yonex Arcsaber 11 Pro Racket", "price": 4899.0, "original_price": 5499.0},
                {"id": 15, "name": "Yonex Aeroplane Feather Shuttlecocks", "price": 1299.0, "original_price": 1499.0}
            ],
            user_goal="badminton tournament setup"
        )
        s1.audit_history.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": "ABANDONED_CART_DETECTED",
            "session_id": s1.session_id,
            "cart_items_count": 2,
            "potential_revenue_inr": 6198.0,
            "user_savings_left_behind_inr": 800.0,
            "risk_level": "HIGH_ABANDONMENT"
        })
        abandoned_sessions[s1.session_id] = s1

        # Session 2: Intervened Running Kit
        s2 = AbandonedCartSession(
            session_id="sess_running_kit_842",
            cart=[
                {"id": 25, "name": "Nike Air Zoom Pegasus 40", "price": 8499.0, "original_price": 9999.0},
                {"id": 30, "name": "Nike Dri-FIT Running Socks (3-Pack)", "price": 899.0, "original_price": 1099.0}
            ],
            user_goal="marathon preparation kit"
        )
        s2.intervention_count = 1
        s2.status = "intervened"
        s2.flash_discount_percent = 5.0
        s2.audit_history.extend([
            {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "action": "ABANDONED_CART_DETECTED",
                "session_id": s2.session_id,
                "cart_items_count": 2,
                "potential_revenue_inr": 9398.0,
                "user_savings_left_behind_inr": 1700.0,
                "risk_level": "HIGH_ABANDONMENT"
            },
            {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "action": "RECOVERY_INTERVENTION_SENT",
                "session_id": s2.session_id,
                "intervention_count": 1,
                "stopping_rule_limit": 1,
                "flash_discount_applied": 5.0,
                "additional_discount_inr": 469.9,
                "new_cart_total_inr": 8928.1,
                "compliant_escalation": True
            }
        ])
        abandoned_sessions[s2.session_id] = s2

        # Session 3: Already Recovered Gym Gear
        s3 = AbandonedCartSession(
            session_id="sess_gym_starter_712",
            cart=[
                {"id": 40, "name": "Puma Speedcat Pro Training Shoes", "price": 4299.0, "original_price": 4999.0},
                {"id": 42, "name": "Puma Sport Water Bottle 1L", "price": 599.0, "original_price": 799.0}
            ],
            user_goal="gym starter pack"
        )
        s3.intervention_count = 1
        s3.status = "recovered"
        s3.flash_discount_percent = 5.0
        s3.recovered_amount = 4653.1
        s3.audit_history.extend([
            {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "action": "ABANDONED_CART_DETECTED",
                "session_id": s3.session_id,
                "cart_items_count": 2,
                "potential_revenue_inr": 4898.0,
                "user_savings_left_behind_inr": 900.0,
                "risk_level": "HIGH_ABANDONMENT"
            },
            {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "action": "RECOVERY_INTERVENTION_SENT",
                "session_id": s3.session_id,
                "intervention_count": 1,
                "stopping_rule_limit": 1,
                "flash_discount_applied": 5.0,
                "additional_discount_inr": 244.9,
                "new_cart_total_inr": 4653.1,
                "compliant_escalation": True
            },
            {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "action": "RECOVERY_PAYMENT_COMPLETED",
                "session_id": s3.session_id,
                "recovered_amount_inr": 4653.1,
                "status": "SUCCESS"
            }
        ])
        abandoned_sessions[s3.session_id] = s3


# Seed default sessions on load
seed_initial_sessions()



def register_abandoned_cart(session_id: str, cart: list[dict], user_goal: str = "running") -> AbandonedCartSession:
    """
    Detect and register an abandoned cart session.
    """
    session = AbandonedCartSession(session_id, cart, user_goal)
    abandoned_sessions[session_id] = session

    raw_total, orig_total, savings = session.get_totals()
    audit_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": "ABANDONED_CART_DETECTED",
        "session_id": session_id,
        "cart_items_count": len(cart),
        "potential_revenue_inr": raw_total,
        "user_savings_left_behind_inr": savings,
        "risk_level": "HIGH_ABANDONMENT"
    }
    session.audit_history.append(audit_entry)
    return session


def trigger_recovery_intervention(session_id: str) -> dict:
    """
    Execute a bounded recovery intervention workflow.
    Enforces Stopping Rule (Max 1 intervention) & Policy Caps (Max 15% discount off MRP).
    """
    if session_id not in abandoned_sessions:
        return {
            "status": "error",
            "message": "Session not found."
        }

    session = abandoned_sessions[session_id]

    # STOPPING RULE CHECK: Max 1 intervention per session
    if session.intervention_count >= 1:
        return {
            "status": "stopping_rule_triggered",
            "session_id": session_id,
            "message": "Stopping rule enforced: Intervention already sent once. No further push messaging allowed.",
            "intervention_allowed": False
        }

    raw_total, orig_total, savings = session.get_totals()
    existing_disc_pct = round(((orig_total - raw_total) / orig_total * 100), 2) if orig_total > 0 else 8.0
    max_discount_cap = 15.0
    max_allowed_flash = max(0.0, max_discount_cap - existing_disc_pct)

    # POLICY CAP CHECK: Block flash offer if cart already exceeds or meets max_discount policy cap
    if max_allowed_flash <= 0:
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": "RECOVERY_INTERVENTION_BLOCKED_POLICY_CAP",
            "session_id": session_id,
            "existing_discount_percent": existing_disc_pct,
            "max_discount_cap": max_discount_cap,
            "max_discount_cap_enforced": True,
            "bounded_reason": "Cart items already at or above maximum 15% discount limit. Flash discount blocked to protect merchant margins."
        }
        session.audit_history.append(audit_entry)
        return {
            "status": "policy_cap_blocked",
            "session_id": session_id,
            "message": "Policy Cap Enforced: Items in cart are already at maximum allowed discount cap of 15%. Additional flash discounts blocked to protect merchant margins.",
            "audit_entry": audit_entry
        }

    flash_discount = min(5.0, max_allowed_flash)
    session.intervention_count += 1
    session.status = "intervened"
    session.flash_discount_percent = flash_discount

    extra_flash_savings = round(raw_total * (flash_discount / 100.0), 2)
    new_total = round(raw_total - extra_flash_savings, 2)
    new_total_savings = round(savings + extra_flash_savings, 2)
    total_combined_discount_pct = round(existing_disc_pct + flash_discount, 2)

    intervention_message = (
        f"Hey there! We noticed you left ₹{savings} in savings in your cart for your {session.user_goal} setup!\n\n"
        f"To help you achieve your fitness goals today, we've applied an **Exclusive {flash_discount}% Extra Flash Discount** to your cart.\n\n"
        f"• Original Cart Value: ₹{raw_total}\n"
        f"• Flash Discount Special:₹{new_total} (You Save a Total of **₹{new_total_savings}**!)\n\n"
        f"Would you like to complete your order with this limited-time flash offer?"
    )

    audit_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": "RECOVERY_INTERVENTION_SENT",
        "session_id": session_id,
        "intervention_count": session.intervention_count,
        "stopping_rule_limit": 1,
        "flash_discount_applied": flash_discount,
        "total_combined_discount_percent": total_combined_discount_pct,
        "max_discount_cap_enforced": True,
        "additional_discount_inr": extra_flash_savings,
        "new_cart_total_inr": new_total,
        "compliant_escalation": True
    }
    session.audit_history.append(audit_entry)

    return {
        "status": "intervention_sent",
        "session_id": session_id,
        "message": intervention_message,
        "original_total": raw_total,
        "flash_discount_total": new_total,
        "total_savings": new_total_savings,
        "audit_entry": audit_entry
    }


def complete_recovery(session_id: str) -> dict:
    """
    Complete recovery payment, record measured money recovered, and store audit trail.
    """
    if session_id not in abandoned_sessions:
        return {
            "status": "error",
            "message": "Session not found."
        }

    session = abandoned_sessions[session_id]
    raw_total, orig_total, savings = session.get_totals()
    
    if session.flash_discount_percent > 0:
        extra_discount = round(raw_total * (session.flash_discount_percent / 100.0), 2)
        recovered_amount = round(raw_total - extra_discount, 2)
    else:
        recovered_amount = raw_total

    session.status = "recovered"
    session.recovered_amount = recovered_amount

    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "session_id": session_id,
        "recovered_amount_inr": recovered_amount,
        "items": [item["name"] for item in session.cart],
        "user_goal": session.user_goal,
        "audit_trail": session.audit_history
    }
    recovered_history.append(record)

    return {
        "status": "recovered_successfully",
        "session_id": session_id,
        "recovered_amount_inr": recovered_amount,
        "message": f"Success! Recovered ₹{recovered_amount} from abandoned cart session {session_id}.",
        "audit_trail": record
    }


def get_recovery_analytics() -> dict:
    """
    Calculate batch analytics: total abandoned, total recovered revenue, conversion rate.
    """
    total_sessions = len(abandoned_sessions)
    recovered_sessions = [s for s in abandoned_sessions.values() if s.status == "recovered"]
    total_recovered_revenue = sum(s.recovered_amount for s in recovered_sessions)
    intervened_sessions = [s for s in abandoned_sessions.values() if s.intervention_count > 0]

    conversion_rate = round((len(recovered_sessions) / total_sessions * 100), 2) if total_sessions > 0 else 0.0

    return {
        "total_abandoned_carts": total_sessions,
        "total_interventions_sent": len(intervened_sessions),
        "total_carts_recovered": len(recovered_sessions),
        "total_revenue_recovered_inr": round(total_recovered_revenue, 2),
        "recovery_conversion_rate_percent": conversion_rate,
        "audit_logs": [s.audit_history for s in abandoned_sessions.values()]
    }
