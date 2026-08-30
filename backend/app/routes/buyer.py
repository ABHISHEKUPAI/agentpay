import re
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.buyer_agent import extract_shopping_intent
from app.services.conversation import get_conversation
from app.services.shopping_service import (
    build_single_main_product,
    build_crazy_deals_recommendations,
    build_lower_priced_deals_recommendations,
    build_checkout_bill
)
from app.services.razorpay_service import create_razorpay_order


router = APIRouter(
    prefix="/buyer",
    tags=["Buyer Agent"]
)


class BuyerRequest(BaseModel):
    message: str


class BuyerChatRequest(BaseModel):
    conversation_id: str
    message: str


class CheckoutRequest(BaseModel):
    conversation_id: str | None = None
    cart: list[dict] | None = None
    flash_discount_percent: float = 0.0


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/intent")
def extract_intent(request: BuyerRequest):
    intent = extract_shopping_intent(request.message)
    return intent


@router.post("/checkout")
def checkout_cart(request: CheckoutRequest):
    target_cart = request.cart

    if not target_cart and request.conversation_id:
        state = get_conversation(request.conversation_id)
        target_cart = state.cart

    if not target_cart:
        return {
            "status": "error",
            "message": "Cart is empty. Please add items to checkout."
        }

    rzp_res = create_razorpay_order(
        cart=target_cart,
        flash_discount_percent=request.flash_discount_percent
    )
    return rzp_res


def parse_selected_indices(msg: str) -> list[int]:
    """
    Parse comma-separated or space-separated numbers like '1', '2', '1, 2', '1,2,3'.
    """
    found = re.findall(r'\b\d+\b', msg)
    indices = []
    for f in found:
        try:
            val = int(f)
            if val > 0 and val not in indices:
                indices.append(val)
        except ValueError:
            pass
    return indices


@router.post("/chat")
def buyer_chat(
    request: BuyerChatRequest,
    db: Session = Depends(get_db)
):
    """
    Refined Multi-Stage Conversational Sales & Recommendation Engine.
    """
    state = get_conversation(request.conversation_id)
    msg_lower = request.message.lower().strip()

    # ---------------------------------------------------------
    # Instant Direct Checkout Command
    # ---------------------------------------------------------
    if msg_lower in ["direct checkout", "force checkout", "checkout now"]:
        state.step = "checkout"
        bill_res = build_checkout_bill(state.cart)
        rzp_res = create_razorpay_order(state.cart) if state.cart else {}
        return {
            "status": bill_res["status"],
            "conversation_id": request.conversation_id,
            "message": bill_res["message"],
            "cart": bill_res.get("cart", []),
            "total": bill_res["total"],
            "total_savings": bill_res["total_savings"],
            "razorpay_order": rzp_res,
            "audit_trail": rzp_res.get("audit_trail"),
            "checkout_gated": False
        }

    # ---------------------------------------------------------
    # Intent Parsing & State Context Update
    # ---------------------------------------------------------
    intent = extract_shopping_intent(request.message, state.intent)
    state.intent = intent
    if intent.sport:
        state.sport = intent.sport

    sp_name = (state.sport or "sports").capitalize()

    # ---------------------------------------------------------
    # Adaptive Questioning for Missing Information
    # ---------------------------------------------------------
    if intent.experience is None:
        state.pending_question = f"Are you a beginner, regular player, or competitive player in {sp_name}?"
        return {
            "status": "need_more_information",
            "conversation_id": request.conversation_id,
            "message": state.pending_question,
            "missing_field": "experience"
        }

    if intent.budget is None:
        state.pending_question = f"What is your maximum budget in INR for your {sp_name} setup?"
        return {
            "status": "need_more_information",
            "conversation_id": request.conversation_id,
            "message": state.pending_question,
            "missing_field": "budget"
        }

    main_cat = intent.main_category or f"{state.sport or 'running'}_shoes"
    related_cats = intent.related_categories or []

    # =========================================================
    # STATE MACHINE TRANSITIONS
    # =========================================================

    # ---------------------------------------------------------
    # STATE 1: main_product (Load 1 main product at a time)
    # ---------------------------------------------------------
    if state.step == "main_product":
        # Check if user says "2" or "show next" to view next option
        if any(k in msg_lower for k in ["2", "next", "show next", "another", "different"]):
            state.main_pointer += 1
            main_res = build_single_main_product(
                db=db,
                main_category=main_cat,
                pointer=state.main_pointer,
                budget=intent.budget,
                experience=intent.experience,
                sport=state.sport
            )
            state.selected_main_product = main_res.get("product")
            return {
                "status": "main_product",
                "conversation_id": request.conversation_id,
                "message": main_res["message"],
                "product": main_res.get("product"),
                "checkout_gated": True
            }

        # Check if user says "1" or "checkout" or selects product
        if any(k in msg_lower for k in ["1", "checkout", "select", "buy", "yes", "option 1"]):
            main_res = build_single_main_product(
                db=db,
                main_category=main_cat,
                pointer=state.main_pointer,
                budget=intent.budget,
                experience=intent.experience,
                sport=state.sport
            )
            chosen_main = main_res.get("product")

            if not chosen_main:
                return {
                    "status": "no_products_found",
                    "conversation_id": request.conversation_id,
                    "message": main_res["message"]
                }

            state.selected_main_product = chosen_main
            if chosen_main not in state.cart:
                state.cart.append(chosen_main)

            # Move to Crazy Deals Stage!
            state.step = "crazy_deals"
            crazy_res = build_crazy_deals_recommendations(
                db=db,
                chosen_main=chosen_main,
                related_categories=related_cats,
                budget=intent.budget,
                experience=intent.experience,
                sport=state.sport
            )
            state.recommended_options = crazy_res.get("recommended_products", [])

            return {
                "status": "crazy_deals",
                "conversation_id": request.conversation_id,
                "message": crazy_res["message"],
                "selected_main": chosen_main,
                "recommended_products": crazy_res["recommended_products"],
                "cart": state.cart,
                "checkout_gated": True
            }

        # Initial loading of single main product
        main_res = build_single_main_product(
            db=db,
            main_category=main_cat,
            pointer=state.main_pointer,
            budget=intent.budget,
            experience=intent.experience,
            sport=state.sport
        )

        if main_res["status"] in ["no_products_found", "budget_exceeded"]:
            return {
                "status": main_res["status"],
                "conversation_id": request.conversation_id,
                "message": main_res["message"]
            }

        state.selected_main_product = main_res.get("product")
        return {
            "status": "main_product",
            "conversation_id": request.conversation_id,
            "message": main_res["message"],
            "product": main_res.get("product"),
            "checkout_gated": True
        }

    # ---------------------------------------------------------
    # STATE 2: crazy_deals
    # Option 1: Checkout all products
    # Option 2: Select specific recommended products (e.g. 1, 2 or 1,2)
    # Option 3: Checkout without any recommended product
    # ---------------------------------------------------------
    elif state.step == "crazy_deals":
        if "1" in msg_lower or "all" in msg_lower or "option 1" in msg_lower:
            # Add all recommended products to cart
            for rec in state.recommended_options:
                if rec not in state.cart:
                    state.cart.append(rec)

            total_sav = sum(item.get("savings", 0.0) for item in state.cart)

            # Convince user with professional copy highlighting savings & sport benefits
            conf_msg = (
                f"🎉 **Outstanding Decision! You secured an incredible deal saving a total of ₹{round(total_sav, 2)}!**\n\n"
                f"Your complete {sp_name} kit has been assembled. All products feature top durability and friction protection "
                f"engineered to elevate your performance on the field/court.\n\n"
                f"Generating your itemized bill and Razorpay order..."
            )

            state.step = "checkout"
            bill_res = build_checkout_bill(state.cart)
            rzp_res = create_razorpay_order(state.cart)

            return {
                "status": "complete",
                "conversation_id": request.conversation_id,
                "message": f"{conf_msg}\n\n{bill_res['message']}",
                "cart": state.cart,
                "total": bill_res["total"],
                "total_savings": bill_res["total_savings"],
                "razorpay_order": rzp_res,
                "audit_trail": rzp_res.get("audit_trail"),
                "checkout_gated": False
            }

        elif "2" in msg_lower or any(c in msg_lower for c in [",", "select"]):
            indices = parse_selected_indices(request.message)

            added = []
            if indices and state.recommended_options:
                for idx in indices:
                    if 1 <= idx <= len(state.recommended_options):
                        item = state.recommended_options[idx - 1]
                        if item not in state.cart:
                            state.cart.append(item)
                            added.append(item)

            total_sav = sum(item.get("savings", 0.0) for item in state.cart)
            conf_msg = (
                f"🎉 **Great Selection! You unlocked ₹{round(total_sav, 2)} in total savings!**\n\n"
                f"Your customized {sp_name} setup delivers the exact performance benefits required for your goals.\n\n"
                f"Generating your itemized bill and Razorpay order..."
            )

            state.step = "checkout"
            bill_res = build_checkout_bill(state.cart)
            rzp_res = create_razorpay_order(state.cart)

            return {
                "status": "complete",
                "conversation_id": request.conversation_id,
                "message": f"{conf_msg}\n\n{bill_res['message']}",
                "cart": state.cart,
                "total": bill_res["total"],
                "total_savings": bill_res["total_savings"],
                "razorpay_order": rzp_res,
                "audit_trail": rzp_res.get("audit_trail"),
                "checkout_gated": False
            }

        elif "3" in msg_lower or "without" in msg_lower or "no" in msg_lower or "skip" in msg_lower:
            state.step = "decline_reason"
            return {
                "status": "decline_reason",
                "conversation_id": request.conversation_id,
                "message": (
                    f"We understand! Could you briefly let us know the main reason for skipping the recommended add-ons? "
                    f"(e.g. price is too high, already own these accessories, or only need the main item)"
                ),
                "checkout_gated": True
            }

    # ---------------------------------------------------------
    # STATE 3: decline_reason -> Present Lower-Priced One-Time Deal
    # ---------------------------------------------------------
    elif state.step == "decline_reason":
        state.user_decline_reason = request.message
        state.step = "discounted_deals"

        lower_res = build_lower_priced_deals_recommendations(
            db=db,
            chosen_main=state.selected_main_product or {},
            related_categories=related_cats,
            budget=intent.budget,
            experience=intent.experience,
            sport=state.sport
        )

        state.lower_priced_options = lower_res.get("recommended_products", [])

        return {
            "status": "discounted_deals",
            "conversation_id": request.conversation_id,
            "message": lower_res["message"],
            "recommended_products": lower_res["recommended_products"],
            "checkout_gated": True
        }

    # ---------------------------------------------------------
    # STATE 4: discounted_deals
    # Option 1: Checkout with recommended product
    # Option 2: Checkout with certain products (enter numbers 1, 2, 3 or 1,2,3)
    # Option 3: Lets checkout (main item only)
    # ---------------------------------------------------------
    elif state.step == "discounted_deals":
        if "1" in msg_lower or "recommended" in msg_lower or "option 1" in msg_lower:
            for item in state.lower_priced_options:
                if item not in state.cart:
                    state.cart.append(item)

        elif "2" in msg_lower or any(c in msg_lower for c in [",", "certain"]):
            indices = parse_selected_indices(request.message)
            if indices and state.lower_priced_options:
                for idx in indices:
                    if 1 <= idx <= len(state.lower_priced_options):
                        item = state.lower_priced_options[idx - 1]
                        if item not in state.cart:
                            state.cart.append(item)

        # Transition to Final Checkout
        state.step = "checkout"
        bill_res = build_checkout_bill(state.cart)
        rzp_res = create_razorpay_order(state.cart) if state.cart else {}

        return {
            "status": bill_res["status"],
            "conversation_id": request.conversation_id,
            "message": bill_res["message"],
            "cart": bill_res.get("cart", []),
            "total": bill_res["total"],
            "total_savings": bill_res["total_savings"],
            "razorpay_order": rzp_res,
            "audit_trail": rzp_res.get("audit_trail"),
            "checkout_gated": False
        }

    # Fallback checkout
    bill_res = build_checkout_bill(state.cart)
    rzp_res = create_razorpay_order(state.cart) if state.cart else {}

    return {
        "status": bill_res["status"],
        "conversation_id": request.conversation_id,
        "message": bill_res["message"],
        "cart": bill_res.get("cart", []),
        "total": bill_res["total"],
        "total_savings": bill_res["total_savings"],
        "razorpay_order": rzp_res,
        "audit_trail": rzp_res.get("audit_trail"),
        "checkout_gated": False
    }
