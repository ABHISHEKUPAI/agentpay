import React, { useState } from 'react';
import ChatAgent from './components/ChatAgent';
import CartDrawer from './components/CartDrawer';
import RazorpayModal from './components/RazorpayModal';
import MerchantDashboard from './components/MerchantDashboard';

const API_BASE = "http://localhost:8000";

export default function App() {
    const [activeTab, setActiveTab] = useState('shopper');
    const [conversationId] = useState(() => "conv_" + Math.random().toString(36).substring(2, 9));
    const [cart, setCart] = useState([]);
    const [currentOrderData, setCurrentOrderData] = useState(null);
    const [isRzpOpen, setIsRzpOpen] = useState(false);
    const [auditLogs, setAuditLogs] = useState(null);

    const handlePaymentSuccess = () => {
        setIsRzpOpen(false);
        setCart([]);
        alert(`Payment Successful via Razorpay Test Mode!\nOrder ID: ${currentOrderData?.order_id}\nAmount Paid: ₹${currentOrderData?.final_amount}`);
    };

    const handleTabSwitch = async (tab) => {
        setActiveTab(tab);
        if (tab === 'merchant' && cart && cart.length > 0) {
            try {
                await fetch(`${API_BASE}/recovery/register-abandoned`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        session_id: conversationId,
                        cart: cart,
                        user_goal: "active shopper session"
                    })
                });
            } catch (err) {
                console.error("Failed to register abandoned cart on tab switch:", err);
            }
        }
    };

    return (
        <div className="app-container">
            {/* Top Navigation */}
            <header className="navbar">
                <div className="logo">
                    <span className="logo-text">Agent<span className="highlight">Pay</span></span>
                </div>
                
                <nav className="nav-tabs">
                    <button
                        className={`tab-btn ${activeTab === 'shopper' ? 'active' : ''}`}
                        onClick={() => handleTabSwitch('shopper')}
                    >
                        Shopper AI Agent
                    </button>
                    <button
                        className={`tab-btn ${activeTab === 'merchant' ? 'active' : ''}`}
                        onClick={() => handleTabSwitch('merchant')}
                    >
                        Revenue & Recovery Dashboard
                    </button>
                </nav>
            </header>

            {/* Tab 1: Shopper AI Agent (Preserved in DOM) */}
            <main className="shopper-grid" style={{ display: activeTab === 'shopper' ? 'grid' : 'none' }}>
                <ChatAgent
                    conversationId={conversationId}
                    cart={cart}
                    setCart={setCart}
                    setCurrentOrderData={setCurrentOrderData}
                    updateAuditLog={setAuditLogs}
                />
                <CartDrawer
                    conversationId={conversationId}
                    cart={cart}
                    openRazorpayModal={() => setIsRzpOpen(true)}
                    setCurrentOrderData={setCurrentOrderData}
                    updateAuditLog={setAuditLogs}
                />
            </main>

            {/* Tab 2: Merchant AI Dashboard (Preserved in DOM) */}
            <div style={{ display: activeTab === 'merchant' ? 'block' : 'none' }}>
                <MerchantDashboard auditLogs={auditLogs} />
            </div>

            {/* Razorpay Test Modal */}
            <RazorpayModal
                isOpen={isRzpOpen}
                onClose={() => setIsRzpOpen(false)}
                orderData={currentOrderData}
                onPaymentSuccess={handlePaymentSuccess}
            />
        </div>
    );
}
