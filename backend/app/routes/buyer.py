import re
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.buyer_agent import extract_shopping_intent, generate_sport_clarification_question
from app.services.conversation import get_conversation
from app.services.shopping_service import (
    build_primary_recommendations,
    build_complementary_recommendations,
    build_lowest_cost_cross_sell,
    find_brand_alternatives,
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
    Parse numbers like '1', '2', '1, 2', '1,3'.
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
    Refined Sports-Commerce Buyer Agent Endpoint with Bounded Financial Audit Trail.
    """
    state = get_conversation(request.conversation_id)
    msg_lower = request.message.lower().strip()

    state.log_audit_event("user_message_received", {
        "step": state.step,
        "message": request.message
    })

    # Direct Checkout Command
    if msg_lower in ["direct checkout", "force checkout", "checkout now"]:
        state.step = "payment_confirmation"
        bill_res = build_checkout_bill(state.cart, budget=state.budget)
        state.log_audit_event("checkout_requested", {"cart_count": len(state.cart), "total": bill_res["final_total"]})
        return {
            "action": "PAYMENT_CONFIRMATION_PROMPT",
            "status": "payment_confirmation",
            "conversation_id": request.conversation_id,
            "message": f"{bill_res['message']}\n\nYour cart total is ₹{int(bill_res['final_total'])}. Would you like to proceed with payment?",
            "cart": state.cart,
            "subtotal": bill_res["subtotal"],
            "final_total": bill_res["final_total"],
            "remaining_budget": bill_res["remaining_budget"],
            "checkout_gated": True
        }

    # Intent Parsing with Context Retention
    intent = extract_shopping_intent(request.message, state.intent)
    state.intent = intent

    if intent.sport:
        state.sport = intent.sport
    elif state.sport:
        intent.sport = state.sport

    if intent.experience:
        state.experience = intent.experience
    elif state.experience:
        intent.experience = state.experience

    if intent.budget:
        state.budget = intent.budget
    elif state.budget:
        intent.budget = state.budget

    if intent.preference:
        state.user_preferences["preference"] = intent.preference


    state.log_audit_event("intent_extracted", {
        "sport": state.sport,
        "category": intent.main_category,
        "experience": state.experience,
        "budget": state.budget,
        "preference": state.user_preferences.get("preference")
    })

    sp_name = (state.sport or "sports").capitalize()

    # ---------------------------------------------------------
    # STEP 1: CLARIFICATION QUESTIONING (Missing info)
    # ---------------------------------------------------------
    if state.experience is None:
        state.step = "ask_experience"
        question = generate_sport_clarification_question(intent)
        state.pending_question = question
        state.log_audit_event("clarification_requested", {"missing_field": "experience", "question": question})
        return {
            "action": "CLARIFICATION_PROMPT",
            "status": "need_more_information",
            "conversation_id": request.conversation_id,
            "message": question,
            "missing_field": "experience"
        }

    if state.budget is None:
        state.step = "ask_experience"
        question = f"What is your maximum budget in INR?"
        state.pending_question = question
        state.log_audit_event("clarification_requested", {"missing_field": "budget", "question": question})
        return {
            "action": "CLARIFICATION_PROMPT",
            "status": "need_more_information",
            "conversation_id": request.conversation_id,
            "message": question,
            "missing_field": "budget"
        }

    if state.step == "ask_experience":
        state.step = "primary_options"


    # ---------------------------------------------------------
    # STEP: ask_preference ("Explore other products" branch)
    # ---------------------------------------------------------
    if state.step == "ask_preference":
        pref = intent.preference or request.message
        state.user_preferences["preference"] = pref
        state.log_audit_event("preference_received", {"preference": pref})

        state.step = "primary_options"
        primary_res = build_primary_recommendations(db, intent, preference=pref)
        state.primary_options = primary_res.get("options", [])
        state.log_audit_event("products_compared", {"options_count": len(state.primary_options)})

        return {
            "action": "PRIMARY_OPTIONS",
            "status": "primary_options",
            "conversation_id": request.conversation_id,
            "message": f"Updated recommendations prioritizing **{pref}** (Budget: ₹{int(state.budget)}):\n\n{primary_res['message']}",
            "options": state.primary_options,
            "checkout_gated": True
        }

    # ---------------------------------------------------------
    # STEP: primary_options (Choice between Option 1, Option 2, Option 3)
    # ---------------------------------------------------------
    if state.step == "primary_options":
        # Build primary options first if not cached/displayed yet
        if not state.primary_options:
            primary_res = build_primary_recommendations(db, intent, preference=state.user_preferences.get("preference"))
            if primary_res["status"] == "budget_stretch_required":
                state.primary_options = primary_res.get("options", [])
                state.log_audit_event("budget_stretch_required", {"diff": primary_res["price_difference"]})
                return {
                    "action": "BUDGET_STRETCH_PROMPT",
                    "status": "budget_stretch_required",
                    "conversation_id": request.conversation_id,
                    "message": primary_res["message"],
                    "options": state.primary_options,
                    "is_pro": primary_res.get("is_pro", False),
                    "checkout_gated": True
                }

            state.primary_options = primary_res.get("options", [])
            state.log_audit_event("primary_recommendation_generated", {"options_count": len(state.primary_options)})

            return {
                "action": "PRIMARY_OPTIONS",
                "status": "primary_options",
                "conversation_id": request.conversation_id,
                "message": primary_res["message"],
                "options": state.primary_options,
                "checkout_gated": True
            }

        # If primary options were already displayed, check user choice:
        opts = state.primary_options

        # Check if user selects Option 3 (Explore other products)
        if any(k in msg_lower for k in ["3", "option 3", "explore", "other", "different"]):
            state.step = "ask_preference"
            state.log_audit_event("explore_other_products_selected")
            pref_msg = (
                "What would you like to prioritize for your recommendation?\n"
                "• Rating (highest customer reviews)\n"
                "• Price ( better deal and affordability)\n"
                
            )
            return {
                "action": "ASK_PREFERENCE",
                "status": "ask_preference",
                "conversation_id": request.conversation_id,
                "message": pref_msg,
                "checkout_gated": True
            }


        # User chooses Option 2 (Best product within budget)
        if ("2" in msg_lower or "option 2" in msg_lower) and len(opts) > 1:
            chosen = opts[1]
            state.selected_primary = chosen
            if chosen not in state.cart:
                state.cart.append(chosen)

            state.log_audit_event("primary_product_selected", {"option": 2, "product_id": chosen["id"], "name": chosen["name"]})

            rem_budget = round(state.budget - chosen["price"], 2)
            conf_msg = (
                f"A strong choice for you. At ₹{int(chosen['price'])}, you're saving "
                f"₹{int(rem_budget)} in remaining budget which could be used to buy supporting gear for mastering {intent.sport}"
            )


            state.step = "cross_sell"
            cross_res = build_complementary_recommendations(db, chosen, intent, rem_budget, selected_path="option2")
            state.cross_sell_products = cross_res.get("products", [])

            return {
                "action": "CROSS_SELL_OPTIONS",
                "status": "cross_sell",
                "conversation_id": request.conversation_id,
                "message": f"{conf_msg}\n\n{cross_res['message']}",
                "selected_primary": chosen,
                "products": cross_res["products"],
                "individual_total": cross_res["individual_total"],
                "bundle_total": cross_res["bundle_total"],
                "bundle_savings": cross_res["bundle_savings"],
                "remaining_budget": rem_budget,
                "checkout_gated": True
            }

        # User chooses Option 1 (Best-value recommendation) or confirms
        if any(k in msg_lower for k in ["1", "option 1", "yes", "select", "value"]):
            chosen = opts[0] if opts else None
            if not chosen:
                return {"status": "error", "message": "No products available."}

            state.selected_primary = chosen
            if chosen not in state.cart:
                state.cart.append(chosen)

            state.log_audit_event("primary_product_selected", {"option": 1, "product_id": chosen["id"], "name": chosen["name"]})

            rem_budget = round(state.budget - chosen["price"], 2)
            conf_msg = (
                f"A strong choice for your current needs. At ₹{int(chosen['price'])}, you're keeping "
                f"₹{int(rem_budget)} in remaining budget available while getting the comfort and reliability that matter most at this stage."
            )


            state.step = "cross_sell"
            cross_res = build_complementary_recommendations(db, chosen, intent, rem_budget, selected_path="option1")
            state.cross_sell_products = cross_res.get("products", [])

            return {
                "action": "CROSS_SELL_OPTIONS",
                "status": "cross_sell",
                "conversation_id": request.conversation_id,
                "message": f"{conf_msg}\n\n{cross_res['message']}",
                "selected_primary": chosen,
                "products": cross_res["products"],
                "individual_total": cross_res["individual_total"],
                "bundle_total": cross_res["bundle_total"],
                "bundle_savings": cross_res["bundle_savings"],
                "remaining_budget": rem_budget,
                "checkout_gated": True
            }

        # Display initial Primary Options
        primary_res = build_primary_recommendations(db, intent, preference=state.user_preferences.get("preference"))
        state.primary_options = primary_res.get("options", [])
        return {
            "action": "PRIMARY_OPTIONS",
            "status": "primary_options",
            "conversation_id": request.conversation_id,
            "message": primary_res["message"],
            "options": state.primary_options,
            "checkout_gated": True
        }

    # ---------------------------------------------------------
    # STEP: cross_sell (Option 1: Add all, Option 2: Select individually, Option 3: Continue without)
    # ---------------------------------------------------------
    elif state.step == "cross_sell":
        if "1" in msg_lower or "all" in msg_lower or "option 1" in msg_lower:
            for item in state.cross_sell_products:
                if item not in state.cart:
                    state.cart.append(item)

            state.selected_cross_sells = list(state.cross_sell_products)
            state.log_audit_event("cross_sell_selected", {"type": "add_all", "count": len(state.cross_sell_products)})

            state.step = "payment_confirmation"
            bill_res = build_checkout_bill(state.cart, budget=state.budget)
            return {
                "action": "PAYMENT_CONFIRMATION_PROMPT",
                "status": "payment_confirmation",
                "conversation_id": request.conversation_id,
                "message": f"Added all recommended products to your order.\n\n{bill_res['message']}\n\nYour cart total is ₹{int(bill_res['final_total'])}. Would you like to proceed with payment?",
                "cart": state.cart,
                "subtotal": bill_res["subtotal"],
                "final_total": bill_res["final_total"],
                "remaining_budget": bill_res["remaining_budget"],
                "checkout_gated": True
            }

        elif "2" in msg_lower or "individual" in msg_lower or any(c in msg_lower for c in [",", "select"]):
            indices = parse_selected_indices(request.message)
            if msg_lower in ["2", "option 2", "select individually", "individually"] or not indices:
                state.step = "individual_select"
                return {
                    "action": "INDIVIDUAL_SELECT_PROMPT",
                    "status": "individual_select",
                    "conversation_id": request.conversation_id,
                    "message": "Which products would you like to add? Select item numbers (e.g. 1, 2):",
                    "products": state.cross_sell_products,
                    "checkout_gated": True
                }

            if indices and state.cross_sell_products:
                added = []
                for idx in indices:
                    if 1 <= idx <= len(state.cross_sell_products):
                        item = state.cross_sell_products[idx - 1]
                        if item not in state.cart:
                            state.cart.append(item)
                            added.append(item)

                            
                state.selected_cross_sells.extend(added)
                state.log_audit_event("cross_sell_selected", {"type": "individual", "items": [i["name"] for i in added]})
                state.step = "payment_confirmation"
                bill_res = build_checkout_bill(state.cart, budget=state.budget)
                return {
                    "action": "PAYMENT_CONFIRMATION_PROMPT",
                    "status": "payment_confirmation",
                    "conversation_id": request.conversation_id,
                    "message": f"Added selected items to cart.\n\n{bill_res['message']}\n\nYour cart total is ₹{int(bill_res['final_total'])}. Would you like to proceed with payment?",
                    "cart": state.cart,
                    "subtotal": bill_res["subtotal"],
                    "final_total": bill_res["final_total"],
                    "remaining_budget": bill_res["remaining_budget"],
                    "checkout_gated": True
                }

        elif "3" in msg_lower or "without" in msg_lower or "skip" in msg_lower or "no" in msg_lower:
            state.step = "decline_reason_prompt"
            state.log_audit_event("cross_sell_rejected", {"type": "checkout_without_recommendations"})
            reason_prompt = (
                "Understood. Could you share the main reason for continuing without recommendations?\n"
                "1. Too expensive\n"
                "2. Not relevant to me\n"
                "3. I don't like the brand\n"
                "4. I don't need additional products\n"
                "5. Other"
            )
            return {
                "action": "DECLINE_REASON_PROMPT",
                "status": "decline_reason_prompt",
                "conversation_id": request.conversation_id,
                "message": reason_prompt,
                "checkout_gated": True
            }

    # ---------------------------------------------------------
    # STEP: individual_select (Parse item selections)
    # ---------------------------------------------------------
    elif state.step == "individual_select":
        indices = parse_selected_indices(request.message)
        added = []
        if indices and state.cross_sell_products:
            for idx in indices:
                if 1 <= idx <= len(state.cross_sell_products):
                    item = state.cross_sell_products[idx - 1]
                    if item not in state.cart:
                        state.cart.append(item)
                        added.append(item)

        state.selected_cross_sells.extend(added)
        state.log_audit_event("cross_sell_selected", {"type": "individual", "items": [i["name"] for i in added]})

        state.step = "payment_confirmation"
        bill_res = build_checkout_bill(state.cart, budget=state.budget)
        return {
            "action": "PAYMENT_CONFIRMATION_PROMPT",
            "status": "payment_confirmation",
            "conversation_id": request.conversation_id,
            "message": f"Selected items added to your cart.\n\n{bill_res['message']}\n\nYour cart total is ₹{int(bill_res['final_total'])}. Would you like to proceed with payment?",
            "cart": state.cart,
            "subtotal": bill_res["subtotal"],
            "final_total": bill_res["final_total"],
            "remaining_budget": bill_res["remaining_budget"],
            "checkout_gated": True
        }

    # ---------------------------------------------------------
    # STEP: decline_reason_prompt
    # ---------------------------------------------------------
    elif state.step == "decline_reason_prompt":
        state.rejection_reason = request.message
        state.log_audit_event("rejection_reason_recorded", {"reason": request.message})

        if "1" in msg_lower or "expensive" in msg_lower or "price" in msg_lower:
            state.step = "low_cost_alternative"
            low_res = build_lowest_cost_cross_sell(db, state.selected_primary or {}, intent)
            state.lower_priced_options = [low_res["product"]] if low_res.get("product") else []

            if low_res["status"] == "no_lower_cost_found":
                state.step = "payment_confirmation"
                bill_res = build_checkout_bill(state.cart, budget=state.budget)
                return {
                    "action": "PAYMENT_CONFIRMATION_PROMPT",
                    "status": "payment_confirmation",
                    "conversation_id": request.conversation_id,
                    "message": f"Proceeding to checkout with your primary selection.\n\n{bill_res['message']}\n\nYour cart total is ₹{int(bill_res['final_total'])}. Would you like to proceed with payment?",
                    "cart": state.cart,
                    "final_total": bill_res["final_total"],
                    "checkout_gated": True
                }

            return {
                "action": "LOW_COST_ALTERNATIVE",
                "status": "low_cost_alternative",
                "conversation_id": request.conversation_id,
                "message": low_res["message"],
                "product": low_res["product"],
                "checkout_gated": True
            }

        elif "3" in msg_lower or "brand" in msg_lower:
            curr_merchant = state.selected_primary.get("merchant_id", 1) if state.selected_primary else 1
            main_c = intent.main_category or "running_shoes"
            alts = find_brand_alternatives(db, main_c, curr_merchant)

            if alts:
                lines = ["Alternative Merchant Brands Available in Catalog:\n"]
                for idx, a in enumerate(alts, start=1):
                    lines.append(f"{idx}. **{a['name']}** — ₹{int(a['price'])} from {a['merchant_name']} ({a['rating']}★)")
                lines.append("\nProceeding to checkout with your selected items...")
                
                state.step = "payment_confirmation"
                bill_res = build_checkout_bill(state.cart, budget=state.budget)
                return {
                    "action": "PAYMENT_CONFIRMATION_PROMPT",
                    "status": "payment_confirmation",
                    "conversation_id": request.conversation_id,
                    "message": f"{'\n'.join(lines)}\n\n{bill_res['message']}\n\nYour cart total is ₹{int(bill_res['final_total'])}. Would you like to proceed with payment?",
                    "cart": state.cart,
                    "final_total": bill_res["final_total"],
                    "checkout_gated": True
                }
            else:
                state.step = "payment_confirmation"
                bill_res = build_checkout_bill(state.cart, budget=state.budget)
                return {
                    "action": "PAYMENT_CONFIRMATION_PROMPT",
                    "status": "payment_confirmation",
                    "conversation_id": request.conversation_id,
                    "message": f"No alternative merchant brand is currently in stock for this category.\n\n{bill_res['message']}\n\nYour cart total is ₹{int(bill_res['final_total'])}. Would you like to proceed with payment?",
                    "cart": state.cart,
                    "final_total": bill_res["final_total"],
                    "checkout_gated": True
                }

        # If "2" (Not relevant), "4" (Don't need), or "5" (Other): Respect decision & proceed directly to checkout
        state.step = "payment_confirmation"
        bill_res = build_checkout_bill(state.cart, budget=state.budget)
        return {
            "action": "PAYMENT_CONFIRMATION_PROMPT",
            "status": "payment_confirmation",
            "conversation_id": request.conversation_id,
            "message": f"Understood! Proceeding directly to checkout with your primary selection.\n\n{bill_res['message']}\n\nYour cart total is ₹{int(bill_res['final_total'])}. Would you like to proceed with payment?",
            "cart": state.cart,
            "final_total": bill_res["final_total"],
            "checkout_gated": True
        }

    # ---------------------------------------------------------
    # STEP: low_cost_alternative (Single attempt)
    # ---------------------------------------------------------
    elif state.step == "low_cost_alternative":
        if any(k in msg_lower for k in ["yes", "add", "1", "ok"]):
            if state.lower_priced_options:
                item = state.lower_priced_options[0]
                if item not in state.cart:
                    state.cart.append(item)
                state.log_audit_event("cross_sell_selected", {"type": "low_cost_alternative", "item": item["name"]})

        state.step = "payment_confirmation"
        bill_res = build_checkout_bill(state.cart, budget=state.budget)
        return {
            "action": "PAYMENT_CONFIRMATION_PROMPT",
            "status": "payment_confirmation",
            "conversation_id": request.conversation_id,
            "message": f"{bill_res['message']}\n\nYour cart total is ₹{int(bill_res['final_total'])}. Would you like to proceed with payment?",
            "cart": state.cart,
            "final_total": bill_res["final_total"],
            "checkout_gated": True
        }

    # ---------------------------------------------------------
    # STEP: payment_confirmation (Explicit user approval before money action)
    # ---------------------------------------------------------
    elif state.step == "payment_confirmation":
        if any(k in msg_lower for k in ["yes", "confirm", "proceed", "pay", "checkout", "ok", "approve"]):
            state.log_audit_event("payment_initiated", {"cart_count": len(state.cart)})
            rzp_res = create_razorpay_order(state.cart) if state.cart else {}
            state.log_audit_event("payment_succeeded", {"order_id": rzp_res.get("order_id")})
            state.step = "payment_complete"

            bill_res = build_checkout_bill(state.cart, budget=state.budget)
            return {
                "action": "PAYMENT_SUCCESS",
                "status": "complete",
                "conversation_id": request.conversation_id,
                "message": f"Payment Successful via Razorpay Test Mode!\n\nOrder ID: {rzp_res.get('order_id')}\nAmount Paid: ₹{rzp_res.get('final_amount')}\n\nYour order has been placed with partner merchants.",
                "cart": state.cart,
                "subtotal": bill_res["subtotal"],
                "final_total": bill_res["final_total"],
                "razorpay_order": rzp_res,
                "audit_trail": state.audit_log,
                "checkout_gated": False
            }
        else:
            bill_res = build_checkout_bill(state.cart, budget=state.budget)
            return {
                "action": "PAYMENT_CONFIRMATION_PROMPT",
                "status": "payment_confirmation",
                "conversation_id": request.conversation_id,
                "message": f"Payment wasn't completed. Your cart is preserved.\n\n{bill_res['message']}\n\nWould you like to proceed with payment?",
                "cart": state.cart,
                "final_total": bill_res["final_total"],
                "checkout_gated": True
            }

    # Fallback response
    bill_res = build_checkout_bill(state.cart, budget=state.budget)
    return {
        "action": "PAYMENT_CONFIRMATION_PROMPT",
        "status": "payment_confirmation",
        "conversation_id": request.conversation_id,
        "message": bill_res["message"],
        "cart": state.cart,
        "final_total": bill_res["final_total"],
        "checkout_gated": True
    }
