from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.buyer_agent import extract_shopping_intent
from app.services.conversation import get_conversation
from app.services.shopping_service import (
    build_recommendation,
    build_merchant_baskets,
    choose_best_merchant_basket
)


router = APIRouter(
    prefix="/buyer",
    tags=["Buyer Agent"]
)


class BuyerRequest(BaseModel):
    message: str


class BuyerChatRequest(BaseModel):
    conversation_id: str
    message: str


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post("/intent")
def extract_intent(
    request: BuyerRequest
):
    intent = extract_shopping_intent(
        request.message
    )

    return intent


@router.post("/recommend")
def recommend_products(
    request: BuyerRequest,
    db: Session = Depends(get_db)
):
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

    # 3. Best individual products
    products, total = build_recommendation(
        db=db,
        categories=intent.categories,
        budget=intent.budget,
        experience=intent.experience
    )

    # 4. Best complete basket from each merchant
    merchant_baskets = build_merchant_baskets(
        db=db,
        categories=intent.categories,
        budget=intent.budget
    )

    # 5. Best merchant
    best_merchant = choose_best_merchant_basket(
        merchant_baskets
    )

    return {
        "intent": intent,

        "best_individual_products": [
            {
                "id": product.id,
                "merchant_id": product.merchant_id,
                "name": product.name,
                "category": product.category,
                "price": product.price,
                "rating": product.rating
            }
            for product in products
        ],

        "individual_total": total,

        "merchant_baskets": [
            {
                "merchant_id": basket["merchant_id"],
                "merchant": basket["merchant"],

                "products": [
                    {
                        "id": product.id,
                        "name": product.name,
                        "category": product.category,
                        "price": product.price,
                        "rating": product.rating
                    }
                    for product in basket["products"]
                ],

                "total": basket["total"],
                "within_budget": basket["within_budget"]
            }
            for basket in merchant_baskets
        ],

        "best_merchant": (
            {
                "merchant_id": best_merchant["merchant_id"],
                "merchant": best_merchant["merchant"],
                "total": best_merchant["total"]
            }
            if best_merchant
            else None
        ),

        "budget": intent.budget
    }


@router.post("/chat")
def buyer_chat(
    request: BuyerChatRequest,
    db: Session = Depends(get_db)
):
    # Get conversation state
    state = get_conversation(
        request.conversation_id
    )

    # Extract intent from current message
    intent = extract_shopping_intent(
        request.message,
        state.intent
    )

    # Save intent in conversation state
    state.intent = intent

    # If budget is missing, ask user
    if intent.budget is None:

        state.pending_question = (
            "What is your maximum budget?"
        )

        return {
            "status": "need_more_information",
            "conversation_id": request.conversation_id,
            "message": state.pending_question
        }

    # Build product recommendation
    products, total = build_recommendation(
        db=db,
        categories=intent.categories,
        budget=intent.budget,
        experience=intent.experience
    )

    # Build merchant baskets
    merchant_baskets = build_merchant_baskets(
        db=db,
        categories=intent.categories,
        budget=intent.budget
    )

    # Select best merchant
    best_merchant = choose_best_merchant_basket(
        merchant_baskets
    )

    return {
        "status": "complete",
        "conversation_id": request.conversation_id,

        "intent": {
            "goal": intent.goal,
            "experience": intent.experience,
            "budget": intent.budget,
            "categories": intent.categories
        },

        "products": [
            {
                "id": product.id,
                "merchant_id": product.merchant_id,
                "name": product.name,
                "category": product.category,
                "price": product.price,
                "rating": product.rating
            }
            for product in products
        ],

        "total": total,

        "best_merchant": (
            {
                "merchant_id": best_merchant["merchant_id"],
                "merchant": best_merchant["merchant"],
                "total": best_merchant["total"]
            }
            if best_merchant
            else None
        ),

        "budget": intent.budget
    }