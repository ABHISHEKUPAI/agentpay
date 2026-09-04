import React from 'react';

const API_BASE = "http://localhost:8000";

export default function CartDrawer({ conversationId, cart, openRazorpayModal, setCurrentOrderData, updateAuditLog }) {
    const totalSubtotal = cart.reduce((acc, item) => acc + (item.original_price || item.price), 0);
    const totalFinal = cart.reduce((acc, item) => acc + item.price, 0);
    const totalSavings = Math.round(totalSubtotal - totalFinal);

    const handleProceedCheckout = async () => {
        try {
            const res = await fetch(`${API_BASE}/buyer/checkout`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    conversation_id: conversationId,
                    cart: cart
                })
            });
            const data = await res.json();
            if (data.status === "order_created") {
                setCurrentOrderData(data);
                if (data.audit_trail) updateAuditLog(data.audit_trail);
                openRazorpayModal();
            }
        } catch (err) {
            console.error(err);
            alert("Failed to initiate Razorpay order.");
        }
    };

    return (
        <div class="cart-side-panel">
            <div class="panel-header">
                <h3>Order Summary & Cart</h3>
                <span class="cart-count-badge">{cart.length} item(s)</span>
            </div>

            <div class="cart-items-list">
                {cart.length === 0 ? (
                    <div class="empty-cart">
                        <p>Your cart is empty. Select products from the chat agent to build your setup.</p>
                    </div>
                ) : (
                    cart.map((item, idx) => (
                        <div key={idx} class="cart-item-card">
                            <div>
                                <div class="cart-item-name">{item.name}</div>
                                <div class="cart-item-merchant">{item.merchant_name || "Merchant"}</div>
                            </div>
                            <div class="cart-item-price">₹{Math.round(item.price)}</div>
                        </div>
                    ))
                )}
            </div>

            {cart.length > 0 && (
                <div class="cart-summary">
                    <div class="summary-row">
                        <span>Subtotal (List Price):</span>
                        <span>₹{Math.round(totalSubtotal)}</span>
                    </div>
                    <div class="summary-row discount-row">
                        <span>Total Savings & Discounts:</span>
                        <span>-₹{totalSavings}</span>
                    </div>
                    <hr class="divider" />
                    <div class="summary-row total-row">
                        <span>Final Amount Payable:</span>
                        <span>₹{Math.round(totalFinal)}</span>
                    </div>

                    {/* <button class="btn-checkout" onClick={handleProceedCheckout}>
                        Pay via Razorpay Test Mode
                    </button> */}
                </div>
            )}
        </div>
    );
}
