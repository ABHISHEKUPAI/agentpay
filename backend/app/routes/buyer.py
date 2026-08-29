from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.buyer_agent import extract_shopping_intent
from app.services.conversation import get_conversation
from app.services.shopping_service import build_recommendation


router = APIRouter(
    prefix="/buyer",
    tags=["Buyer Agent"]
)


# =========================================================
# Request Models
# =========================================================

class BuyerRequest(BaseModel):
    message: str


class BuyerChatRequest(BaseModel):
    conversation_id: str
    message: str


# =========================================================
# Database Dependency
# =========================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================================================
# POST /buyer/intent
# =========================================================

@router.post("/intent")
def extract_intent(
    request: BuyerRequest
):
    """
    Extract the user's shopping intent.
    """
    intent = extract_shopping_intent(
        request.message
    )
    return intent


# =========================================================
# POST /buyer/recommend
# =========================================================

@router.post("/recommend")
def recommend_products(
    request: BuyerRequest,
    db: Session = Depends(get_db)
):
    """
    Generate product recommendations across all available merchants.
    """
    # 1. Understand user
    intent = extract_shopping_intent(
        request.message
    )

    # 2. Ask for budget if missing
    if intent.budget is None:
        return {
            "status": "need_more_information",
            "message": "What is your maximum budget?"
        }

    # 3. Ask for experience level if missing
    if (
        intent.experience is None
        and intent.product_level is None
    ):
        return {
            "status": "need_more_information",
            "message": "Are you a beginner runner or an experienced/pro runner?"
        }

    # 4. Generate recommendations
    rec = build_recommendation(
        db=db,
        main_category=intent.main_category,
        related_categories=intent.related_categories,
        categories=intent.categories,
        budget=intent.budget,
        experience=intent.experience,
        product_level=intent.product_level
    )

    # 5. Return audit-ready result
    return {
        "status": rec["status"],
        "message": rec["message"],
        "intent": {
            "goal": intent.goal,
            "main_category": intent.main_category,
            "related_categories": intent.related_categories,
            "experience": intent.experience,
            "product_level": intent.product_level,
            "budget": intent.budget,
            "categories": intent.categories
        },
        "main_product": rec["main_product"],
        "cross_sells": rec["cross_sells"],
        "products": rec["products"],
        "total": rec["total"],
        "budget": intent.budget,
        "missing_categories": rec["missing_categories"],
        "checkout_gated": rec.get("checkout_gated", True)
    }


# =========================================================
# POST /buyer/chat
# =========================================================

@router.post("/chat")
def buyer_chat(
    request: BuyerChatRequest,
    db: Session = Depends(get_db)
):
    """
    Main conversational Buyer Agent.
    """
    # 1. Get conversation state
    state = get_conversation(
        request.conversation_id
    )

    # 2. Extract intent using previous state context
    intent = extract_shopping_intent(
        request.message,
        state.intent
    )

    # 3. Save updated intent
    state.intent = intent

    # 4. Ask for budget if missing
    if intent.budget is None:
        state.pending_question = "What is your maximum budget?"
        return {
            "status": "need_more_information",
            "conversation_id": request.conversation_id,
            "message": state.pending_question
        }

    # 5. Ask for experience level if missing
    if (
        intent.experience is None
        and intent.product_level is None
    ):
        state.pending_question = "Are you a beginner runner or an experienced/pro runner?"
        return {
            "status": "need_more_information",
            "conversation_id": request.conversation_id,
            "message": state.pending_question
        }

    # 6. Build recommendation
    rec = build_recommendation(
        db=db,
        main_category=intent.main_category,
        related_categories=intent.related_categories,
        categories=intent.categories,
        budget=intent.budget,
        experience=intent.experience,
        product_level=intent.product_level
    )

    # 7. Clear pending question
    state.pending_question = None

    # 8. Return complete recommendation
    return {
        "status": rec["status"],
        "conversation_id": request.conversation_id,
        "message": rec["message"],
        "intent": {
            "goal": intent.goal,
            "main_category": intent.main_category,
            "related_categories": intent.related_categories,
            "experience": intent.experience,
            "product_level": intent.product_level,
            "budget": intent.budget,
            "categories": intent.categories
        },
        "main_product": rec["main_product"],
        "cross_sells": rec["cross_sells"],
        "products": rec["products"],
        "total": rec["total"],
        "budget": intent.budget,
        "missing_categories": rec["missing_categories"],
        "checkout_gated": rec.get("checkout_gated", True)
    }
