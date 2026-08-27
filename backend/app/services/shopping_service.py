from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.models.product import Product
from app.models.merchant import Merchant
                  
class RecommendedProduct(BaseModel):
    product_id: int
    merchant_id: int
    name: str
    category: str
    price: float
    rating: float

def search_products(
    db: Session,
    category: str,
    max_price: float | None = None
):
    query = db.query(Product).filter(
        Product.category == category,
        Product.stock > 0
    )

    if max_price is not None:
        query = query.filter(
            Product.price <= max_price
        )

    return query.all()

class RecommendedProduct(BaseModel):
    product_id: int
    merchant_id: int
    name: str
    category: str
    price: float
    rating: float


def build_recommendation(
    db: Session,
    categories: list[str],
    budget: float
):
    selected_products = []
    total = 0

    for category in categories:

        products = search_products(
            db=db,
            category=category
        )

        if not products:
            continue

        # Sort cheapest first
        products = sorted(
            products,
            key=lambda product: product.price
        )

        # Pick the cheapest product that
        # keeps the basket within budget
        chosen = None

        for product in products:

            if total + product.price <= budget:
                chosen = product
                break

        if chosen:
            selected_products.append(chosen)
            total += chosen.price

    return selected_products, total

def build_merchant_baskets(
    db: Session,
    categories: list[str],
    budget: float
):
    merchants = db.query(Merchant).all()

    baskets = []

    for merchant in merchants:

        products = []

        for category in categories:

            product = db.query(Product).filter(
                Product.merchant_id == merchant.id,
                Product.category == category,
                Product.stock > 0
            ).order_by(
                Product.price.asc()
            ).first()

            if product:
                products.append(product)

        total = sum(
            product.price
            for product in products
        )

        baskets.append({
            "merchant_id": merchant.id,
            "merchant": merchant.name,
            "products": products,
            "total": total,
            "within_budget": total <= budget
        })

    return baskets

def choose_best_merchant_basket(
    merchant_baskets
):
    valid_baskets = [
        basket
        for basket in merchant_baskets
        if basket["within_budget"]
    ]

    if not valid_baskets:
        return None

    return min(
        valid_baskets,
        key=lambda basket: basket["total"]
    )

if __name__ == "__main__":
    print("Shopping service loaded")