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
    Enforces Stopping Rule: Max 1 intervention per session.
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

    session.intervention_count += 1
    session.status = "intervened"
    session.flash_discount_percent = 5.0  # 5% bounded flash recovery incentive

    raw_total, orig_total, savings = session.get_totals()
    extra_flash_savings = round(raw_total * 0.05, 2)
    new_total = round(raw_total - extra_flash_savings, 2)
    new_total_savings = round(savings + extra_flash_savings, 2)

    intervention_message = (
        f"🏃 Hey there! We noticed you left ₹{savings} in savings in your cart for your {session.user_goal} setup!\n\n"
        f"To help you achieve your fitness goals today, we've applied an **Exclusive 5% Extra Flash Discount** to your cart.\n\n"
        f"• Original Cart Value: ₹{raw_total}\n"
        f"• Flash Discount Special: **₹{new_total}** (You Save a Total of **₹{new_total_savings}**!)\n\n"
        f"⚡ Would you like to complete your order with this limited-time flash offer?"
    )

    audit_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": "RECOVERY_INTERVENTION_SENT",
        "session_id": session_id,
        "intervention_count": session.intervention_count,
        "stopping_rule_limit": 1,
        "flash_discount_applied": 5.0,
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
