import React, { useState } from 'react';
import ChatAgent from './components/ChatAgent';
import CartDrawer from './components/CartDrawer';
import RazorpayModal from './components/RazorpayModal';
import MerchantDashboard from './components/MerchantDashboard';

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

    return (
        <div class="app-container">
            {/* Top Navigation */}
            <header class="navbar">
                <div class="logo">
                    <span class="logo-text">Agent<span class="highlight">Pay</span></span>
                    
                </div>
                
                <nav class="nav-tabs">
                    <button
                        class={`tab-btn ${activeTab === 'shopper' ? 'active' : ''}`}
                        onClick={() => setActiveTab('shopper')}
                    >
                        Shopper AI Agent
                    </button>
                    <button
                        class={`tab-btn ${activeTab === 'merchant' ? 'active' : ''}`}
                        onClick={() => setActiveTab('merchant')}
                    >
                        Revenue & Recovery Dashboard
                    </button>
                </nav>

              
            </header>

            {/* Tab 1: Shopper AI Agent */}
            {activeTab === 'shopper' && (
                <main class="shopper-grid">
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
            )}

            {/* Tab 2: Merchant AI Dashboard */}
            {activeTab === 'merchant' && (
                <MerchantDashboard auditLogs={auditLogs} />
            )}

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
