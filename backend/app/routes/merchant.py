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


# =========================
# MERCHANT ANALYTICS & STATS
# =========================

@router.get("/merchant-analytics")
def get_merchant_analytics(
    db: Session = Depends(get_db)
):
    merchants = db.query(Merchant).all()
    products = db.query(Product).all()

    breakdown = []
    total_val = 0.0

    for m in merchants:
        m_products = [p for p in products if p.merchant_id == m.id]
        m_stock = sum(p.stock for p in m_products)
        m_value = sum(p.price * p.stock for p in m_products)
        total_val += m_value

        breakdown.append({
            "id": m.id,
            "name": m.name,
            "category": m.category,
            "min_margin": m.min_margin,
            "max_discount": m.max_discount,
            "product_count": len(m_products),
            "total_stock": m_stock,
            "catalog_value_inr": round(m_value, 2)
        })

    max_disc_cap = max([m.max_discount if m.max_discount <= 1.0 else m.max_discount / 100.0 for m in merchants], default=0.15) * 100
    min_margin_cap = min([m.min_margin if m.min_margin <= 1.0 else m.min_margin / 100.0 for m in merchants], default=0.80) * 100

    return {
        "merchant_count": len(merchants),
        "total_products": len(products),
        "total_catalog_value_inr": round(total_val, 2),
        "active_policy_caps": f"{int(max_disc_cap)}% Max Discount | Min Margin {int(min_margin_cap)}% Guaranteed",
        "merchant_breakdown": breakdown
    }