import React from 'react';

export default function RazorpayModal({ isOpen, onClose, orderData, onPaymentSuccess }) {
    if (!isOpen || !orderData) return null;

    return (
        <div class="modal-overlay">
            <div class="modal-card">
                <div class="modal-header">
                    <span class="rzp-logo">Razorpay <span class="test-tag">TEST MODE</span></span>
                    <button class="close-modal" onClick={onClose}>✕</button>
                </div>
                <div class="modal-body">
                    <div class="order-summary-box">
                        <p class="merchant-name">AgentPay AI Commerce</p>
                        <h2>₹{orderData.final_amount}</h2>
                        <p class="order-id-label">Order ID: {orderData.order_id}</p>
                    </div>
                    <div class="payment-methods">
                        <button class="pay-method-btn" onClick={onPaymentSuccess}>
                            <span>Pay with Test Card / UPI</span>
                            <span class="arrow">→</span>
                        </button>
                    </div>
                    <div class="rzp-security-note">
                        Secured by Razorpay 256-bit Encryption • Audit Trail Logged
                    </div>
                </div>
            </div>
        </div>
    );
}
