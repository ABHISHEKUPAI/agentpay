import React, { useState } from 'react';

const API_BASE = "http://localhost:8000";

export default function ChatAgent({ conversationId, cart, setCart, setCurrentOrderData, updateAuditLog }) {
    const [inputMsg, setInputMsg] = useState("");
    const [selectedItemIndices, setSelectedItemIndices] = useState([]);
    const [messages, setMessages] = useState([
        {
            sender: "bot",
            text: "Welcome to AgentPay. I am your Sports-Commerce AI Agent. Tell me your sport requirement and budget, and I will find the optimal setup for you across partner merchants.",
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

    // Helper to format text paragraphs with bold support
    const renderFormattedText = (text) => {
        if (!text) return null;
        
        // Filter out redundant raw option listings if rich cards are shown
        const lines = text.split('\n').filter(line => !line.trim().startsWith('Please select an action'));
        
        return lines.map((line, i) => {
            if (!line.trim()) return <div key={i} style={{ height: '6px' }} />;
            
            // Format bold **text**
            const parts = line.split(/(\*\*.*?\*\*)/g);
            const formatted = parts.map((part, pIdx) => {
                if (part.startsWith('**') && part.endsWith('**')) {
                    return <strong key={pIdx} style={{ color: '#F8FAFC' }}>{part.slice(2, -2)}</strong>;
                }
                return part;
            });

            if (line.includes('⚠️')) {
                return (
                    <div key={i} class="warning-callout">
                        {formatted}
                    </div>
                );
            }

            return <p key={i} class="chat-text-line">{formatted}</p>;
        });
    };

    return (
        <div class="chat-card">
            <div class="chat-header">
                <div class="chat-header-title">
                    <h2>AI Agent</h2>
                </div>
                <p>Multi-merchant product comparison, value trade-offs & bounded budget gating.</p>
            </div>

            {/* Message Stream */}
            <div class="chat-messages">
                {messages.map((msg, idx) => (
                    <div key={idx} class={`message message-${msg.sender}`}>
                        {msg.sender === "bot" && <div class="bot-avatar">AI</div>}
                        <div class="message-content">
                            
                            {/* Text lines */}
                            <div class="message-text-body">
                                {renderFormattedText(msg.text)}
                            </div>

                            {/* RICH PRODUCT CARDS: PRIMARY_OPTIONS & BUDGET_STRETCH */}
                            {msg.sender === "bot" && (msg.action === "PRIMARY_OPTIONS" || msg.action === "BUDGET_STRETCH_PROMPT") && msg.data?.options && (
                                <div class="product-cards-grid">
                                    {msg.data.options.map((item, itemIdx) => {
                                        const optNum = item.option_num || (itemIdx + 1);
                                        const isBestValue = item.option_type === "balanced_deal" || item.option_type === "value_recommendation";
                                        return (
                                            <div key={itemIdx} class={`product-card-rich ${isBestValue ? 'highlight-border' : ''}`}>
                                                <div class="card-top-bar">
                                                    <span class={`opt-badge ${isBestValue ? 'badge-glow' : 'badge-standard'}`}>
                                                        {item.option_type === "balanced_deal" ? "Recommendation 1 — Balanced Deal" :
                                                         item.option_type === "max_main_product" ? "Recommendation 2 — Max Main Product" :
                                                         item.option_type === "value_recommendation" ? "Best-Value Choice" :
                                                         item.option_type === "best_within_budget" ? "Best Product Within Budget" :
                                                         `Recommendation ${optNum}`}
                                                    </span>
                                                    <span class="rating-badge">★ {item.rating}</span>
                                                </div>

                                                <h3 class="product-title">{item.name}</h3>
                                                <div class="merchant-tag">
                                                    Provided by <strong>{item.merchant_name}</strong>
                                                </div>

                                                {/* Price & Savings Display */}
                                                <div class="product-price-section">
                                                    <div class="price-main">
                                                        <span class="price-currency">₹</span>
                                                        <span class="price-value">{item.price.toLocaleString()}</span>
                                                    </div>
                                                    {item.original_price > item.price && (
                                                        <div class="price-savings-wrap">
                                                            <span class="price-original">₹{item.original_price.toLocaleString()}</span>
                                                            <span class="discount-pill">{item.discount_percent}% OFF</span>
                                                        </div>
                                                    )}
                                                </div>

                                                {item.savings > 0 && (
                                                    <div class="savings-text">
                                                        ⚡ You Save <strong>₹{item.savings.toLocaleString()}</strong> on standard list price
                                                    </div>
                                                )}

                                                {/* Attributes */}
                                                {item.attributes && (
                                                    <div class="attributes-row">
                                                        <span class="attr-tag">✨ {item.attributes}</span>
                                                    </div>
                                                )}

                                                {/* Use Case / Reason Card */}
                                                <div class="use-case-box">
                                                    <div class="use-case-title">Why this product:</div>
                                                    <div class="use-case-desc">{item.reason}</div>
                                                </div>

                                                {/* Card Action Button */}
                                                <button 
                                                    class={`btn-card-select ${isBestValue ? 'btn-primary-gradient' : 'btn-secondary-dark'}`}
                                                    onClick={() => handleSend(String(optNum))}
                                                >
                                                    Select Recommendation {optNum} (₹{item.price})
                                                </button>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}

                            {/* RICH PRODUCT CARDS: CROSS_SELL_OPTIONS */}
                            {msg.sender === "bot" && msg.action === "CROSS_SELL_OPTIONS" && msg.data?.products && (
                                <div class="cross-sell-section">
                                    <div class="section-sub-title">Recommended Cross-Merchant Gear for Your Setup:</div>
                                    <div class="product-cards-grid compact-grid">
                                        {msg.data.products.map((item, itemIdx) => (
                                            <div key={itemIdx} class="product-card-compact">
                                                <div class="compact-header">
                                                    <span class="item-index-badge">#{itemIdx + 1}</span>
                                                    <span class="rating-badge-sm">★ {item.rating}</span>
                                                </div>
                                                <div class="compact-title">{item.name}</div>
                                                <div class="compact-merchant">from {item.merchant_name}</div>
                                                
                                                <div class="compact-price-row">
                                                    <span class="compact-price">₹{item.price}</span>
                                                    {item.original_price > item.price && (
                                                        <span class="compact-orig">₹{item.original_price}</span>
                                                    )}
                                                </div>

                                                {item.personalized_reason && (
                                                    <div class="compact-reason">{item.personalized_reason}</div>
                                                )}
                                            </div>
                                        ))}
                                    </div>

                                    {msg.data.bundle_savings > 0 && (
                                        <div class="bundle-savings-banner">
                                            <strong>Bundle Savings:</strong> You save <strong>₹{msg.data.bundle_savings}</strong> off standard list prices across items!
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* RICH PRODUCT CARD: LOW_COST_ALTERNATIVE */}
                            {msg.sender === "bot" && msg.action === "LOW_COST_ALTERNATIVE" && msg.data?.product && (
                                <div class="product-cards-grid single-grid">
                                    <div class="product-card-rich low-cost-card">
                                        <div class="card-top-bar">
                                            <span class="opt-badge badge-glow">Lower-Cost Alternative Essential</span>
                                            <span class="rating-badge">★ {msg.data.product.rating}</span>
                                        </div>
                                        <h3 class="product-title">{msg.data.product.name}</h3>
                                        <div class="merchant-tag">Provided by <strong>{msg.data.product.merchant_name}</strong></div>

                                        <div class="product-price-section">
                                            <div class="price-main">
                                                <span class="price-currency">₹</span>
                                                <span class="price-value">{msg.data.product.price}</span>
                                            </div>
                                        </div>

                                        <div class="use-case-box">
                                            <div class="use-case-title">Why consider this:</div>
                                            <div class="use-case-desc">{msg.data.product.personalized_reason || msg.data.product.reason}</div>
                                        </div>

                                        <button 
                                            class="btn-card-select btn-primary-gradient"
                                            onClick={() => handleSend('Yes, add lower-cost item')}
                                        >
                                            Add This Item (₹{msg.data.product.price})
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* PRIMARY_OPTIONS Action Panel
                            {msg.sender === "bot" && msg.action === "PRIMARY_OPTIONS" && (
                                <div class="action-buttons-panel">
                                    <button class="btn-action-primary" onClick={() => handleSend('1')}>
                                        Choose Recommendation 1 (Best Value)
                                    </button>
                                    {msg.data?.options?.length > 1 && (
                                        <button class="btn-action-secondary" onClick={() => handleSend('2')}>
                                            Choose Recommendation 2 (Max Product)
                                        </button>
                                    )}
                                    <button class="btn-action-secondary" onClick={() => handleSend('3')}>
                                        Explore Other Products / Priorities
                                    </button>
                                </div>
                            )} */}

                            {/* BUDGET_STRETCH_PROMPT Action Panel */}
                            {/* {msg.sender === "bot" && msg.action === "BUDGET_STRETCH_PROMPT" && (
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
                            )} */}

                            {/* ASK_PREFERENCE Chips Panel */}
                            {msg.sender === "bot" && msg.action === "ASK_PREFERENCE" && (
                                <div class="action-buttons-panel">
                                    <div class="chip-actions-group">
                                        <button class="btn-action-chip" onClick={() => handleSend('Rating')}>
                                            Highest Rating
                                        </button>
                                        <button class="btn-action-chip" onClick={() => handleSend('Comfort')}>
                                            Comfort & Cushioning
                                        </button>
                                        <button class="btn-action-chip" onClick={() => handleSend('Performance')}>
                                            Pro Performance
                                        </button>
                                        <button class="btn-action-chip" onClick={() => handleSend('Price')}>
                                            Best Price Deal
                                        </button>
                                        <button class="btn-action-chip" onClick={() => handleSend('Durability')}>
                                            Durability
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* CROSS_SELL_OPTIONS Action Panel */}
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

                            {/* INDIVIDUAL_SELECT_PROMPT Checkboxes */}
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
                                                    onClick={() => toggleItemSelection(itemIdx)}
                                                >
                                                    {isSelected ? '✓' : '+'} #{itemNo} {item.name} (₹{item.price})
                                                </button>
                                            );
                                        })}
                                    </div>
                                    <button class="btn-action-primary" style={{ marginTop: '10px' }} onClick={handleAddSelectedItems}>
                                        Add Selected Items ({selectedItemIndices.length} Selected)
                                    </button>
                                </div>
                            )}

                            {/* DECLINE_REASON_PROMPT Chips Panel */}
                            {msg.sender === "bot" && msg.action === "DECLINE_REASON_PROMPT" && (
                                <div class="action-buttons-panel">
                                    <div class="chip-actions-group">
                                        <button class="btn-action-chip" onClick={() => handleSend('1')}>
                                            1. Too expensive
                                        </button>
                                        <button class="btn-action-chip" onClick={() => handleSend('2')}>
                                            2. Not relevant to me
                                        </button>
                                        <button class="btn-action-chip" onClick={() => handleSend('3')}>
                                            3. I don't like the brand
                                        </button>
                                        <button class="btn-action-chip" onClick={() => handleSend('4')}>
                                            4. I don't need additional products
                                        </button>
                                        <button class="btn-action-chip" onClick={() => handleSend('5')}>
                                            5. Other
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* LOW_COST_ALTERNATIVE Panel */}
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

                            {/* PAYMENT_CONFIRMATION_PROMPT Panel */}
                            {msg.sender === "bot" && msg.action === "PAYMENT_CONFIRMATION_PROMPT" && (
                                <div class="action-buttons-panel">
                                    <button class="btn-action-primary btn-pay-glow" onClick={() => handleSend('Confirm and Pay')}>
                                        Confirm & Proceed to Razorpay Test Payment
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
                    placeholder="Type your message or response..."
                    onChange={(e) => setInputMsg(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                />
                <button class="btn-send" onClick={() => handleSend()}>Send</button>
            </div>
        </div>
    );
}
