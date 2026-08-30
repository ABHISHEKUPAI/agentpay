from typing import Optional

from app.services.buyer_agent import ShoppingIntent


class ConversationState:
    def __init__(self):
        self.intent: Optional[ShoppingIntent] = None
        self.pending_question: Optional[str] = None
        self.step: str = "main_product"  # "need_info", "main_product", "crazy_deals", "decline_reason", "discounted_deals", "checkout"
        self.sport: Optional[str] = None
        self.main_pointer: int = 0
        self.selected_main_product: Optional[dict] = None
        self.main_options: list[dict] = []
        self.recommended_options: list[dict] = []
        self.lower_priced_options: list[dict] = []
        self.user_decline_reason: Optional[str] = None
        self.cart: list[dict] = []
        self.audit_log: list[dict] = []


conversations: dict[str, ConversationState] = {}


def get_conversation(
    conversation_id: str
) -> ConversationState:

    if conversation_id not in conversations:
        conversations[conversation_id] = ConversationState()

    return conversations[conversation_id]