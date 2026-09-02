from datetime import datetime
from typing import Optional, Any
from app.services.buyer_agent import ShoppingIntent


class ConversationState:
    def __init__(self):
        self.intent: Optional[ShoppingIntent] = None
        self.pending_question: Optional[str] = None
        self.step: str = "ask_experience"
        # Steps: "ask_experience", "primary_options", "ask_preference", "confirm_primary", "cross_sell", "decline_reason_prompt", "low_cost_alternative", "brand_alternatives", "checkout_summary", "payment_confirmation", "payment_complete"
        
        self.sport: Optional[str] = None
        self.experience: Optional[str] = None
        self.budget: Optional[float] = None
        self.user_preferences: dict = {}
        
        self.primary_options: list[dict] = []
        self.selected_primary: Optional[dict] = None
        
        self.cross_sell_products: list[dict] = []
        self.selected_cross_sells: list[dict] = []
        self.lower_priced_options: list[dict] = []
        self.rejection_reason: Optional[str] = None
        
        self.cart: list[dict] = []
        self.audit_log: list[dict] = []

    def log_audit_event(self, action: str, details: Optional[dict] = None):
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": action,
            "details": details or {}
        }
        self.audit_log.append(event)


conversations: dict[str, ConversationState] = {}


def get_conversation(conversation_id: str) -> ConversationState:
    if conversation_id not in conversations:
        conversations[conversation_id] = ConversationState()
    return conversations[conversation_id]