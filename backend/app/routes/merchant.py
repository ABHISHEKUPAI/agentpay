from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import SessionLocal
from app.models.merchant import Merchant
from app.models.product import Product


router = APIRouter(
    prefix="/ai",
    tags=["AI Merchant API"]
)


# =========================
# DATABASE DEPENDENCY
# =========================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# =========================
# REQUEST MODELS
# =========================

class QuoteRequest(BaseModel):
    product_ids: list[int]


# =========================
# CATALOG
# =========================

@router.get("/catalog")
def get_catalog(
    db: Session = Depends(get_db)
):

    merchants = db.query(Merchant).all()

    result = []

    for merchant in merchants:

        products = db.query(Product).filter(
            Product.merchant_id == merchant.id
        ).all()

        result.append({
            "merchant": merchant.name,
            "category": merchant.category,
            "currency": "INR",

            "policies": {
                "minimum_margin": merchant.min_margin,
                "maximum_discount": merchant.max_discount
            },

            "products": [
                {
                    "id": product.id,
                    "name": product.name,
                    "category": product.category,
                    "price": product.price,
                    "stock": product.stock,
                    "rating": product.rating,
                    "attributes": product.attributes
                }
                for product in products
            ]
        })

    return result


# =========================
# PRODUCT SEARCH
# =========================

@router.get("/products")
def get_products(
    category: str | None = None,
    max_price: float | None = None,
    db: Session = Depends(get_db)
):

    query = db.query(Product)

    if category:
        query = query.filter(
            Product.category == category
        )

    if max_price:
        query = query.filter(
            Product.price <= max_price
        )

    products = query.all()

    return [
        {
            "id": product.id,
            "merchant_id": product.merchant_id,
            "name": product.name,
            "category": product.category,
            "price": product.price,
            "stock": product.stock,
            "rating": product.rating,
            "attributes": product.attributes
        }
        for product in products
    ]


# =========================
# INVENTORY
# =========================

@router.get("/inventory")
def get_inventory(
    db: Session = Depends(get_db)
):

    products = db.query(Product).all()

    return [
        {
            "product_id": product.id,
            "merchant_id": product.merchant_id,
            "product": product.name,
            "stock": product.stock,
            "available": product.stock > 0
        }
        for product in products
    ]


# =========================
# QUOTE
# =========================

@router.post("/quote")
def create_quote(
    request: QuoteRequest,
    db: Session = Depends(get_db)
):

    products = db.query(Product).filter(
        Product.id.in_(request.product_ids)
    ).all()

    if len(products) != len(request.product_ids):
        raise HTTPException(
            status_code=404,
            detail="One or more products not found"
        )

    total = sum(
        product.price
        for product in products
    )

    return {
        "items": [
            {
                "product_id": product.id,
                "name": product.name,
                "price": product.price
            }
            for product in products
        ],

        "subtotal": total,
        "currency": "INR"
    }

@router.get("/products/{product_id}")
def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return {
        "id": product.id,
        "merchant_id": product.merchant_id,
        "name": product.name,
        "category": product.category,
        "price": product.price,
        "stock": product.stock,
        "rating": product.rating,
        "attributes": product.attributes
    }