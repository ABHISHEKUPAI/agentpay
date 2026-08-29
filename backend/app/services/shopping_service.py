from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.models.product import Product
from app.models.merchant import Merchant


class RecommendedProduct(BaseModel):
    id: int
    merchant_id: int
    merchant_name: str
    name: str
    category: str
    price: float
    rating: float
    reason: str


def search_products(
    db: Session,
    category: str,
    max_price: float | None = None
) -> list[Product]:
    """
    Find all available in-stock products for a category
    across every merchant.
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


def build_recommendation(
    db: Session,
    main_category: str | None = None,
    related_categories: list[str] | None = None,
    categories: list[str] | None = None,
    budget: float | None = None,
    experience: str | None = None,
    product_level: str | None = None
):
    """
    Primary AI Buyer Agent Recommendation Logic.
    
    1. Main product:
       - Selected from main_category (or first category in categories).
       - MUST be in stock and price <= budget.
       - Maximizes budget utilization while considering product rating & user experience.
       
    2. Cross-sells:
       - Selected from related_categories across all available merchants.
       - Beginner: favors low-cost, practical, high-value options.
       - Experienced/Pro: favors premium, top-rated, performance options.
    """
    if related_categories is None:
        related_categories = []

    if categories is None:
        categories = []

    # Determine main category
    if not main_category:
        if categories:
            main_category = categories[0]
            related_categories = categories[1:]
        else:
            main_category = "running_shoes"

    # Ensure related categories don't duplicate main category
    related_categories = [c for c in related_categories if c != main_category]

    missing_categories = []

    # Pre-fetch merchants for quick name lookup
    merchants = {m.id: m.name for m in db.query(Merchant).all()}

    # Normalize experience
    exp_clean = (experience or "").lower().strip()
    is_pro = exp_clean in {"experienced", "pro", "professional"}
    is_beginner = exp_clean == "beginner"

    # =========================================================
    # 1. MAIN PRODUCT RECOMMENDATION
    # =========================================================

    main_candidates = search_products(
        db=db,
        category=main_category,
        max_price=budget
    )

    if not main_candidates:
        # Handle failure gracefully (Requirement 14 & Test E)
        return {
            "status": "no_products_found",
            "message": f"No suitable {main_category.replace('_', ' ')} were found within your ₹{int(budget) if budget else 0} budget.",
            "main_product": None,
            "cross_sells": [],
            "products": [],
            "total": 0.0,
            "budget": budget,
            "missing_categories": [main_category] + related_categories
        }

    # Score main candidates: prefer highest-priced suitable option within budget, using rating as quality signal
    def score_main_product(p: Product):
        price_ratio = (p.price / budget) if (budget and budget > 0) else 0.5
        rating = p.rating or 0.0
        attrs = (p.attributes or "").lower()

        if is_pro:
            pro_bonus = 15 if ("pro" in attrs or "experienced" in attrs or "carbon" in attrs) else 0
            return (price_ratio * 40) + (rating * 12) + pro_bonus
        elif is_beginner:
            return (price_ratio * 30) + (rating * 10)
        else:
            return (price_ratio * 35) + (rating * 10)

    main_candidates.sort(key=score_main_product, reverse=True)
    chosen_main = main_candidates[0]
    chosen_main_merchant = merchants.get(chosen_main.merchant_id, f"Merchant #{chosen_main.merchant_id}")

    exp_label = "experienced/pro" if is_pro else ("beginner" if is_beginner else "runner")
    main_reason = (
        f"You specified a ₹{int(budget) if budget else 0} budget. "
        f"The {chosen_main.name} from {chosen_main_merchant} at ₹{int(chosen_main.price)} is the top-suited "
        f"option within your budget limit with a rating of {chosen_main.rating}, making it a strong choice for a {exp_label}."
    )

    main_prod_dict = {
        "id": chosen_main.id,
        "merchant_id": chosen_main.merchant_id,
        "merchant_name": chosen_main_merchant,
        "name": chosen_main.name,
        "category": chosen_main.category,
        "price": chosen_main.price,
        "rating": chosen_main.rating,
        "selection_reason": main_reason
    }

    # =========================================================
    # 2. CROSS-SELL / UPSELL RECOMMENDATION
    # =========================================================

    cross_sells = []
    total = chosen_main.price

    for cat in related_categories:
        cat_candidates = search_products(db=db, category=cat)

        if not cat_candidates:
            missing_categories.append(cat)
            continue

        if is_beginner:
            # Beginner cross-sell: favor low cost, practical, good value
            cat_candidates.sort(key=lambda p: (p.price, -p.rating))
            chosen_cs = cat_candidates[0]
            cs_merchant = merchants.get(chosen_cs.merchant_id, f"Merchant #{chosen_cs.merchant_id}")
            cs_reason = (
                f"These {chosen_cs.name} (₹{int(chosen_cs.price)} from {cs_merchant}) are a practical, low-cost "
                f"addition that keeps your additional spend low while starting out."
            )
        elif is_pro:
            # Pro cross-sell: favor top rating, premium attributes, higher quality
            def score_pro_cs(p: Product):
                attrs = (p.attributes or "").lower()
                pro_bonus = 10 if ("pro" in attrs or "experienced" in attrs or "compression" in attrs) else 0
                return (p.rating * 15) + (p.price * 0.005) + pro_bonus

            cat_candidates.sort(key=score_pro_cs, reverse=True)
            chosen_cs = cat_candidates[0]
            cs_merchant = merchants.get(chosen_cs.merchant_id, f"Merchant #{chosen_cs.merchant_id}")
            cs_reason = (
                f"These {chosen_cs.name} (₹{int(chosen_cs.price)} from {cs_merchant}) offer high performance "
                f"with a {chosen_cs.rating} rating to complement your pro running setup."
            )
        else:
            # Standard cross-sell
            cat_candidates.sort(key=lambda p: -p.rating)
            chosen_cs = cat_candidates[0]
            cs_merchant = merchants.get(chosen_cs.merchant_id, f"Merchant #{chosen_cs.merchant_id}")
            cs_reason = (
                f"These {chosen_cs.name} (₹{int(chosen_cs.price)} from {cs_merchant}) have a strong rating of "
                f"{chosen_cs.rating} and complement your purchase."
            )

        cross_sells.append({
            "id": chosen_cs.id,
            "merchant_id": chosen_cs.merchant_id,
            "merchant_name": cs_merchant,
            "name": chosen_cs.name,
            "category": chosen_cs.category,
            "price": chosen_cs.price,
            "rating": chosen_cs.rating,
            "cross_sell_reason": cs_reason
        })

        total += chosen_cs.price

    # Flattened list for backwards compatibility
    all_products = [
        {
            "id": chosen_main.id,
            "merchant_id": chosen_main.merchant_id,
            "merchant_name": chosen_main_merchant,
            "name": chosen_main.name,
            "category": chosen_main.category,
            "price": chosen_main.price,
            "rating": chosen_main.rating
        }
    ] + [
        {
            "id": cs["id"],
            "merchant_id": cs["merchant_id"],
            "merchant_name": cs["merchant_name"],
            "name": cs["name"],
            "category": cs["category"],
            "price": cs["price"],
            "rating": cs["rating"]
        }
        for cs in cross_sells
    ]

    # Summary text
    summary_message = (
        f"I've selected the {chosen_main.name} (₹{int(chosen_main.price)} from {chosen_main_merchant}) "
        f"as your main product within your ₹{int(budget) if budget else 0} budget. "
    )
    if cross_sells:
        cs_names = ", ".join([f"{cs['name']} (₹{int(cs['price'])})" for cs in cross_sells])
        summary_message += f"I also recommend these complementary items: {cs_names}. "

    summary_message += f"Total: ₹{int(total)}. Would you like to proceed to checkout?"

    return {
        "status": "complete",
        "message": summary_message,
        "main_product": main_prod_dict,
        "cross_sells": cross_sells,
        "products": all_products,
        "total": total,
        "budget": budget,
        "missing_categories": missing_categories,
        "checkout_gated": True
    }


if __name__ == "__main__":
    print("Shopping service loaded")
