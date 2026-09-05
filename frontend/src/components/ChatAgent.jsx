import React, { useState } from 'react';

const API_BASE = "http://localhost:8000";

export default function ChatAgent({ conversationId, cart, setCart, setCurrentOrderData, updateAuditLog, openRazorpayModal }) {
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
        const query = typeof textToSend === 'string' ? textToSend : (textToSend != null ? String(textToSend) : inputMsg);
        if (!query || !query.trim()) return;

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
                if (openRazorpayModal) openRazorpayModal();
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

    const handleCheckoutModalTrigger = () => {
        handleSend("Yes");
    };

    // Helper to format text paragraphs with bold support
    const renderFormattedText = (text) => {
        if (!text) return null;
        const strText = typeof text === 'string' ? text : String(text);
        
        // Filter out redundant raw option listings if rich cards are shown
        const lines = strText.split('\n').filter(line => !line.trim().startsWith('Please select an action'));
        
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
                    <div key={i} className="warning-callout">
                        {formatted}
                    </div>
                );
            }

            return <p key={i} className="chat-text-line">{formatted}</p>;
        });
    };

    return (
        <div className="chat-card">
            <div className="chat-header">
                <div className="chat-header-title">
                    <h2>AI Agent</h2>
                </div>
                <p>Multi-merchant product comparison, value trade-offs & bounded budget gating.</p>
            </div>

            {/* Message Stream */}
            <div className="chat-messages">
                {messages.map((msg, idx) => (
                    <div key={idx} className={`message message-${msg.sender}`}>
                        {msg.sender === "bot" && <div className="bot-avatar">AI</div>}
                        <div className="message-content">
                            
                            {/* Text lines */}
                            <div className="message-text-body">
                                {renderFormattedText(msg.text)}
                            </div>

                            {/* RICH PRODUCT CARDS: PRIMARY_OPTIONS & BUDGET_STRETCH */}
                            {msg.sender === "bot" && (msg.action === "PRIMARY_OPTIONS" || msg.action === "BUDGET_STRETCH_PROMPT") && msg.data?.options && (
                                <div className="product-cards-grid">
                                    {msg.data.options.map((item, itemIdx) => {
                                        const optNum = item.option_num || (itemIdx + 1);
                                        const isBestValue = item.option_type === "balanced_deal" || item.option_type === "value_recommendation";
                                        return (
                                            <div key={itemIdx} className={`product-card-rich ${isBestValue ? 'highlight-border' : ''}`}>
                                                <div className="card-top-bar">
                                                    <span className={`opt-badge ${isBestValue ? 'badge-glow' : 'badge-standard'}`}>
                                                        {item.option_type === "balanced_deal" ? "Recommendation 1 — Balanced Deal" :
                                                         item.option_type === "max_main_product" ? "Recommendation 2 — Max Main Product" :
                                                         item.option_type === "value_recommendation" ? "Best-Value Choice" :
                                                         item.option_type === "best_within_budget" ? "Best Product Within Budget" :
                                                         `Recommendation ${optNum}`}
                                                    </span>
                                                    <span className="rating-badge">★ {item.rating}</span>
                                                </div>

                                                <h3 className="product-title">{item.name}</h3>
                                                <div className="merchant-tag">
                                                    Provided by <strong>{item.merchant_name}</strong>
                                                </div>

                                                {/* Price & Savings Display */}
                                                <div className="product-price-section">
                                                    <div className="price-main">
                                                        <span className="price-currency">₹</span>
                                                        <span className="price-value">
                                                            {typeof item?.price === 'number' ? item.price.toLocaleString() : (item?.price || 0)}
                                                        </span>
                                                    </div>
                                                    {item?.original_price > item?.price && (
                                                        <div className="price-savings-wrap">
                                                            <span className="price-original">
                                                                ₹{typeof item.original_price === 'number' ? item.original_price.toLocaleString() : item.original_price}
                                                            </span>
                                                            <span className="discount-pill">{item.discount_percent}% OFF</span>
                                                        </div>
                                                    )}
                                                </div>

                                                {item?.savings > 0 && (
                                                    <div className="savings-text">
                                                        You Save <strong>₹{typeof item.savings === 'number' ? item.savings.toLocaleString() : item.savings}</strong> on standard list price
                                                    </div>
                                                )}

                                                {/* Attributes */}
                                                {item?.attributes && (
                                                    <div className="attributes-row">
                                                        <span className="attr-tag">✨ {item.attributes}</span>
                                                    </div>
                                                )}

                                                {/* Use Case / Reason Card */}
                                                <div className="use-case-box">
                                                    <div className="use-case-title">Why this product:</div>
                                                    <div className="use-case-desc">{item?.reason}</div>
                                                </div>

                                                {/* Card Action Button */}
                                                <button 
                                                    className={`btn-card-select ${isBestValue ? 'btn-primary-gradient' : 'btn-secondary-dark'}`}
                                                    onClick={() => handleSend(String(optNum))}
                                                >
                                                    Select Recommendation {optNum} (₹{item?.price})
                                                </button>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}

                            {/* RICH PRODUCT CARDS: CROSS_SELL_OPTIONS */}
                            {msg.sender === "bot" && msg.action === "CROSS_SELL_OPTIONS" && Array.isArray(msg.data?.products) && (
                                <div className="cross-sell-section">
                                    <div className="section-sub-title">Recommended Cross-Merchant Gear for Your Setup:</div>
                                    <div className="product-cards-grid compact-grid">
                                        {msg.data.products.map((item, itemIdx) => (
                                            <div key={itemIdx} className="product-card-compact">
                                                <div className="compact-header">
                                                    <span className="item-index-badge">#{itemIdx + 1}</span>
                                                    <span className="rating-badge-sm">★ {item?.rating}</span>
                                                </div>
                                                <div className="compact-title">{item?.name}</div>
                                                <div className="compact-merchant">from {item?.merchant_name}</div>
                                                
                                                <div className="compact-price-row">
                                                    <span className="compact-price">₹{item?.price}</span>
                                                    {item?.original_price > item?.price && (
                                                        <span className="compact-orig">₹{item?.original_price}</span>
                                                    )}
                                                </div>

                                                {item?.personalized_reason && (
                                                    <div className="compact-reason">{item.personalized_reason}</div>
                                                )}
                                            </div>
                                        ))}
                                    </div>

                                    {msg.data?.bundle_savings > 0 && (
                                        <div className="bundle-savings-banner">
                                            <strong>Bundle Savings:</strong> You save <strong>₹{msg.data.bundle_savings}</strong> off standard list prices across items!
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* RICH PRODUCT CARD: LOW_COST_ALTERNATIVE */}
                            {msg.sender === "bot" && msg.action === "LOW_COST_ALTERNATIVE" && msg.data?.product && (
                                <div className="product-cards-grid single-grid">
                                    <div className="product-card-rich low-cost-card">
                                        <div className="card-top-bar">
                                            <span className="opt-badge badge-glow">Lower-Cost Alternative Essential</span>
                                            <span className="rating-badge">★ {msg.data.product.rating}</span>
                                        </div>
                                        <h3 className="product-title">{msg.data.product.name}</h3>
                                        <div className="merchant-tag">Provided by <strong>{msg.data.product.merchant_name}</strong></div>

                                        <div className="product-price-section">
                                            <div className="price-main">
                                                <span className="price-currency">₹</span>
                                                <span className="price-value">{msg.data.product.price}</span>
                                            </div>
                                        </div>

                                        <div className="use-case-box">
                                            <div className="use-case-title">Why consider this:</div>
                                            <div className="use-case-desc">{msg.data.product.personalized_reason || msg.data.product.reason}</div>
                                        </div>

                                        <button 
                                            className="btn-card-select btn-primary-gradient"
                                            onClick={() => handleSend('Yes, add lower-cost item')}
                                        >
                                            Add This Item (₹{msg.data.product.price})
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* ASK_PREFERENCE Chips Panel */}
                            {msg.sender === "bot" && msg.action === "ASK_PREFERENCE" && (
                                <div className="action-buttons-panel">
                                    <div className="chip-actions-group">
                                        <button className="btn-action-chip" onClick={() => handleSend('Rating')}>
                                            Highest Rating
                                        </button>
                                        <button className="btn-action-chip" onClick={() => handleSend('Comfort')}>
                                            Comfort & Cushioning
                                        </button>
                                        <button className="btn-action-chip" onClick={() => handleSend('Performance')}>
                                            Pro Performance
                                        </button>
                                        <button className="btn-action-chip" onClick={() => handleSend('Price')}>
                                            Best Price Deal
                                        </button>
                                        <button className="btn-action-chip" onClick={() => handleSend('Durability')}>
                                            Durability
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* CROSS_SELL_OPTIONS Action Panel */}
                            {msg.sender === "bot" && msg.action === "CROSS_SELL_OPTIONS" && (
                                <div className="action-buttons-panel">
                                    <button className="btn-action-primary" onClick={() => handleSend('1')}>
                                        Add All Recommended Products
                                    </button>
                                    <button className="btn-action-secondary" onClick={() => handleSend('2')}>
                                        Select Individually
                                    </button>
                                    <button className="btn-action-decline" onClick={() => handleSend('3')}>
                                        Checkout Without Recommendations
                                    </button>
                                </div>
                            )}

                            {/* INDIVIDUAL_SELECT_PROMPT Checkboxes */}
                            {msg.sender === "bot" && msg.action === "INDIVIDUAL_SELECT_PROMPT" && (
                                <div className="action-buttons-panel">
                                    <div className="chip-actions-group">
                                        {(Array.isArray(msg.data?.products) ? msg.data.products : []).map((item, itemIdx) => {
                                            const itemNo = itemIdx + 1;
                                            const isSelected = selectedItemIndices.includes(itemNo);
                                            return (
                                                <button
                                                    key={itemIdx}
                                                    className={`btn-item-chip ${isSelected ? 'active' : ''}`}
                                                    onClick={() => toggleItemSelection(itemIdx)}
                                                >
                                                    {isSelected ? '✓' : '+'} #{itemNo} {item?.name} (₹{item?.price})
                                                </button>
                                            );
                                        })}
                                    </div>
                                    <button className="btn-action-primary" style={{ marginTop: '10px' }} onClick={handleAddSelectedItems}>
                                        Add Selected Items ({selectedItemIndices.length} Selected)
                                    </button>
                                </div>
                            )}

                            {/* DECLINE_REASON_PROMPT Chips Panel */}
                            {msg.sender === "bot" && msg.action === "DECLINE_REASON_PROMPT" && (
                                <div className="action-buttons-panel">
                                    <div className="chip-actions-group">
                                        <button className="btn-action-chip" onClick={() => handleSend('1')}>
                                            1. Too expensive
                                        </button>
                                        <button className="btn-action-chip" onClick={() => handleSend('2')}>
                                            2. Not relevant to me
                                        </button>
                                        <button className="btn-action-chip" onClick={() => handleSend('3')}>
                                            3. I don't like the brand
                                        </button>
                                        <button className="btn-action-chip" onClick={() => handleSend('4')}>
                                            4. I don't need additional products
                                        </button>
                                        <button className="btn-action-chip" onClick={() => handleSend('5')}>
                                            5. Other
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* LOW_COST_ALTERNATIVE Panel */}
                            {msg.sender === "bot" && msg.action === "LOW_COST_ALTERNATIVE" && (
                                <div className="action-buttons-panel">
                                    <button className="btn-action-primary" onClick={() => handleSend('Yes, add lower-cost item')}>
                                        Add Lower-Cost Item
                                    </button>
                                    <button className="btn-action-secondary" onClick={() => handleSend('No, proceed to checkout')}>
                                        Proceed to Checkout Only
                                    </button>
                                </div>
                            )}

                            {/* PAYMENT_CONFIRMATION_PROMPT Panel */}
                            {msg.sender === "bot" && msg.action === "PAYMENT_CONFIRMATION_PROMPT" && (
                                <div className="action-buttons-panel">
                                    <button className="btn-action-primary btn-pay-glow" onClick={handleCheckoutModalTrigger}>
                                        Confirm & Proceed to Razorpay Test Payment
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>

            {/* Input Bar */}
            <div className="chat-input-bar">
                <input
                    type="text"
                    value={inputMsg}
                    placeholder="Type your message or response..."
                    onChange={(e) => setInputMsg(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                />
                <button className="btn-send" onClick={() => handleSend()}>Send</button>
            </div>
        </div>
    );
}
