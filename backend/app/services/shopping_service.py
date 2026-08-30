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


def get_personalized_product_need(
    product: Product,
    sport: str | None = None,
    experience: str | None = None
) -> str:
    """
    Generate professional, non-generic explanations based on attributes, ratings, and sport.
    """
    attrs = (product.attributes or "").lower()
    sp = (sport or "sports").capitalize()

    if "pro" in attrs or "carbon" in attrs or "english_willow" in attrs or "pitta" in attrs:
        return (
            f"Engineered for high-level {sp} performance with professional-grade materials ({product.rating}★ rating) "
            f"to maximize stroke control, speed, and durability."
        )
    elif "intermediate" in attrs or "balanced" in attrs or "fg" in attrs:
        return (
            f"A balanced choice for {sp} delivering solid responsiveness ({product.rating}★ rating), "
            f"enhanced stability, and long-lasting performance for regular play."
        )
    else:
        return (
            f"An excellent value pick for starting out in {sp} ({product.rating}★ rating), "
            f"offering reliable comfort, flexible handling, and solid build quality."
        )


def get_personalized_recommendation_reason(
    product: Product,
    sport: str | None = None
) -> str:
    """
    Generate professional utility explanations for cross-sell add-ons.
    """
    cat = (product.category or "").lower()
    sp = (sport or "sports").capitalize()

    if "grip" in cat:
        return (
            f"Essential for racquet control in {sp}. Absorbs moisture, prevents handle slipping, "
            f"and provides superior tactile grip during long sessions."
        )
    elif "shuttlecock" in cat:
        return (
            f"Tournament-tested shuttlecocks delivering consistent flight trajectory, accurate speed, "
            f"and high durability for practice and matches."
        )
    elif "socks" in cat:
        return (
            f"Engineered with moisture-wicking fabric and targeted cushioning to protect against friction and blisters."
        )
    elif "shin_guards" in cat or "pads" in cat or "gloves" in cat:
        return (
            f"Impact-absorbing protective gear designed to cushion strikes and safeguard against injury."
        )
    elif "balls" in cat:
        return (
            f"High-density felt balls providing consistent bounce, spin response, and durability."
        )
    elif "goggles" in cat or "swimwear" in cat or "cap" in cat:
        return (
            f"Anti-fog, UV-protected gear providing clear underwater visibility and ergonomic chlorine resistance."
        )
    else:
        return (
            f"High-value complement rated {product.rating}★ to complete your performance setup."
        )


def format_product_dict(p: Product, merchant_map: dict, sport: str | None = None, experience: str | None = None) -> dict:
    m = merchant_map.get(p.merchant_id)
    m_name = m.name if m else f"Merchant #{p.merchant_id}"
    disc_pct = m.max_discount if (m and m.max_discount) else 15.0
    orig_price = round(p.price / (1.0 - (disc_pct / 100.0)), 2)
    savings = round(orig_price - p.price, 2)
    need_stmt = get_personalized_product_need(p, sport=sport, experience=experience)

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
        "personalized_need": need_stmt
    }


def build_single_main_product(
    db: Session,
    main_category: str = "badminton_racket",
    pointer: int = 0,
    budget: float | None = None,
    experience: str | None = None,
    sport: str | None = None
):
    """
    Loads ONE main product at a time matching budget & sport, presenting 2 choices:
    Option 1: Checkout
    Option 2: Show next product
    """
    merchant_map = {m.id: m for m in db.query(Merchant).all()}
    candidates = search_products(db=db, category=main_category, max_price=budget)

    if not candidates:
        all_candidates = search_products(db=db, category=main_category)
        if not all_candidates:
            sp_display = (sport or "sports").capitalize()
            return {
                "status": "no_products_found",
                "message": f"Sorry, no products available for '{main_category.replace('_', ' ')}' in {sp_display}.",
                "product": None,
                "total_candidates": 0
            }
        else:
            min_price = min(p.price for p in all_candidates)
            return {
                "status": "budget_exceeded",
                "message": f"Requested budget of ₹{int(budget) if budget else 0} is below the catalog minimum of ₹{int(min_price)}.",
                "product": None,
                "total_candidates": 0
            }

    # Sort candidates: for beginners, overall value (rating desc, price asc); for experienced, performance (rating desc, price desc)
    if (experience or "").lower() == "beginner":
        candidates.sort(key=lambda p: (-p.rating, p.price))
    else:
        candidates.sort(key=lambda p: (-p.rating, -p.price))

    current_idx = pointer % len(candidates)
    selected = candidates[current_idx]
    fmt = format_product_dict(selected, merchant_map, sport=sport, experience=experience)

    sp_str = (sport or "sports").capitalize()
    lines = []
    lines.append(f"🏆 Top {sp_str} Recommendation (Option {current_idx + 1} of {len(candidates)}):\n")
    lines.append(f"• **{fmt['name']}** — **₹{int(fmt['price'])}** ({fmt['rating']}★ from {fmt['merchant_name']})")
    lines.append(f"• Why it fits your purpose: {fmt['personalized_need']}")
    lines.append(f"• Exclusive Deal: List Price ₹{fmt['original_price']} | Special Discount: {fmt['discount_percent']}% OFF | You Save: ₹{fmt['savings']}!\n")
    lines.append("Please select an option:")
    lines.append("• **Option 1**: Checkout")
    lines.append("• **Option 2**: Show next product")

    return {
        "status": "main_product",
        "message": "\n".join(lines),
        "product": fmt,
        "total_candidates": len(candidates),
        "current_pointer": current_idx,
        "has_next": len(candidates) > 1
    }


def build_crazy_deals_recommendations(
    db: Session,
    chosen_main: dict,
    related_categories: list[str],
    budget: float | None = None,
    experience: str | None = None,
    sport: str | None = None
):
    """
    Displays "We have got crazy deals just for you!" with add-on recommendations and 3 choices:
    Option 1: Checkout all the products
    Option 2: Select specific recommended products (e.g. 1, 2, or 1,2)
    Option 3: Checkout without any recommended product
    """
    merchant_map = {m.id: m for m in db.query(Merchant).all()}
    chosen_price = chosen_main.get("price", 0.0)
    remaining_budget = (budget - chosen_price) if (budget and budget > chosen_price) else None

    formatted_recs = []
    for cat in related_categories:
        items = search_products(db=db, category=cat, max_price=remaining_budget)
        if not items:
            items = search_products(db=db, category=cat)
        if not items:
            continue

        items.sort(key=lambda p: (-p.rating, p.price))
        p = items[0]
        fmt = format_product_dict(p, merchant_map, sport=sport, experience=experience)
        fmt["personalized_reason"] = get_personalized_recommendation_reason(p, sport=sport)
        formatted_recs.append(fmt)

    # Sort add-ons least costly first
    formatted_recs.sort(key=lambda x: x["price"])

    sp_str = (sport or "sports").capitalize()
    lines = []
    lines.append(f"🎉 **We have got crazy deals just for you!**\n")
    lines.append(f"You selected **{chosen_main['name']}** (₹{int(chosen_main['price'])}). To maximize your {sp_str} performance, we've unlocked exclusive add-on deals:\n")

    for idx, item in enumerate(formatted_recs, start=1):
        lines.append(f"{idx}. **{item['name']}** — **₹{int(item['price'])}** (from {item['merchant_name']})")
        lines.append(f"   • Why you need this: {item['personalized_reason']}")
        lines.append(f"   • Special Savings: List Price ₹{item['original_price']} | {item['discount_percent']}% OFF | You Save ₹{item['savings']}!\n")

    lines.append("Please select how you would like to proceed:")
    lines.append("• **Option 1**: Checkout all the products (Main item + All recommended add-ons)")
    lines.append("• **Option 2**: Select specific recommended products (Enter item numbers e.g. '1' or '1, 2')")
    lines.append("• **Option 3**: Checkout without any recommended product")

    return {
        "status": "crazy_deals",
        "message": "\n".join(lines),
        "selected_main": chosen_main,
        "recommended_products": formatted_recs
    }


def build_lower_priced_deals_recommendations(
    db: Session,
    chosen_main: dict,
    related_categories: list[str],
    budget: float | None = None,
    experience: str | None = None,
    sport: str | None = None
):
    """
    One-time lower-priced add-on deal presented after user declines initial recommendations,
    offering 3 options:
    Option 1: Checkout with recommended product
    Option 2: Checkout with certain products (enter item numbers e.g. 1, 2, 3)
    Option 3: Lets checkout (main item only)
    """
    merchant_map = {m.id: m for m in db.query(Merchant).all()}
    formatted_lower = []

    for cat in related_categories:
        items = search_products(db=db, category=cat)
        if not items:
            continue

        # Sort by lowest price first for budget-conscious value
        items.sort(key=lambda p: p.price)
        p = items[0]
        fmt = format_product_dict(p, merchant_map, sport=sport, experience=experience)
        fmt["personalized_reason"] = get_personalized_recommendation_reason(p, sport=sport)
        formatted_lower.append(fmt)

    formatted_lower.sort(key=lambda x: x["price"])

    sp_str = (sport or "sports").capitalize()
    main_val = int(chosen_main.get("price", 0))

    lines = []
    lines.append("⚡ **EXCLUSIVE ONE-TIME DISCOUNT UNLOCKED FOR YOU!**\n")
    lines.append(
        f"Since you are completing your order for **{chosen_main['name']}** (₹{main_val}), "
        f"we have unlocked an exclusive, lower-priced add-on deal strictly valid for this session:\n"
    )

    for idx, item in enumerate(formatted_lower, start=1):
        lines.append(f"{idx}. **{item['name']}** — **₹{int(item['price'])}** (from {item['merchant_name']})")
        lines.append(f"   • Essential Benefit: {item['personalized_reason']}")
        lines.append(f"   • Special Deal: List Price ₹{item['original_price']} | Saved ₹{item['savings']}!\n")

    lines.append("Please select an option:")
    lines.append("• **Option 1**: Checkout with recommended product")
    lines.append("• **Option 2**: Checkout with certain products (Enter item numbers e.g. '1' or '1, 2')")
    lines.append("• **Option 3**: Lets checkout (Main item only)")

    return {
        "status": "discounted_deals",
        "message": "\n".join(lines),
        "selected_main": chosen_main,
        "recommended_products": formatted_lower
    }


def build_checkout_bill(cart: list[dict]):
    """
    Generate final itemized bill directly when user completes checkout.
    """
    if not cart:
        return {
            "status": "complete",
            "message": "Your cart is currently empty.",
            "total": 0.0,
            "total_savings": 0.0,
            "checkout_gated": False
        }

    total_price = round(sum(item["price"] for item in cart), 2)
    total_orig_price = round(sum(item.get("original_price", item["price"]) for item in cart), 2)
    total_savings = round(total_orig_price - total_price, 2)

    lines = []
    lines.append("========================================")
    lines.append("🛍️ OFFICIAL CHECKOUT BILL & ORDER SUMMARY")
    lines.append("========================================\n")
    lines.append("Items in Your Order:")

    for idx, item in enumerate(cart, start=1):
        m_info = f" from {item.get('merchant_name')}" if item.get('merchant_name') else ""
        lines.append(
            f"{idx}. {item['name']}{m_info} - ₹{int(item['price'])} "
            f"(List Price: ₹{item.get('original_price', item['price'])} | Saved: ₹{item.get('savings', 0.0)})"
        )

    lines.append("\n----------------------------------------")
    lines.append(f"Subtotal (List Price Total): ₹{total_orig_price}")
    lines.append(f"Your Total Savings: ₹{total_savings}")
    lines.append(f"Final Amount Payable: ₹{int(total_price)}")
    lines.append("----------------------------------------\n")
    lines.append("✅ Order Confirmed! Ready for Razorpay Test Payment.")

    return {
        "status": "complete",
        "message": "\n".join(lines),
        "cart": cart,
        "total": total_price,
        "total_savings": total_savings,
        "checkout_gated": False
    }
