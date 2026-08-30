from fastapi import APIRouter
from pydantic import BaseModel

from app.services.recovery_agent import (
    abandoned_sessions,
    register_abandoned_cart,
    trigger_recovery_intervention,
    complete_recovery,
    get_recovery_analytics
)

router = APIRouter(
    prefix="/recovery",
    tags=["AI Revenue Recovery Agent"]
)


class AbandonedCartRequest(BaseModel):
    session_id: str
    cart: list[dict]
    user_goal: str = "running setup"


class InterveneRequest(BaseModel):
    session_id: str


@router.post("/register-abandoned")
def register_abandoned(request: AbandonedCartRequest):
    """
    Register an abandoned cart session.
    """
    session = register_abandoned_cart(
        session_id=request.session_id,
        cart=request.cart,
        user_goal=request.user_goal
    )
    raw_total, orig_total, savings = session.get_totals()
    return {
        "status": "registered",
        "session_id": session.session_id,
        "potential_revenue": raw_total,
        "savings_left_behind": savings,
        "message": f"Abandoned cart registered for session {session.session_id}."
    }


@router.get("/abandoned-carts")
def list_abandoned_carts():
    """
    List all detected abandoned cart sessions.
    """
    result = []
    for sid, s in abandoned_sessions.items():
        raw_total, orig_total, savings = s.get_totals()
        result.append({
            "session_id": s.session_id,
            "status": s.status,
            "user_goal": s.user_goal,
            "cart_items_count": len(s.cart),
            "potential_revenue_inr": raw_total,
            "savings_left_behind_inr": savings,
            "intervention_count": s.intervention_count,
            "created_at": s.created_at
        })
    return result


@router.post("/intervene")
def intervene_abandoned_cart(request: InterveneRequest):
    """
    Execute bounded recovery intervention workflow. Enforces stopping rule (max 1 intervention).
    """
    res = trigger_recovery_intervention(request.session_id)
    return res


@router.post("/complete")
def complete_recovered_cart(request: InterveneRequest):
    """
    Complete recovery payment, record measured money recovered, and output audit trail.
    """
    res = complete_recovery(request.session_id)
    return res


@router.get("/analytics")
def get_analytics():
    """
    Return batch recovery metrics, money recovered, stopping rules, and full audit logs.
    """
    return get_recovery_analytics()
