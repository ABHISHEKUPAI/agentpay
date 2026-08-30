import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


class ShoppingIntent(BaseModel):
    goal: str = Field(
        description="What the user is trying to accomplish"
    )

    sport: str | None = Field(
        default=None,
        description="Sport or activity explicitly or implicitly mentioned (e.g. 'badminton', 'football', 'cricket', 'tennis', 'swimming', 'running', 'gym', 'hiking', etc.)"
    )

    main_category: str | None = Field(
        default=None,
        description="Primary product category requested (e.g. 'badminton_racket', 'football_boots', 'cricket_bat', 'tennis_racket', 'swimming_goggles', 'running_shoes')"
    )

    related_categories: list[str] = Field(
        default_factory=list,
        description="Complementary product categories for cross-selling (e.g. ['badminton_grip', 'shuttlecock', 'badminton_shoes'] for badminton)"
    )

    experience: str | None = Field(
        default=None,
        description="User's explicit experience level: 'beginner', 'intermediate', 'experienced', or 'pro'. Set to null if not explicitly mentioned!"
    )

    product_level: str | None = Field(
        default=None,
        description="Expected product level: 'basic', 'standard', 'premium', 'performance'. Set to null if not mentioned."
    )

    budget: float | None = Field(
        default=None,
        description="Maximum budget in INR (e.g. 3000.0). Set to null if not explicitly mentioned!"
    )

    categories: list[str] = Field(
        default_factory=list,
        description="All relevant categories (main_category + related_categories)"
    )

    missing_info: list[str] = Field(
        default_factory=list,
        description="List of essential missing fields needed for a quality recommendation (e.g. ['experience'], ['budget'])"
    )


load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# Default Category Mappings for Popular Sports
SPORT_CATEGORY_MAP = {
    "badminton": {
        "main": "badminton_racket",
        "cross_sells": ["badminton_grip", "shuttlecock", "badminton_shoes"]
    },
    "football": {
        "main": "football_boots",
        "cross_sells": ["football_socks", "shin_guards", "football_jersey"]
    },
    "cricket": {
        "main": "cricket_bat",
        "cross_sells": ["cricket_gloves", "cricket_pads", "cricket_ball"]
    },
    "tennis": {
        "main": "tennis_racket",
        "cross_sells": ["tennis_balls", "tennis_grip"]
    },
    "swimming": {
        "main": "swimming_goggles",
        "cross_sells": ["swimwear", "swimming_cap"]
    },
    "running": {
        "main": "running_shoes",
        "cross_sells": ["running_socks", "running_shorts", "running_shirt"]
    }
}


def _fallback_extract_intent(
    user_message: str,
    previous_intent: ShoppingIntent | None = None
) -> ShoppingIntent:
    """
    Fallback deterministic parser for generic sports shopping.
    """
    msg_lower = user_message.lower()

    goal = previous_intent.goal if previous_intent else user_message
    sport = previous_intent.sport if previous_intent else None
    main_category = previous_intent.main_category if previous_intent else None
    related_categories = list(previous_intent.related_categories) if previous_intent else []
    experience = previous_intent.experience if previous_intent else None
    product_level = previous_intent.product_level if previous_intent else None
    budget = previous_intent.budget if previous_intent else None

    if any(k in msg_lower for k in ["badminton", "shuttle", "racket"]):
        sport = "badminton"
    elif any(k in msg_lower for k in ["football", "cleats", "boots", "jersey", "shin"]):
        sport = "football"
    elif any(k in msg_lower for k in ["cricket", "bat", "batting", "pads", "willow"]):
        sport = "cricket"
    elif any(k in msg_lower for k in ["tennis"]):
        sport = "tennis"
    elif any(k in msg_lower for k in ["swim", "swimming", "goggles", "swimwear", "jammers"]):
        sport = "swimming"
    elif any(k in msg_lower for k in ["running", "shoe", "shoes", "runner"]):
        sport = "running"

    if "racket" in msg_lower or "racquet" in msg_lower:
        if sport == "tennis":
            main_category = "tennis_racket"
        else:
            main_category = "badminton_racket"
    elif "bat" in msg_lower and "gloves" not in msg_lower and "pads" not in msg_lower:
        main_category = "cricket_bat"
    elif "boots" in msg_lower or "cleats" in msg_lower:
        main_category = "football_boots"
    elif "goggles" in msg_lower:
        main_category = "swimming_goggles"
    elif "shoes" in msg_lower or "shoe" in msg_lower:
        if sport == "badminton":
            main_category = "badminton_shoes"
        elif sport == "football":
            main_category = "football_boots"
        else:
            main_category = "running_shoes"

    if sport and not main_category:
        cfg = SPORT_CATEGORY_MAP.get(sport, {})
        main_category = cfg.get("main")
        related_categories = cfg.get("cross_sells", [])
    elif sport and main_category and not related_categories:
        cfg = SPORT_CATEGORY_MAP.get(sport, {})
        related_categories = [c for c in cfg.get("cross_sells", []) if c != main_category]

    budget_match = re.search(r'(?:under|below|max|budget|for|rs\.?|rupees|₹)\s*(\d+)', msg_lower)
    if not budget_match:
        budget_match = re.search(r'(\d+)\s*(?:rupees|rs|inr|\b)', msg_lower)
    if budget_match:
        try:
            val = float(budget_match.group(1))
            if val > 50:
                budget = val
        except ValueError:
            pass

    if any(k in msg_lower for k in ["pro", "experienced", "professional", "advanced", "competitive"]):
        experience = "experienced"
        product_level = "performance"
    elif any(k in msg_lower for k in ["beginner", "starter", "starting", "novice", "new", "casual"]):
        experience = "beginner"
        product_level = "basic"
    elif any(k in msg_lower for k in ["intermediate", "regular"]):
        experience = "intermediate"
        product_level = "standard"

    missing_info = []
    if experience is None:
        missing_info.append("experience")

    all_cats = []
    if main_category:
        all_cats.append(main_category)
    for rc in related_categories:
        if rc not in all_cats:
            all_cats.append(rc)

    return ShoppingIntent(
        goal=goal or user_message,
        sport=sport,
        main_category=main_category,
        related_categories=related_categories,
        experience=experience,
        product_level=product_level,
        budget=budget,
        categories=all_cats,
        missing_info=missing_info
    )


def extract_shopping_intent(
    user_message: str,
    previous_intent: ShoppingIntent | None = None
) -> ShoppingIntent:

    previous_context = ""

    if previous_intent is not None:
        previous_context = f"""
Previous conversation intent:
Goal: {previous_intent.goal}
Sport: {previous_intent.sport}
Main Category: {previous_intent.main_category}
Related Categories: {previous_intent.related_categories}
Experience: {previous_intent.experience}
Product level: {previous_intent.product_level}
Budget: {previous_intent.budget}
Categories: {previous_intent.categories}

Use this context to update missing fields when user provides new information.
"""

    prompt = f"""
You are the General Sports Buyer Agent for AgentPay, an AI-native shopping platform.
Your job is to understand what sports gear the user wants to buy across any sport (Badminton, Football, Cricket, Tennis, Swimming, Running, Gym, Hiking, etc.).

Extract:
1. goal: Summary of user's shopping goal.
2. sport: The sport or activity (e.g. 'badminton', 'football', 'cricket', 'tennis', 'swimming', 'running').
3. main_category: Primary product category requested (e.g. 'badminton_racket', 'football_boots', 'cricket_bat', 'swimming_goggles', 'running_shoes').
4. related_categories: List of 2-3 genuine complementary categories for cross-selling (e.g. ['badminton_grip', 'shuttlecock', 'badminton_shoes'] for badminton).
5. experience: User's experience level if mentioned ('beginner', 'intermediate', 'experienced', 'pro'). Return NULL if not mentioned!
6. product_level: Product level if mentioned ('basic', 'standard', 'premium', 'performance'). Return NULL if not mentioned!
7. budget: Maximum budget float in INR if mentioned (e.g. 'under 3000' -> 3000.0). Return NULL if not mentioned!
8. categories: List containing main_category plus related_categories.
9. missing_info: List containing missing essential fields (e.g. ['experience'] if experience is null).

CRITICAL RULES:
- Do NOT default to running! The user could be asking for badminton, football, cricket, tennis, swimming, etc.
- Do NOT assume experience level. If user did not state whether they are beginner or experienced, set experience to NULL and add 'experience' to missing_info.
- Do NOT fabricate budget if omitted.

{previous_context}

User message:
"{user_message}"
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ShoppingIntent,
            ),
        )
        parsed = ShoppingIntent.model_validate_json(response.text)
        if parsed.experience is None and "experience" not in parsed.missing_info:
            parsed.missing_info.append("experience")
        return parsed
    except Exception as e:
        return _fallback_extract_intent(user_message, previous_intent)


if __name__ == "__main__":
    res = extract_shopping_intent("I need a badminton racket under 3000 rupees")
    print(res)
