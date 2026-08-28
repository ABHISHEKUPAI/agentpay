import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


class ShoppingIntent(BaseModel):
    goal: str = Field(
        description="What the user is trying to accomplish"
    )

    experience: str | None = Field(
        default=None,
        description="User's experience level, such as beginner, intermediate, advanced, or professional"
    )

    product_level: str | None = Field(
        default=None,
        description="Expected product level, such as basic, standard, premium, or performance"
    )

    budget: float | None = Field(
        default=None,
        description="Maximum total budget in INR"
    )

    categories: list[str] = Field(
        description="Product categories needed to accomplish the goal"
    )


load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def extract_shopping_intent(
    user_message: str,
    previous_intent: ShoppingIntent | None = None
) -> ShoppingIntent:

    previous_context = "No previous conversation."

    if previous_intent is not None:
        previous_context = f"""
Previous shopping intent:

Goal:
{previous_intent.goal}

Experience:
{previous_intent.experience}

Product level:
{previous_intent.product_level}

Budget:
{previous_intent.budget}

Categories:
{previous_intent.categories}
"""

    prompt = f"""
You are the Buyer Agent for AgentPay, an AI-native shopping platform.

Your job is to understand what the user wants to buy and maintain
their shopping intent across multiple messages.

Extract:

- the user's goal
- experience level if explicitly mentioned
- expected product level if explicitly mentioned or clearly expressed
- maximum budget if mentioned
- product categories required to accomplish the goal

{previous_context}

Current user message:

{user_message}

Rules:

1. Never invent a budget.
   If neither the current message nor the previous intent contains a budget,
   return null.

2. Never invent an experience level.
   If the user has not explicitly provided their experience,
   return null.

3. Never invent a product level.
   Only set product_level when the user clearly expresses the type
   or quality level of product they expect.

4. Preserve information from the previous intent unless the user
   explicitly changes it.

5. If the current message provides a new budget, use the new budget.

6. If the current message provides a new experience level,
   use the new experience level.

7. If the current message provides a new product level,
   use the new product level.

8. Convert natural language into our product categories.

9. For someone starting running, useful categories can include:
   running_shoes,
   running_shirt,
   running_shorts,
   running_socks.

10. Do not assume that "starting running" means beginner.
    Only set experience to beginner if the user actually indicates
    that they are a beginner or equivalent.

Examples of product levels:

- "something basic" → basic
- "normal everyday quality" → standard
- "something premium" → premium
- "high performance running shoes" → performance

If the user has not expressed a product level,
product_level must remain null.
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ShoppingIntent,
        ),
    )

    return ShoppingIntent.model_validate_json(
        response.text
    )


if __name__ == "__main__":

    result = extract_shopping_intent(
        "I want to start running. "
        "I'm a beginner and I have a budget of 5000 rupees."
    )

    print(result)