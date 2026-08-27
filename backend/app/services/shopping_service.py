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
    """
    Find products in a category that are in stock.
    Optionally restrict by maximum price.
    """

    query = db.query(Product).filter(
        Product.category == category,
        Product.stock > 0
    )

    if max_price is not None:
        query = query.filter(
            Product.price <= max_price
        )

    return query.all()


def score_product(
    product: Product,
    experience: str | None = None,
    budget: float | None = None
):
    """
    Give a product a score based on:
    - rating
    - experience match
    - price/value
    """

    score = 0.0

    # -----------------------------------------
    # 1. Rating score
    # -----------------------------------------

    score += product.rating * 10

    # -----------------------------------------
    # 2. Experience match
    # -----------------------------------------

    if experience:
        attributes = (
            product.attributes or ""
        ).lower()

        if experience.lower() in attributes:
            score += 20

    # -----------------------------------------
    # 3. Price/value score
    # -----------------------------------------

    if budget and budget > 0:

        price_ratio = product.price / budget

        if price_ratio <= 0.5:
            score += 10

        elif price_ratio <= 0.75:
            score += 7

        elif price_ratio <= 1.0:
            score += 4

    return score


def build_recommendation(
    db: Session,
    categories: list[str],
    budget: float,
    experience: str | None = None
):
    """
    Find the best product for each required category.
    Products are ranked using the scoring system.
    """

    selected_products = []
    total = 0.0

    if not categories:
        return selected_products, total

    # Give each category a reasonable portion
    # of the total budget.
    category_budget = budget / len(categories)

    for category in categories:

        products = search_products(
            db=db,
            category=category,
            max_price=budget
        )

        if not products:
            continue

        # -----------------------------------------
        # Score every product
        # -----------------------------------------

        scored_products = []

        for product in products:

            score = score_product(
                product=product,
                experience=experience,
                budget=category_budget
            )

            scored_products.append(
                (product, score)
            )

        # -----------------------------------------
        # Highest scoring products first
        # -----------------------------------------

        scored_products.sort(
            key=lambda item: item[1],
            reverse=True
        )

        # -----------------------------------------
        # Choose the highest scoring product
        # that keeps the entire basket within budget.
        # -----------------------------------------

        chosen = None

        for product, score in scored_products:

            if total + product.price <= budget:
                chosen = product
                break

        if chosen:

            selected_products.append(
                chosen
            )

            total += chosen.price

    return selected_products, total


def build_merchant_baskets(
    db: Session,
    categories: list[str],
    budget: float
):
    """
    Build a complete shopping basket for every merchant.
    """

    merchants = db.query(Merchant).all()

    baskets = []

    for merchant in merchants:

        products = []

        for category in categories:

            category_products = db.query(Product).filter(
                Product.merchant_id == merchant.id,
                Product.category == category,
                Product.stock > 0
            ).all()

            if not category_products:
                continue

            # Choose the highest-rated product
            # from this merchant/category.
            product = max(
                category_products,
                key=lambda p: p.rating
            )

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
    """
    Choose the cheapest complete basket
    that fits within the user's budget.
    """

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