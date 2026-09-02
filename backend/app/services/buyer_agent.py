import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


class ShoppingIntent(BaseModel):
    goal: str = Field(
        description="Summary of what the user is trying to accomplish"
    )

    sport: str | None = Field(
        default=None,
        description="Sport or activity mentioned (e.g. 'running', 'badminton', 'football', 'cricket', 'tennis', 'swimming', 'cycling', 'gym')"
    )

    main_category: str | None = Field(
        default=None,
        description="Primary product category requested (e.g. 'running_shoes', 'badminton_racket', 'football_boots', 'cricket_bat', 'tennis_racket', 'swimming_goggles')"
    )

    related_categories: list[str] = Field(
        default_factory=list,
        description="Complementary product categories for cross-selling"
    )

    experience: str | None = Field(
        default=None,
        description="User's experience level: 'beginner', 'intermediate', 'experienced', or 'pro'. Return NULL if not explicitly mentioned!"
    )

    preference: str | None = Field(
        default=None,
        description="User's explicit preference if mentioned: 'rating', 'comfort', 'performance', 'price', 'durability'. Set to NULL if omitted."
    )

    budget: float | None = Field(
        default=None,
        description="Maximum budget float in INR. Set to NULL if not explicitly mentioned!"
    )

    categories: list[str] = Field(
        default_factory=list,
        description="All relevant categories (main_category + related_categories)"
    )

    missing_info: list[str] = Field(
        default_factory=list,
        description="List of essential missing fields (e.g. ['experience'])"
    )


load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


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


def generate_sport_clarification_question(intent: ShoppingIntent) -> str:
    """
    Generates dynamic, sport-specific clarification questions.
    """
    sp = (intent.sport or "sports").lower()

    if sp == "running":
        return "To find the right fit, would you describe yourself as a beginner, intermediate, or experienced runner?"
    elif sp == "badminton":
        return "To select the right product, are you a beginner, regular player, or competitive player in badminton?"
    elif sp == "cricket":
        return "To recommend the right cricket bat/gear, are you a beginner, regular player, or competitive cricketer?"
    elif sp == "football":
        return "To select the right football boots, are you a beginner, regular player, or competitive footballer?"
    elif sp == "swimming":
        return "To recommend the best swim gear, are you a beginner swimmer, lap swimmer, or competitive athlete?"
    elif sp == "tennis":
        return "To recommend the right tennis racket, are you a beginner, regular player, or competitive tennis player?"
    else:
        sp_title = sp.capitalize()
        return f"To recommend the right gear, are you a beginner, regular player, or competitive player i?"


def _fallback_extract_intent(
    user_message: str,
    previous_intent: ShoppingIntent | None = None
) -> ShoppingIntent:
    """
    Deterministic fallback parser for generic sports shopping.
    """
    msg_lower = user_message.lower()

    goal = previous_intent.goal if previous_intent else user_message
    sport = previous_intent.sport if previous_intent else None
    main_category = previous_intent.main_category if previous_intent else None
    related_categories = list(previous_intent.related_categories) if previous_intent else []
    experience = previous_intent.experience if previous_intent else None
    preference = previous_intent.preference if previous_intent else None
    budget = previous_intent.budget if previous_intent else None

    if any(k in msg_lower for k in ["badminton", "shuttle", "racket"]):
        sport = "badminton"
    elif any(k in msg_lower for k in ["football", "cleats", "boots", "jersey", "shin"]):
        sport = "football"
    elif any(k in msg_lower for k in ["cricket", "bat", "batting", "pads", "willow"]):
        sport = "cricket"
    elif any(k in msg_lower for k in ["tennis"]):
        sport = "tennis"
    elif any(k in msg_lower for k in ["swim", "swimming", "goggles", "swimwear"]):
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

    clean_msg = msg_lower.replace(",", "")
    budget_match = re.search(r'(?:under|below|max|budget|for|rs\.?|rupees|₹)\s*(\d+)', clean_msg)
    if not budget_match:
        budget_match = re.search(r'(\d+)\s*(?:rupees|rs|inr|\b)', clean_msg)
    if budget_match:
        try:
            val = float(budget_match.group(1))
            if val > 50:
                budget = val
        except ValueError:
            pass


    if any(k in msg_lower for k in ["pro", "experienced", "professional", "advanced", "competitive", "km", "compete"]):
        experience = "experienced"
    elif any(k in msg_lower for k in ["beginner", "starter", "starting", "novice", "new", "casual", "getting started", "i'm a beginner"]):
        experience = "beginner"
    elif any(k in msg_lower for k in ["intermediate", "regular"]):
        experience = "intermediate"

    if "rating" in msg_lower:
        preference = "rating"
    elif "comfort" in msg_lower:
        preference = "comfort"
    elif "performance" in msg_lower:
        preference = "performance"
    elif "cheapest" in msg_lower or "price" in msg_lower or "value" in msg_lower:
        preference = "price"
    elif "durability" in msg_lower or "durable" in msg_lower:
        preference = "durability"

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
        preference=preference,
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
Budget: {previous_intent.budget}
Preference: {previous_intent.preference}
Categories: {previous_intent.categories}

Use this context to update missing fields when user provides new information.
"""

    prompt = f"""
You are the General Sports Buyer Agent for AgentPay, an AI-native shopping platform.
Your job is to extract user shopping intent across any sport (Running, Badminton, Cricket, Football, Tennis, Swimming, Cycling, Gym, etc.).

Extract:
1. goal: Summary of user's shopping goal.
2. sport: The sport or activity (e.g. 'running', 'badminton', 'cricket', 'football', 'tennis', 'swimming').
3. main_category: Primary product category requested (e.g. 'running_shoes', 'badminton_racket', 'cricket_bat', 'football_boots').
4. related_categories: List of 2-3 genuine complementary categories.
5. experience: User's experience level if mentioned ('beginner', 'intermediate', 'experienced', 'pro'). Return NULL if not mentioned!
6. preference: User's preference if mentioned ('rating', 'comfort', 'performance', 'price', 'durability'). Return NULL if not mentioned!
7. budget: Maximum budget float in INR if mentioned (e.g. 5000.0). Return NULL if not mentioned!
8. categories: List containing main_category plus related_categories.
9. missing_info: List containing missing essential fields (e.g. ['experience'] if experience is null).

CRITICAL RULES:
- Do NOT assume experience level. Return NULL and add 'experience' to missing_info if omitted.
- Do NOT fabricate budget or prices.

{previous_context}

User message:
"{user_message}"
"""

    try:
        chat = client.chats.create(
            model="gemini-3.6-flash",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ShoppingIntent,
            ),
        )
        response = chat.send_message(prompt)
        parsed = ShoppingIntent.model_validate_json(response.text)
        if parsed.experience is None and "experience" not in parsed.missing_info:
            parsed.missing_info.append("experience")

        if parsed.budget is None or parsed.sport is None or parsed.main_category is None:
            fallback = _fallback_extract_intent(user_message, previous_intent)
            if parsed.budget is None and fallback.budget is not None:
                parsed.budget = fallback.budget
            if parsed.sport is None and fallback.sport is not None:
                parsed.sport = fallback.sport
            if parsed.main_category is None and fallback.main_category is not None:
                parsed.main_category = fallback.main_category

        return parsed

    except Exception as e:
        return _fallback_extract_intent(user_message, previous_intent)
