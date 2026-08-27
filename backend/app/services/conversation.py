from typing import Optional

from app.services.buyer_agent import ShoppingIntent


class ConversationState:
    def __init__(self):
        self.intent: Optional[ShoppingIntent] = None
        self.pending_question: Optional[str] = None


conversations: dict[str, ConversationState] = {}


def get_conversation(
    conversation_id: str
) -> ConversationState:

    if conversation_id not in conversations:
        conversations[conversation_id] = ConversationState()

    return conversations[conversation_id]