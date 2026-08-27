from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.buyer_agent import extract_shopping_intent
from app.services.shopping_service import (
    build_recommendation,
    build_merchant_baskets
)
router = APIRouter(
    prefix="/buyer",
    tags=["Buyer Agent"]
)


class BuyerRequest(BaseModel):
    message: str

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

@router.post("/intent")
def extract_intent(request: BuyerRequest):

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
        budget=intent.budget
    )

    # 4. Best complete basket from each merchant
    merchant_baskets = build_merchant_baskets(
        db=db,
        categories=intent.categories,
        budget=intent.budget
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

        "budget": intent.budget
    }