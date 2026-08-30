const API_BASE = "http://localhost:8000";

let conversationId = "conv_" + Math.random().toString(36).substring(2, 9);
let cartItems = [];
let currentOrderData = null;

// Initialize App
document.addEventListener("DOMContentLoaded", () => {
    fetchAbandonedCarts();
    fetchAnalytics();
});

// Tab Navigation
function switchTab(tabName) {
    document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(content => content.classList.remove("active"));

    document.getElementById(`tab-${tabName}`).classList.add("active");
    document.getElementById(`content-${tabName}`).classList.add("active");

    if (tabName === "merchant") {
        fetchAbandonedCarts();
        fetchAnalytics();
    }
}

// Preset Chips
function sendPreset(text) {
    document.getElementById("user-input").value = text;
    sendMessage();
}

// Chat API Communication
async function sendMessage() {
    const input = document.getElementById("user-input");
    const message = input.value.trim();
    if (!message) return;

    appendMessage("user", message);
    input.value = "";

    try {
        const response = await fetch(`${API_BASE}/buyer/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                conversation_id: conversationId,
                message: message
            })
        });

        const data = await response.json();
        handleBotResponse(data);
    } catch (err) {
        console.error(err);
        appendMessage("bot", "⚠️ Unable to connect to AgentPay backend. Make sure FastAPI server is running on http://localhost:8000!");
    }
}

// Render Messages & Products
function handleBotResponse(data) {
    appendMessage("bot", data.message);

    if (data.cart) {
        cartItems = data.cart;
        updateCartUI();
    }

    if (data.status === "complete" || data.razorpay_order) {
        currentOrderData = data.razorpay_order || data;
        updateAuditLogView(data.audit_trail || data.razorpay_order?.audit_trail);
    }
}

function appendMessage(sender, text) {
    const messagesContainer = document.getElementById("chat-messages");
    const messageDiv = document.createElement("div");
    messageDiv.className = `message message-${sender}`;

    if (sender === "bot") {
        messageDiv.innerHTML = `
            <div class="bot-avatar">🤖</div>
            <div class="message-content">${formatMessageText(text)}</div>
        `;
    } else {
        messageDiv.innerHTML = `
            <div class="message-content">${text}</div>
        `;
    }

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function formatMessageText(text) {
    return text
        .replace(/\n/g, "<br>")
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
}

// Cart Management
function updateCartUI() {
    const cartList = document.getElementById("cart-items-list");
    const cartCount = document.getElementById("cart-count");
    const summaryBox = document.getElementById("cart-summary");

    cartCount.textContent = `${cartItems.length} item(s)`;

    if (cartItems.length === 0) {
        cartList.innerHTML = `
            <div class="empty-cart">
                <span class="empty-icon">🛒</span>
                <p>Your cart is empty. Select products from the chat agent to start building your order!</p>
            </div>
        `;
        summaryBox.style.display = "none";
        return;
    }

    cartList.innerHTML = "";
    let totalSubtotal = 0;
    let totalFinal = 0;

    cartItems.forEach(item => {
        const origPrice = item.original_price || item.price;
        totalSubtotal += origPrice;
        totalFinal += item.price;

        const card = document.createElement("div");
        card.className = "cart-item-card";
        card.innerHTML = `
            <div>
                <div class="cart-item-name">${item.name}</div>
                <div class="cart-item-merchant">${item.merchant_name || "Merchant"}</div>
            </div>
            <div class="cart-item-price">₹${Math.round(item.price)}</div>
        `;
        cartList.appendChild(card);
    });

    const totalSavings = Math.round(totalSubtotal - totalFinal);

    document.getElementById("summary-subtotal").textContent = `₹${Math.round(totalSubtotal)}`;
    document.getElementById("summary-savings").textContent = `-₹${totalSavings}`;
    document.getElementById("summary-final").textContent = `₹${Math.round(totalFinal)}`;
    summaryBox.style.display = "block";
}

// Razorpay Modal Integration
async function openRazorpayCheckout() {
    try {
        const response = await fetch(`${API_BASE}/buyer/checkout`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                conversation_id: conversationId,
                cart: cartItems
            })
        });

        const data = await response.json();

        if (data.status === "order_created") {
            currentOrderData = data;
            document.getElementById("rzp-modal-amount").textContent = `₹${data.final_amount}`;
            document.getElementById("rzp-modal-order-id").textContent = `Razorpay Order ID: ${data.order_id}`;
            document.getElementById("rzp-modal").style.display = "flex";

            if (data.audit_trail) {
                updateAuditLogView(data.audit_trail);
            }
        }
    } catch (err) {
        console.error(err);
        alert("Failed to initiate Razorpay checkout.");
    }
}

function closeRazorpayModal() {
    document.getElementById("rzp-modal").style.display = "none";
}

function simulatePaymentSuccess() {
    closeRazorpayModal();
    appendMessage("bot", `✅ **Payment Successful via Razorpay Test Mode!**\n\nOrder ID: ${currentOrderData.order_id}\nAmount Paid: ₹${currentOrderData.final_amount}\n\nYour items are being packed and dispatched. Thank you for using AgentPay!`);
    cartItems = [];
    updateCartUI();
}

// Merchant Dashboard API calls
async function fetchAbandonedCarts() {
    try {
        const response = await fetch(`${API_BASE}/recovery/abandoned-carts`);
        const data = await response.json();
        renderAbandonedTable(data);
    } catch (err) {
        console.error("Failed to fetch abandoned carts:", err);
    }
}

function renderAbandonedTable(carts) {
    const tbody = document.getElementById("abandoned-table-body");
    tbody.innerHTML = "";

    if (!carts || carts.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color: var(--text-muted);">No active abandoned carts detected.</td></tr>`;
        return;
    }

    carts.forEach(c => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><code>${c.session_id}</code></td>
            <td>${c.user_goal}</td>
            <td>₹${c.potential_revenue_inr}</td>
            <td style="color: var(--accent);">₹${c.savings_left_behind_inr}</td>
            <td><span class="badge ${c.status === 'recovered' ? 'badge-success' : 'badge-info'}">${c.status}</span></td>
            <td>${c.intervention_count} / 1 (Max limit)</td>
            <td>
                ${c.status === 'abandoned' ? `<button class="btn-intervene" onclick="triggerIntervention('${c.session_id}')">Intervene (+5% Offer)</button>` : '<span style="color:var(--text-muted);">Action Completed</span>'}
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function triggerIntervention(sessionId) {
    try {
        const response = await fetch(`${API_BASE}/recovery/intervene`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId })
        });
        const data = await response.json();
        alert(data.message);
        fetchAbandonedCarts();
        fetchAnalytics();
    } catch (err) {
        console.error(err);
    }
}

async function fetchAnalytics() {
    try {
        const response = await fetch(`${API_BASE}/recovery/analytics`);
        const data = await response.json();

        document.getElementById("metric-recovered").textContent = `₹${data.total_revenue_recovered_inr}`;
        document.getElementById("metric-conversion").textContent = `${data.recovery_conversion_rate_percent}%`;

        if (data.audit_logs && data.audit_logs.length > 0) {
            updateAuditLogView(data.audit_logs);
        }
    } catch (err) {
        console.error("Failed to fetch analytics:", err);
    }
}

function updateAuditLogView(logData) {
    const viewer = document.getElementById("audit-log-viewer");
    if (typeof logData === "object") {
        viewer.textContent = JSON.stringify(logData, null, 2);
    } else {
        viewer.textContent = String(logData);
    }
}
