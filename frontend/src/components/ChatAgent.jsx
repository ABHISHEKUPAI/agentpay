import React, { useState } from 'react';

const API_BASE = "http://localhost:8000";

export default function ChatAgent({ conversationId, cart, setCart, setCurrentOrderData, updateAuditLog }) {
    const [inputMsg, setInputMsg] = useState("");
    const [messages, setMessages] = useState([
        {
            sender: "bot",
            text: "Welcome to AgentPay. I am your General Sports Shopping AI Agent. State your sport requirement and budget, and I will construct the optimal setup for you.",
            status: "initial"
        }
    ]);
    const [latestBotState, setLatestBotState] = useState(null);

    const handleSend = async (textToSend) => {
        const query = textToSend || inputMsg;
        if (!query.trim()) return;

        // Append user message
        const updatedMsgs = [...messages, { sender: "user", text: query }];
        setMessages(updatedMsgs);
        if (!textToSend) setInputMsg("");

        try {
            const res = await fetch(`${API_BASE}/buyer/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    conversation_id: conversationId,
                    message: query
                })
            });

            const data = await res.json();
            setLatestBotState(data);

            setMessages(prev => [
                ...prev,
                {
                    sender: "bot",
                    text: data.message,
                    status: data.status,
                    data: data
                }
            ]);

            if (data.cart) {
                setCart(data.cart);
            }

            if (data.status === "complete" || data.razorpay_order) {
                if (data.razorpay_order) setCurrentOrderData(data.razorpay_order);
                if (data.audit_trail || data.razorpay_order?.audit_trail) {
                    updateAuditLog(data.audit_trail || data.razorpay_order?.audit_trail);
                }
            }
        } catch (err) {
            console.error(err);
            setMessages(prev => [
                ...prev,
                { sender: "bot", text: "Unable to connect to backend server. Please verify FastAPI is running on port 8000." }
            ]);
        }
    };

    const handlePreset = (presetText) => {
        handleSend(presetText);
    };

    return (
        <div class="chat-card">
            <div class="chat-header">
                <h2>Conversational AI Buyer Agent</h2>
                <p>Multi-merchant sports shopping, tailored trade-offs, and interactive checkout.</p>
            </div>

            {/* Quick Sport Preset Chips */}
           

            {/* Message Stream */}
            <div class="chat-messages">
                {messages.map((msg, idx) => (
                    <div key={idx} class={`message message-${msg.sender}`}>
                        {msg.sender === "bot" && <div class="bot-avatar">AI</div>}
                        <div class="message-content">
                            <div>{msg.text.split('\n').map((line, i) => <p key={i}>{line}</p>)}</div>

                            {/* Render Interactive Action Buttons for Bot Responses */}
                            {msg.sender === "bot" && msg.status === "main_product" && (
                                <div class="action-buttons-panel">
                                    <button class="btn-action-primary" onClick={() => handleSend('1')}>
                                        Option 1: Checkout This Product
                                    </button>
                                    <button class="btn-action-secondary" onClick={() => handleSend('2')}>
                                        Option 2: Show Next Product
                                    </button>
                                </div>
                            )}

                            {msg.sender === "bot" && msg.status === "crazy_deals" && (
                                <div class="action-buttons-panel">
                                    <button class="btn-action-primary" onClick={() => handleSend('1')}>
                                        Option 1: Checkout All Recommended Products
                                    </button>
                                    <div class="chip-actions-group">
                                        <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Select specific items:</span>
                                        {msg.data?.recommended_products?.map((item, itemIdx) => (
                                            <button key={itemIdx} class="btn-item-chip" onClick={() => handleSend(`${itemIdx + 1}`)}>
                                                + Add Item #{itemIdx + 1} ({item.name})
                                            </button>
                                        ))}
                                    </div>
                                    <button class="btn-action-decline" onClick={() => handleSend('3')}>
                                        Option 3: Checkout Without Recommended Products
                                    </button>
                                </div>
                            )}

                            {msg.sender === "bot" && msg.status === "decline_reason" && (
                                <div class="action-buttons-panel">
                                    <div class="chip-actions-group">
                                        <button class="btn-action-secondary" onClick={() => handleSend('Price is slightly too high')}>
                                            Price is too high
                                        </button>
                                        <button class="btn-action-secondary" onClick={() => handleSend('Already own these accessories')}>
                                            Already own these accessories
                                        </button>
                                        <button class="btn-action-secondary" onClick={() => handleSend('Only need main equipment today')}>
                                            Only need main item
                                        </button>
                                    </div>
                                </div>
                            )}

                            {msg.sender === "bot" && msg.status === "discounted_deals" && (
                                <div class="action-buttons-panel">
                                    <button class="btn-action-primary" onClick={() => handleSend('1')}>
                                        Option 1: Checkout with Recommended Product
                                    </button>
                                    <div class="chip-actions-group">
                                        {msg.data?.recommended_products?.map((item, itemIdx) => (
                                            <button key={itemIdx} class="btn-item-chip" onClick={() => handleSend(`${itemIdx + 1}`)}>
                                                + Add Item #{itemIdx + 1} ({item.name})
                                            </button>
                                        ))}
                                    </div>
                                    <button class="btn-action-secondary" onClick={() => handleSend('3')}>
                                        Option 3: Checkout Main Item Only
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>

            {/* Input Bar */}
            <div class="chat-input-bar">
                <input
                    type="text"
                    value={inputMsg}
                    onChange={(e) => setInputMsg(e.target.value)}
                    placeholder="Type a message or click an action button above..."
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                />
                <button class="btn-send" onClick={() => handleSend()}>Send</button>
            </div>
        </div>
    );
}
