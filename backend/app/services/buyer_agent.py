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

    main_category: str | None = Field(
        default=None,
        description="Primary product category explicitly asked for (e.g. running_shoes)"
    )

    related_categories: list[str] = Field(
        default_factory=list,
        description="Complementary product categories for cross-selling (e.g. running_socks, running_shorts, running_shirt)"
    )

    experience: str | None = Field(
        default=None,
        description=(
            "User's experience level: beginner, intermediate, "
            "experienced, or pro/professional. Set to null if not explicitly mentioned."
        )
    )

    product_level: str | None = Field(
        default=None,
        description=(
            "Expected product level: basic, standard, "
            "premium, or performance. Set to null if not explicitly mentioned."
        )
    )

    budget: float | None = Field(
        default=None,
        description="Maximum budget in INR (e.g. 5000.0). Set to null if not explicitly mentioned."
    )

    categories: list[str] = Field(
        default_factory=list,
        description="All relevant product categories (main_category + related_categories)"
    )


load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def _fallback_extract_intent(
    user_message: str,
    previous_intent: ShoppingIntent | None = None
) -> ShoppingIntent:
    """
    Fallback deterministic parser used when LLM API is rate limited or unavailable.
    """
    msg_lower = user_message.lower()

    # Preserve previous values if available
    goal = previous_intent.goal if previous_intent else user_message
    main_category = previous_intent.main_category if previous_intent else None
    related_categories = list(previous_intent.related_categories) if previous_intent else []
    experience = previous_intent.experience if previous_intent else None
    product_level = previous_intent.product_level if previous_intent else None
    budget = previous_intent.budget if previous_intent else None

    # Parse Budget
    budget_match = re.search(r'(?:under|below|max|budget|for|rs\.?|rupees|₹)\s*(\d+)', msg_lower)
    if not budget_match:
        budget_match = re.search(r'(\d+)\s*(?:rupees|rs|inr|\b)', msg_lower)
    if budget_match:
        try:
            val = float(budget_match.group(1))
            if val > 50:  # Avoid matching arbitrary small numbers
                budget = val
        except ValueError:
            pass

    # Parse Experience
    if any(k in msg_lower for k in ["pro", "experienced", "professional", "advanced"]):
        experience = "experienced"
        product_level = "performance"
    elif any(k in msg_lower for k in ["beginner", "starter", "starting", "novice", "new"]):
        experience = "beginner"
        product_level = "basic"

    # Parse Categories
    if "hiking" in msg_lower or "boots" in msg_lower:
        main_category = "hiking_boots"
        related_categories = []
    elif any(k in msg_lower for k in ["shoe", "shoes", "runner", "running"]):
        main_category = "running_shoes"
        related_categories = ["running_socks", "running_shorts", "running_shirt"]

    all_cats = []
    if main_category:
        all_cats.append(main_category)
    for rc in related_categories:
        if rc not in all_cats:
            all_cats.append(rc)

    return ShoppingIntent(
        goal=goal or user_message,
        main_category=main_category,
        related_categories=related_categories,
        experience=experience,
        product_level=product_level,
        budget=budget,
        categories=all_cats
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
Main Category: {previous_intent.main_category}
Related Categories: {previous_intent.related_categories}
Experience: {previous_intent.experience}
Product level: {previous_intent.product_level}
Budget: {previous_intent.budget}
Categories: {previous_intent.categories}

Use this information as context.

If the user's new message provides a new or updated value for any field, update that value.
If the new message does not change or mention a value, preserve the previous value exactly as it was.
"""

    prompt = f"""
You are the Buyer Agent for AgentPay, an AI-native shopping platform for Agentic Commerce.

Your job is to understand what the user wants to buy.

Extract:
1. goal: Clear description of user's shopping goal.
2. main_category: The single main product category requested (e.g. 'running_shoes', 'hiking_boots', etc.).
3. related_categories: Complementary product categories relevant for cross-selling/upselling (e.g. ['running_socks', 'running_shorts', 'running_shirt'] for running shoes).
4. experience: User's explicit experience level if provided (e.g. 'beginner', 'experienced', 'pro'). Return null if NOT mentioned!
5. product_level: Expected product level if provided ('basic', 'standard', 'premium', 'performance'). Return null if NOT mentioned!
6. budget: Maximum budget in INR as a float if mentioned (e.g. 'under 5000' -> 5000.0). Return null if NOT mentioned!
7. categories: List containing main_category plus related_categories.

CRITICAL RULES:
- Do NOT assume the user is a beginner. If they didn't specify experience, set experience to null.
- Do NOT invent a budget if the user did not specify one. Set budget to null.
- Do NOT invent an experience level or product level.
- Convert natural language to standard categories (e.g., 'running shoes' -> 'running_shoes', 'socks' -> 'running_socks', 'shorts' -> 'running_shorts', 'shirt' -> 'running_shirt').

{previous_context}

Current user message:
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
        return ShoppingIntent.model_validate_json(response.text)
    except Exception as e:
        # Fallback to local rule parser if LLM API is unavailable/rate-limited
        return _fallback_extract_intent(user_message, previous_intent)


if __name__ == "__main__":
    result = extract_shopping_intent("I need running shoes under 5000 rupees")
    print(result)
