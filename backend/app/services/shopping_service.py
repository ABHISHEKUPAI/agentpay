from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.models.product import Product
from app.models.merchant import Merchant


class RecommendedProduct(BaseModel):
    id: int
    merchant_id: int
    merchant_name: str
    name: str
    category: str
    price: float
    original_price: float
    discount_percent: float
    savings: float
    rating: float
    attributes: Optional[str] = None
    reason: str


def calculate_category_stats(db: Session, category: str) -> dict:
    """
    Deterministic Python calculation of category price statistics across all in-stock products.
    """
    products = db.query(Product).filter(
        Product.category == category,
        Product.stock > 0
    ).all()

    if not products:
        return {
            "total_in_stock": 0,
            "min_price": 0.0,
            "max_price": 0.0,
            "avg_price": 0.0,
            "products": []
        }

    prices = [p.price for p in products]
    min_p = min(prices)
    max_p = max(prices)
    avg_p = sum(prices) / len(prices)

    return {
        "total_in_stock": len(products),
        "min_price": round(min_p, 2),
        "max_price": round(max_p, 2),
        "avg_price": round(avg_p, 2),
        "products": products
    }


def search_products(
    db: Session,
    category: str,
    max_price: float | None = None
) -> list[Product]:
    """
    Find all available in-stock products for a category across all merchants.
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


def format_product_dict(p: Product, merchant_map: dict, sport: str | None = None, experience: str | None = None) -> dict:
    m = merchant_map.get(p.merchant_id)
    m_name = m.name if m else f"Merchant #{p.merchant_id}"
    disc_pct = m.max_discount if (m and m.max_discount) else 15.0
    orig_price = round(p.price / (1.0 - (disc_pct / 100.0)), 2)
    savings = round(orig_price - p.price, 2)
    
    sp = (sport or "sports").capitalize()
    exp = (experience or "beginner").lower()

    if exp in ["experienced", "pro", "competitive"]:
        reason = f"High-performance {sp} selection ({p.rating}★ rating) engineered with durable materials for competitive match play."
    elif exp in ["intermediate", "regular"]:
        reason = f"Balanced {sp} choice ({p.rating}★ rating) delivering solid responsiveness and stability for regular sessions."
    else:
        reason = f"Comfortable value choice ({p.rating}★ rating) providing reliable build quality for getting started in {sp}."

    return {
        "id": p.id,
        "merchant_id": p.merchant_id,
        "merchant_name": m_name,
        "name": p.name,
        "category": p.category,
        "price": p.price,
        "original_price": orig_price,
        "discount_percent": disc_pct,
        "savings": savings,
        "rating": p.rating,
        "attributes": p.attributes,
        "reason": reason
    }


def get_personalized_recommendation_reason(
    product: Product,
    sport: str | None = None,
    experience: str | None = None
) -> str:
    cat = (product.category or "").lower()
    sp = (sport or "sports").capitalize()

    if "grip" in cat:
        return f"Essential for racquet handle control in {sp}. Absorbs sweat and prevents slipping during long sessions."
    elif "shuttlecock" in cat:
        return f"Tournament-tested shuttlecocks delivering consistent flight trajectory and durability."
    elif "socks" in cat:
        return f"Cushioned socks with moisture-wicking fabric; helps reduce friction and keeps feet comfortable on longer runs."
    elif "shin_guards" in cat or "pads" in cat or "gloves" in cat:
        return f"Impact-absorbing protective gear designed to cushion strikes and safeguard against injury."
    elif "balls" in cat:
        return f"High-density felt balls providing consistent bounce and spin durability."
    elif "goggles" in cat or "swimwear" in cat or "cap" in cat:
        return f"Anti-fog, UV-protected gear providing clear visibility and chlorine resistance."
    elif "shirt" in cat or "jersey" in cat:
        return f"Lightweight moisture-wicking fabric that regulates temperature and prevents chafing."
    elif "shorts" in cat:
        return f"Flexible ergonomic shorts designed for unrestricted motion and breathability."
    else:
        return f"Useful complement rated {product.rating}★ to complete your performance setup."


def build_primary_recommendations(
    db: Session,
    intent,
    preference: str | None = None
) -> dict:
    """
    Deterministic calculation & selection of primary product options adhering strictly to 
    experience levels, budget tiers (below min, min<b<avg, b>=avg), and professional prioritization.
    - CASE 1: Beginner/Intermediate < min_price (UNTOUCHED)
    - CASE 2: Pro < min_price (UNTOUCHED)
    - CASE 3: Anyone with min_price <= budget < avg_price (UNTOUCHED)
    - CASE 4: Beginner/Intermediate with budget >= avg_price
    - CASE 5: Pro with budget >= avg_price
    """
    main_cat = intent.main_category or f"{intent.sport or 'running'}_shoes"
    merchant_map = {m.id: m for m in db.query(Merchant).all()}
    
    stats = calculate_category_stats(db, main_cat)
    if stats["total_in_stock"] == 0:
        sp_display = (intent.sport or "sports").capitalize()
        return {
            "status": "no_products_found",
            "message": f"Sorry, no products are currently available in stock for '{main_cat.replace('_', ' ')}' in {sp_display}.",
            "options": []
        }

    all_in_stock = stats["products"]
    avg_price = stats["avg_price"]
    min_price = stats["min_price"]
    max_price = stats["max_price"]
    budget_val = intent.budget if (intent.budget and intent.budget > 0) else 5000.0
    exp_lower = (intent.experience or "beginner").lower()
    is_pro = exp_lower in ["pro", "professional", "experienced", "competitive"]

    # =========================================================
    # CASE 1 & CASE 2: BUDGET BELOW THE CHEAPEST PRODUCT (UNTOUCHED)
    # =========================================================
    if budget_val < min_price:
        budget_gap = round(min_price - budget_val, 2)
        cheapest_p = min(all_in_stock, key=lambda p: p.price)
        fmt_cheap = format_product_dict(cheapest_p, merchant_map, sport=intent.sport, experience=intent.experience)
        fmt_cheap["option_num"] = 1
        fmt_cheap["option_type"] = "entry_level"

        sp_str = (intent.sport or "sports").capitalize()
        lines = []

        if not is_pro:
            # CASE 1: Beginner / Intermediate below cheapest product (UNTOUCHED)
            lines.append(f"You're ₹{int(budget_gap)} short of the most affordable {sp_str} option currently available.")
            lines.append(
                f"Stretching your budget slightly to ₹{int(min_price)} gives you a reliable entry-level choice "
                f"with a {fmt_cheap['rating']}★ rating and the essentials needed for comfortable training:\n"
            )
            lines.append(f"• {fmt_cheap['name']} — ₹{int(fmt_cheap['price'])} ({fmt_cheap['rating']}★ from {fmt_cheap['merchant_name']})")
            lines.append(f"• Budget Gap: ₹{int(budget_gap)}")
            lines.append(f"• Reason: {fmt_cheap['reason']}\n")
            lines.append("Please select an action:")
            return {
                "status": "budget_stretch_required",
                "message": "\n".join(lines),
                "options": [fmt_cheap],
                "price_difference": budget_gap,
                "is_pro": False
            }
        else:
            # CASE 2: Professional below cheapest product (UNTOUCHED)
            highest_quality_p = max(all_in_stock, key=lambda p: (p.rating, p.price))
            fmt_high = format_product_dict(highest_quality_p, merchant_map, sport=intent.sport, experience=intent.experience)
            fmt_high["option_num"] = 2
            fmt_high["option_type"] = "pro_quality"

            lines.append(f"Your target budget of ₹{int(budget_val)} is below available {sp_str} inventory.")
            lines.append(f"For professional match play, here are the two relevant options available:\n")
            
            lines.append(f"Recommendation 1 (Accessible Entry) — {fmt_cheap['name']} — ₹{int(fmt_cheap['price'])} (from {fmt_cheap['merchant_name']})")
            lines.append(f"• Rating: {fmt_cheap['rating']}★ | Budget Gap: ₹{int(budget_gap)}")
            lines.append(f"• Features: Entry-level build for basic practice sessions.\n")

            options = [fmt_cheap]
            if fmt_high["id"] != fmt_cheap["id"]:
                fmt_high_gap = round(fmt_high["price"] - budget_val, 2)
                lines.append(f"Recommendation 2 (Pro Performance Tier) — {fmt_high['name']} — ₹{int(fmt_high['price'])}** (from {fmt_high['merchant_name']})")
                lines.append(f"• Rating: {fmt_high['rating']}★ | Attributes: {fmt_high['attributes'] or 'Pro Specifications'}")
                lines.append(f"• Pro Reasoning: As a competitive athlete, stretching to this tier gives you high-response cushioning, premium durability, and carbon/stability support required for match play.\n")
                options.append(fmt_high)

            lines.append("Please select an action:")

            return {
                "status": "budget_stretch_required",
                "message": "\n".join(lines),
                "options": options,
                "price_difference": budget_gap,
                "is_pro": True
            }

    # Filter candidate products within user budget
    candidates = [p for p in all_in_stock if p.price <= budget_val]
    if not candidates:
        candidates = [min(all_in_stock, key=lambda p: p.price)]

    # Preference-Aware Re-ranking if user provided explicit preference
    pref = (preference or intent.preference or "").lower()
    if pref == "rating":
        candidates.sort(key=lambda p: (-p.rating, -p.price))
    elif pref == "comfort":
        candidates.sort(key=lambda p: (0 if "comfort" in (p.attributes or "").lower() or "cushion" in (p.attributes or "").lower() else 1, -p.rating, -p.price))
    elif pref == "performance":
        candidates.sort(key=lambda p: (0 if "pro" in (p.attributes or "").lower() or "carbon" in (p.attributes or "").lower() or "willow" in (p.attributes or "").lower() else 1, -p.rating, -p.price))
    elif pref in ["price", "value", "cheapest"]:
        candidates.sort(key=lambda p: (p.price, -p.rating))
    elif pref == "durability":
        candidates.sort(key=lambda p: (0 if "durable" in (p.attributes or "").lower() or "fg" in (p.attributes or "").lower() else 1, -p.rating, -p.price))

    # =========================================================
    # CASE 3: ANYONE WITH BUDGET BETWEEN MIN PRICE AND AVG PRICE (UNTOUCHED)
    # =========================================================
    if budget_val < avg_price:
        opt1_p = min(candidates, key=lambda p: (abs(p.price - budget_val), -p.rating))
        candidates_opt2 = [p for p in candidates if p.id != opt1_p.id]
        if candidates_opt2:
            opt2_p = max(candidates_opt2, key=lambda p: (p.rating, p.price))
        else:
            opt2_p = opt1_p

        fmt1 = format_product_dict(opt2_p, merchant_map, sport=intent.sport, experience=intent.experience)
        fmt1["option_num"] = 1
        fmt1["option_type"] = "value_recommendation"

        fmt2 = format_product_dict(opt1_p, merchant_map, sport=intent.sport, experience=intent.experience)
        fmt2["option_num"] = 2
        fmt2["option_type"] = "best_within_budget"

        options_list = [fmt1]
        if fmt2["id"] != fmt1["id"]:
            options_list.append(fmt2)

        sp_str = (intent.sport or "sports").capitalize()
        lines = []
        lines.append(f"Top {sp_str} Primary Product Recommendations (Budget: ₹{int(budget_val)}):\n")

        lines.append(f"Best-Value Recommendation — {fmt1['name']} — ₹{int(fmt1['price'])} (from {fmt1['merchant_name']})")
        lines.append(f"• Rating: {fmt1['rating']}★ \n  key features of the product: {fmt1['attributes'] or 'Comfort & Value'}")
        lines.append(f"• this product : Provides strong value and reliable quality without unnecessarily consuming your entire ₹{int(budget_val)} budget, leaving room for useful sports gear.\n\n\n")

        if len(options_list) > 1:
            lines.append(f"Best Product Within Budget — {fmt2['name']} — ₹{int(fmt2['price'])} (from {fmt2['merchant_name']})")
            lines.append(f"• Rating: {fmt2['rating']}★ \n Attributes: {fmt2['attributes'] or 'High Quality'}")
            lines.append(f"• The highest-quality suitable product available within your ₹{int(budget_val)} budget.\n")

        lines.append("Please select an action:")

        return {
            "status": "primary_options",
            "message": "\n".join(lines),
            "options": options_list,
            "avg_price": avg_price,
            "min_price": min_price,
            "max_price": max_price
        }

    # =========================================================
    # CASE 5: PROFESSIONAL USER WITH BUDGET >= AVG PRICE
    # =========================================================
    if is_pro:
        # Best product overall in category (highest rating/price across all in-stock)
        best_overall_p = max(all_in_stock, key=lambda p: (p.rating, p.price))
        # Best product within user budget
        best_within_p = max(candidates, key=lambda p: (p.rating, p.price))

        fmt_within = format_product_dict(best_within_p, merchant_map, sport=intent.sport, experience=intent.experience)
        fmt_within["option_num"] = 2
        fmt_within["option_type"] = "pro_within_budget"

        options_list = [fmt_within]

        fmt_overall = None
        # Only show Recommendation 1 (Best Product Overall) if budget < max_price
        if budget_val < max_price and best_overall_p.id != best_within_p.id:
            fmt_overall = format_product_dict(best_overall_p, merchant_map, sport=intent.sport, experience=intent.experience)
            fmt_overall["option_num"] = 1
            fmt_overall["option_type"] = "pro_top_stretch"
            options_list = [fmt_overall, fmt_within]

        sp_str = (intent.sport or "sports").capitalize()
        lines = []
        lines.append(f"Top {sp_str} Performance Recommendations for Professional/Competitive Play (Budget: ₹{int(budget_val)}):\n")

        if fmt_overall:
            stretch_gap = round(best_overall_p.price - budget_val, 2)
            lines.append(f"Recommendation 1 (Top Pro Product Stretch) — {fmt_overall['name']} — ₹{int(fmt_overall['price'])} (from {fmt_overall['merchant_name']})")
            lines.append(f"• Rating: {fmt_overall['rating']}★ | Attributes: {fmt_overall['attributes'] or 'Pro Specifications'}")
            lines.append(f"• Stretch Prompt: This is the highest-rated overall pro product available. Can you stretch your budget by ₹{int(stretch_gap)} to get this top-tier match setup?\n")

        lines.append(f"Recommendation 2 (Best Pro Product Within Budget) — {fmt_within['name']} — ₹{int(fmt_within['price'])} (from {fmt_within['merchant_name']})")
        lines.append(f"• Rating: {fmt_within['rating']}★ | Attributes: {fmt_within['attributes'] or 'Pro Grade'}")
        lines.append(f"• Pro Reasoning: The highest-rated pro product available within your ₹{int(budget_val)} budget for competitive play.\n")

        lines.append("Please select an action:")

        return {
            "status": "primary_options",
            "message": "\n".join(lines),
            "options": options_list,
            "avg_price": avg_price,
            "min_price": min_price,
            "max_price": max_price
        }

    # =========================================================
    # CASE 4: BEGINNER / INTERMEDIATE WITH BUDGET >= AVG PRICE
    # =========================================================
    # Recommendation 2: Best Ranked & Highest Priced Product Within Budget
    opt2_p = max(candidates, key=lambda p: (p.price, p.rating))

    # Recommendation 1: Best Value Product based on (budget_val - sub_product_total)
    comp_res = _preview_complementary_total(db, intent, is_pro=False)
    sub_product_total = comp_res["sub_product_total"]
    target_main_price = max(min_price, budget_val - sub_product_total)

    remaining_candidates = [p for p in candidates if p.id != opt2_p.id]
    if remaining_candidates:
        opt1_p = min(remaining_candidates, key=lambda p: (abs(p.price - target_main_price), -p.rating))
    else:
        opt1_p = opt2_p

    fmt1 = format_product_dict(opt1_p, merchant_map, sport=intent.sport, experience=intent.experience)
    fmt1["option_num"] = 1
    fmt1["option_type"] = "value_recommendation"

    fmt2 = format_product_dict(opt2_p, merchant_map, sport=intent.sport, experience=intent.experience)
    fmt2["option_num"] = 2
    fmt2["option_type"] = "highest_priced_within_budget"

    options_list = [fmt1]
    if fmt2["id"] != fmt1["id"]:
        options_list.append(fmt2)

    sp_str = (intent.sport or "sports").capitalize()
    lines = []
    lines.append(f"Top {sp_str} Recommendations (Budget: ₹{int(budget_val)}):\n")

    lines.append(f"Recommendation 1 (Best-Value Product) — {fmt1['name']} — ₹{int(fmt1['price'])} (from {fmt1['merchant_name']})")
    lines.append(f"• Rating: {fmt1['rating']}★ | Attributes: {fmt1['attributes'] or 'Comfort & Value'}")
    lines.append(f"• Best Value Reasoning: Delivers solid performance without consuming your full budget.\n")

    if len(options_list) > 1:
        lines.append(f"Recommendation 2 (Best Ranked & Highest Priced Within Budget) — {fmt2['name']} — ₹{int(fmt2['price'])} (from {fmt2['merchant_name']})")
        lines.append(f"• Rating: {fmt2['rating']}★ | Attributes: {fmt2['attributes'] or 'Premium Build'}")
        lines.append(f"• High Rank Reasoning: The highest-priced and top-rated primary product available within your ₹{int(budget_val)} budget.\n")

    lines.append("Please select an action:")

    return {
        "status": "primary_options",
        "message": "\n".join(lines),
        "options": options_list,
        "avg_price": avg_price,
        "min_price": min_price,
        "max_price": max_price
    }


def _preview_complementary_total(db: Session, intent, is_pro: bool = False) -> dict:
    """
    Helper to calculate sub_product_total for sports gear without adding to cart.
    """
    related_cats = intent.related_categories or []
    sub_total = 0.0
    items_count = 0

    for cat in related_cats:
        items = search_products(db=db, category=cat)
        if items:
            if is_pro:
                items.sort(key=lambda p: (-p.rating, -p.price))
            else:
                items.sort(key=lambda p: (p.price, -p.rating))
            sub_total += items[0].price
            items_count += 1

    return {"sub_product_total": round(sub_total, 2), "items_count": items_count}


def build_complementary_recommendations(
    db: Session,
    selected_main: dict,
    intent,
    remaining_budget: float,
    selected_path: str = "option1"
) -> dict:
    """
    Identifies dynamic cross-merchant add-on recommendations matching sport, budget, and experience level:
    - CASE 1 (Beginner < min_price): cheapest useful products + highest rating (UNTOUCHED).
    - CASE 2 (Pro < min_price): highest rating + price (UNTOUCHED).
    - CASE 3 (min_price <= budget < avg_price): highest rating + price (UNTOUCHED).
    - CASE 4 (Beginner/Intermediate & budget >= avg_price):
      * If Recommendation 1 (Best Value) selected: highest-priced sub-category products (-price, -rating) so total exceeds budget.
      * If Recommendation 2 selected: highest-ranked sub-category products (-rating, -price).
    - CASE 5 (Pro & budget >= avg_price): rating main filter, then price (-rating, -price).
    """
    merchant_map = {m.id: m for m in db.query(Merchant).all()}
    related_cats = intent.related_categories or []
    exp_lower = (intent.experience or "beginner").lower()
    is_pro = exp_lower in ["pro", "professional", "experienced", "competitive"]
    budget_val = intent.budget if (intent.budget and intent.budget > 0) else 5000.0

    main_cat = intent.main_category or f"{intent.sport or 'running'}_shoes"
    stats = calculate_category_stats(db, main_cat)
    min_price = stats.get("min_price", 0.0)
    avg_price = stats.get("avg_price", 0.0)

    option_type = selected_main.get("option_type", "")
    is_best_value_selected = (selected_path == "option1") or ("value_recommendation" in option_type) or ("balanced_deal" in option_type)

    formatted_recs = []
    seen_ids = {selected_main.get("id")}
    exceeds_budget_warning = False

    for cat in related_cats:
        items = search_products(db=db, category=cat)
        if not items:
            continue

        if is_pro:
            # CASE 2 & CASE 5 (Pro): rating as main filter, then price
            items.sort(key=lambda p: (-p.rating, -p.price))
        elif budget_val < min_price:
            # CASE 1: Beginner/Intermediate below min -> cheapest useful products + highest rating
            items.sort(key=lambda p: (p.price, -p.rating))
        elif budget_val < avg_price:
            # CASE 3: rating, then price
            items.sort(key=lambda p: (-p.rating, -p.price))
        else:
            # CASE 4: Beginner/Intermediate with budget >= avg_price
            if is_best_value_selected:
                # If User Clicks Recommendation 1 (Best Value): highest-priced sub-category products
                items.sort(key=lambda p: (-p.price, -p.rating))
            else:
                # If User Clicks Recommendation 2: highest-ranked sub-category products
                items.sort(key=lambda p: (-p.rating, -p.price))

        for p in items:
            if p.id not in seen_ids:
                seen_ids.add(p.id)
                fmt = format_product_dict(p, merchant_map, sport=intent.sport, experience=intent.experience)
                fmt["personalized_reason"] = get_personalized_recommendation_reason(p, sport=intent.sport, experience=intent.experience)
                formatted_recs.append(fmt)
                break

    formatted_recs.sort(key=lambda x: x["price"])

    indiv_total = round(sum(i["price"] for i in formatted_recs), 2)
    orig_indiv_total = round(sum(i["original_price"] for i in formatted_recs), 2)
    bundle_savings = round(orig_indiv_total - indiv_total, 2)
    bundle_total = indiv_total
    grand_total = round(selected_main.get("price", 0.0) + bundle_total, 2)

    if grand_total > budget_val:
        exceeds_budget_warning = True

    lines = []
    lines.append(f"Recommended Cross-Merchant product specially for you !\n")
    lines.append(f"{selected_main['name']} — ₹{int(selected_main['price'])} (from {selected_main.get('merchant_name', 'Merchant')})\n")

    for idx, item in enumerate(formatted_recs, start=1):
        lines.append(f"• {item['name']} — ₹{int(item['price'])} — ★{item['rating']} (from {item['merchant_name']})")
        lines.append(f"  {item['personalized_reason']}\n")

    if bundle_savings > 0:
        lines.append(f"Bundle Savings: You save ₹{int(bundle_savings)} off standard list prices across items!\n")

    lines.append("Please select how you would like to proceed:")
    lines.append("• Add all recommended products")
    lines.append("• Select individually")
    lines.append("• End shopping (No complementary products)")

    return {
        "status": "cross_sell",
        "message": "\n".join(lines),
        "products": formatted_recs,
        "individual_total": indiv_total,
        "bundle_total": bundle_total,
        "bundle_savings": bundle_savings,
        "exceeds_budget": exceeds_budget_warning
    }


def build_lowest_cost_cross_sell(
    db: Session,
    selected_main: dict,
    intent
) -> dict:
    """
    Section 14: Finds the least expensive suitable complementary product for 'Too expensive' decline path.
    Single final attempt.
    """
    merchant_map = {m.id: m for m in db.query(Merchant).all()}
    related_cats = intent.related_categories or []

    lowest_product = None
    for cat in related_cats:
        items = search_products(db=db, category=cat)
        if items:
            items.sort(key=lambda p: p.price)
            if lowest_product is None or items[0].price < lowest_product.price:
                lowest_product = items[0]

    if not lowest_product:
        return {
            "status": "no_lower_cost_found",
            "message": "No lower-cost alternative is available.",
            "product": None
        }

    fmt = format_product_dict(lowest_product, merchant_map, sport=intent.sport, experience=intent.experience)
    fmt["personalized_reason"] = get_personalized_recommendation_reason(lowest_product, sport=intent.sport, experience=intent.experience)

    lines = []
    lines.append("Since you've already chosen the primary product, here's a lower-cost way to add one useful essential without significantly increasing your total:\n")
    lines.append(f"{fmt['name']} — ₹{int(fmt['price'])} — \n ★{fmt['rating']} (from {fmt['merchant_name']})")
    lines.append(f"{fmt['personalized_reason']}\n")
    lines.append("Would you like to add this item to your order or proceed to checkout?")

    return {
        "status": "low_cost_alternative",
        "message": "\n".join(lines),
        "product": fmt
    }


def find_brand_alternatives(
    db: Session,
    main_category: str,
    excluded_merchant_id: int
) -> list[dict]:
    """
    Section 16: Searches DB for alternative merchant brands offering equivalent category products.
    """
    merchant_map = {m.id: m for m in db.query(Merchant).all()}
    alt_products = db.query(Product).filter(
        Product.category == main_category,
        Product.merchant_id != excluded_merchant_id,
        Product.stock > 0
    ).all()

    formatted_alts = []
    for p in alt_products:
        fmt = format_product_dict(p, merchant_map)
        formatted_alts.append(fmt)

    return formatted_alts


def build_checkout_bill(cart: list[dict], budget: float | None = None):
    """
    Section 17: Provides a concise purchase summary containing main product, complementary products,
    merchants, subtotal, applicable discount, actual savings, and final total.
    """
    if not cart:
        return {
            "status": "complete",
            "message": "Your cart is currently empty.",
            "subtotal": 0.0,
            "total_savings": 0.0,
            "final_total": 0.0,
            "checkout_gated": False
        }

    total_price = round(sum(item["price"] for item in cart), 2)
    total_orig_price = round(sum(item.get("original_price", item["price"]) for item in cart), 2)
    total_savings = round(total_orig_price - total_price, 2)
    remaining_b = round(budget - total_price, 2) if (budget and budget >= total_price) else 0.0

    lines = []
    lines.append("========================================")
    lines.append("OFFICIAL CHECKOUT BILL & ORDER SUMMARY")
    lines.append("========================================\n")
    lines.append("Items in Your Order:")

    for idx, item in enumerate(cart, start=1):
        m_info = f" from {item.get('merchant_name')}" if item.get('merchant_name') else ""
        lines.append(
            f"{idx}. {item['name']}{m_info} — ₹{int(item['price'])} "
            f"(List Price: ₹{item.get('original_price', item['price'])})"
        )

    lines.append("\n----------------------------------------")
    lines.append(f"Subtotal (List Price Total): ₹{total_orig_price}")
    if total_savings > 0:
        lines.append(f"Actual Discount Savings: ₹{total_savings}")
    if remaining_b > 0:
        lines.append(f"Remaining Budget: ₹{remaining_b}")
    lines.append(f"Final Amount Payable: ₹{int(total_price)}")
    lines.append("----------------------------------------\n")
    lines.append("Order Confirmed! Ready for Razorpay Test Payment.")

    return {
        "status": "complete",
        "message": "\n".join(lines),
        "cart": cart,
        "subtotal": total_orig_price,
        "total_savings": total_savings,
        "final_total": total_price,
        "remaining_budget": remaining_b,
        "checkout_gated": False
    }