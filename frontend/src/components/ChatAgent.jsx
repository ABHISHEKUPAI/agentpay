import React, { useState } from 'react';

const API_BASE = "http://localhost:8000";

export default function ChatAgent({ conversationId, cart, setCart, setCurrentOrderData, updateAuditLog }) {
    const [inputMsg, setInputMsg] = useState("");
    const [selectedItemIndices, setSelectedItemIndices] = useState([]);
    const [messages, setMessages] = useState([
        {
            sender: "bot",
            text: "Welcome to AgentPay. I am your Sports-Commerce Shopping AI Agent. State your sport requirement and budget, and I will construct the optimal setup for you across partner merchants.",
            status: "initial"
        }
    ]);

    const handleSend = async (textToSend) => {
        const query = textToSend || inputMsg;
        if (!query.trim()) return;

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

            setMessages(prev => [
                ...prev,
                {
                    sender: "bot",
                    text: data.message,
                    status: data.status,
                    action: data.action,
                    data: data
                }
            ]);

            if (data.cart) {
                setCart(data.cart);
            }

            if (data.action === "PAYMENT_SUCCESS" || data.status === "complete" || data.razorpay_order) {
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

    const toggleItemSelection = (idx) => {
        const itemNo = idx + 1;
        if (selectedItemIndices.includes(itemNo)) {
            setSelectedItemIndices(selectedItemIndices.filter(i => i !== itemNo));
        } else {
            setSelectedItemIndices([...selectedItemIndices, itemNo]);
        }
    };

    const handleAddSelectedItems = () => {
        if (selectedItemIndices.length === 0) {
            alert("Please select at least one item.");
            return;
        }
        handleSend(selectedItemIndices.join(", "));
        setSelectedItemIndices([]);
    };

    const handlePreset = (presetText) => {
        handleSend(presetText);
    };

    return (
        <div class="chat-card">
            <div class="chat-header">
                <h2>Sports-Commerce AI Buyer Agent</h2>
                <p>Multi-merchant product comparison, value trade-offs, and payment gating.</p>
            </div>

            {/* Message Stream */}
            <div class="chat-messages">
                {messages.map((msg, idx) => (
                    <div key={idx} class={`message message-${msg.sender}`}>
                        {msg.sender === "bot" && <div class="bot-avatar">AI</div>}
                        <div class="message-content">
                            <div>{msg.text.split('\n').map((line, i) => <p key={i}>{line}</p>)}</div>

                            {/* PRIMARY_OPTIONS buttons */}
                            {msg.sender === "bot" && msg.action === "PRIMARY_OPTIONS" && (
                                <div class="action-buttons-panel">
                                    <button class="btn-action-primary" onClick={() => handleSend('1')}>
                                        Choose Best-Value Recommendation
                                    </button>
                                    {msg.data?.options?.length > 1 && (
                                        <button class="btn-action-secondary" onClick={() => handleSend('2')}>
                                        Choose Best Product Within Budget
                                        </button>
                                    )}
                                    <button class="btn-action-secondary" onClick={() => handleSend('3')}>
                                        Explore Other Products
                                    </button>
                                </div>
                            )}

                            {/* BUDGET_STRETCH_PROMPT button */}
                            {msg.sender === "bot" && msg.action === "BUDGET_STRETCH_PROMPT" && (
                                <div class="action-buttons-panel">
                                    {msg.data?.options?.length > 1 ? (
                                        <>
                                            <button class="btn-action-primary" onClick={() => handleSend('1')}>
                                                Approve Stretch & Proceed for Recommendation 1
                                            </button>
                                            <button class="btn-action-secondary" onClick={() => handleSend('2')}>
                                                Approve Stretch & Proceed for Recommendation 2
                                            </button>
                                        </>
                                    ) : (
                                        <button class="btn-action-primary" onClick={() => handleSend('1')}>
                                            Approve Stretch & Proceed
                                        </button>
                                    )}
                                </div>
                            )}

                            {/* ASK_PREFERENCE chips */}
                            {msg.sender === "bot" && msg.action === "ASK_PREFERENCE" && (
                                <div class="action-buttons-panel">
                                    <div class="chip-actions-group">
                                        <button class="btn-action-secondary" onClick={() => handleSend('Rating')}>
                                            Highest Rating
                                        </button>
                                        <button class="btn-action-secondary" onClick={() => handleSend('Comfort')}>
                                            Comfort & Cushioning
                                        </button>
                                        <button class="btn-action-secondary" onClick={() => handleSend('Performance')}>
                                            Pro Performance
                                        </button>
                                        <button class="btn-action-secondary" onClick={() => handleSend('Price')}>
                                            Cheapest Value
                                        </button>
                                        <button class="btn-action-secondary" onClick={() => handleSend('Durability')}>
                                            Durability
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* CROSS_SELL_OPTIONS buttons */}
                            {msg.sender === "bot" && msg.action === "CROSS_SELL_OPTIONS" && (
                                <div class="action-buttons-panel">
                                    <button class="btn-action-primary" onClick={() => handleSend('1')}>
                                        Add All Recommended Products
                                    </button>
                                    <button class="btn-action-secondary" onClick={() => handleSend('2')}>
                                        Select Individually
                                    </button>
                                    <button class="btn-action-decline" onClick={() => handleSend('3')}>
                                        Checkout Without Recommendations
                                    </button>
                                </div>
                            )}

                            {/* INDIVIDUAL_SELECT_PROMPT checkboxes */}
                            {msg.sender === "bot" && msg.action === "INDIVIDUAL_SELECT_PROMPT" && (
                                <div class="action-buttons-panel">
                                    <div class="chip-actions-group">
                                        {msg.data?.products?.map((item, itemIdx) => {
                                            const itemNo = itemIdx + 1;
                                            const isSelected = selectedItemIndices.includes(itemNo);
                                            return (
                                                <button
                                                    key={itemIdx}
                                                    class={`btn-item-chip ${isSelected ? 'active' : ''}`}
                                                    style={{ background: isSelected ? 'var(--primary)' : 'rgba(2, 132, 199, 0.15)', color: '#FFF' }}
                                                    onClick={() => toggleItemSelection(itemIdx)}
                                                >
                                                    {isSelected ? '[✓]' : '[ ]'} {itemNo}. {item.name} — ₹{item.price}
                                                </button>
                                            );
                                        })}
                                    </div>
                                    <button class="btn-action-primary" style={{ marginTop: '10px' }} onClick={handleAddSelectedItems}>
                                        Add Selected Items
                                    </button>
                                </div>
                            )}

                            {/* DECLINE_REASON_PROMPT buttons */}
                            {msg.sender === "bot" && msg.action === "DECLINE_REASON_PROMPT" && (
                                <div class="action-buttons-panel">
                                    <div class="chip-actions-group">
                                        <button class="btn-action-secondary" onClick={() => handleSend('1')}>
                                            1. Too expensive
                                        </button>
                                        <button class="btn-action-secondary" onClick={() => handleSend('2')}>
                                            2. Not relevant to me
                                        </button>
                                        <button class="btn-action-secondary" onClick={() => handleSend('3')}>
                                            3. I don't like the brand
                                        </button>
                                        <button class="btn-action-secondary" onClick={() => handleSend('4')}>
                                            4. I don't need additional products
                                        </button>
                                        <button class="btn-action-secondary" onClick={() => handleSend('5')}>
                                            5. Other
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* LOW_COST_ALTERNATIVE buttons */}
                            {msg.sender === "bot" && msg.action === "LOW_COST_ALTERNATIVE" && (
                                <div class="action-buttons-panel">
                                    <button class="btn-action-primary" onClick={() => handleSend('Yes, add lower-cost item')}>
                                        Add Lower-Cost Item
                                    </button>
                                    <button class="btn-action-secondary" onClick={() => handleSend('No, proceed to checkout')}>
                                        Proceed to Checkout Only
                                    </button>
                                </div>
                            )}

                            {/* PAYMENT_CONFIRMATION_PROMPT button */}
                            {msg.sender === "bot" && msg.action === "PAYMENT_CONFIRMATION_PROMPT" && (
                                <div class="action-buttons-panel">
                                    <button class="btn-action-primary" onClick={() => handleSend('Confirm and Pay')}>
                                        Confirm & Proceed to Payment
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
                    placeholder="Type a message or click an action button..."
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                />
                <button class="btn-send" onClick={() => handleSend()}>Send</button>
            </div>
        </div>
    );
}
