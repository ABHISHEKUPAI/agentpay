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
        description="User's experience level, such as beginner or experienced"
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

def extract_shopping_intent(user_message: str) -> ShoppingIntent:

    prompt = f"""
You are the Buyer Agent for AgentPay, an AI-native shopping platform.

Your job is to understand what the user wants to buy.

Extract:
- the user's goal
- experience level if mentioned
- maximum budget if mentioned
- the product categories required to accomplish the goal

Rules:

1. Do not invent a budget if the user didn't provide one.
2. Do not invent an experience level if the user didn't provide one.
3. Convert natural language into our product categories.
4. For someone starting running, useful categories can include:
   running_shoes,
   running_shirt,
   running_shorts,
   running_socks.

User message:

{user_message}
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ShoppingIntent,
        ),
    )

    return ShoppingIntent.model_validate_json(response.text)


if __name__ == "__main__":

    result = extract_shopping_intent(
        "I want to start running. "
        "I'm a beginner and I have a budget of 5000 rupees."
    )

    print(result)