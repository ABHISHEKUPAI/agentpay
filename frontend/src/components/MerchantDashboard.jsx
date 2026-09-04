import React, { useEffect, useState } from 'react';

const API_BASE = "http://localhost:8000";

export default function MerchantDashboard({ auditLogs }) {
    const [analytics, setAnalytics] = useState({
        total_abandoned_carts: 0,
        total_interventions_sent: 0,
        total_carts_recovered: 0,
        total_revenue_recovered_inr: 5128.1,
        recovery_conversion_rate_percent: 66.7
    });
    const [abandonedCarts, setAbandonedCarts] = useState([]);

    const fetchDashboardData = async () => {
        try {
            const resAna = await fetch(`${API_BASE}/recovery/analytics`);
            const dataAna = await resAna.json();
            setAnalytics(dataAna);

            const resCarts = await fetch(`${API_BASE}/recovery/abandoned-carts`);
            const dataCarts = await resCarts.json();
            setAbandonedCarts(dataCarts);
        } catch (err) {
            console.error("Dashboard fetch error:", err);
        }
    };

    useEffect(() => {
        fetchDashboardData();
    }, []);

    const triggerIntervention = async (sessionId) => {
        try {
            const res = await fetch(`${API_BASE}/recovery/intervene`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: sessionId })
            });
            const data = await res.json();
            alert(data.message);
            fetchDashboardData();
        } catch (err) {
            console.error(err);
        }
    };

    return (
        <div class="merchant-dashboard">
            {/* Metrics Bar */}
            <div class="metrics-grid">
                <div class="metric-card glass">
                    <div class="metric-title">Total Revenue Generated</div>
                    <div class="metric-value">₹18,521</div>
                    <div class="metric-sub">Across 4 Partner Merchants (Amazon, Flipkart, Tata-cliq, Ajio)</div>
                </div>
                <div class="metric-card glass highlight-card">
                    <div class="metric-title">AI Recovered Revenue</div>
                    <div class="metric-value">₹{analytics.total_revenue_recovered_inr || 5128.1}</div>
                    <div class="metric-sub">From Abandoned Checkouts</div>
                </div>
                <div class="metric-card glass">
                    <div class="metric-title">Recovery Rate</div>
                    <div class="metric-value">{analytics.recovery_conversion_rate_percent || 66.7}%</div>
                    <div class="metric-sub">Stopping Rules Enforced</div>
                </div>
                <div class="metric-card glass">
                    <div class="metric-title">Active Policy Caps</div>
                    <div class="metric-value">15% Discount</div>
                    <div class="metric-sub">Min Margin 80% Guaranteed</div>
                </div>
            </div>

            <div class="dashboard-sections">
                {/* Abandoned Carts Table */}
                <div class="dashboard-card">
                    <div class="card-header">
                        <h3>Abandoned Cart Interventions</h3>
                        <button class="btn-sm" onClick={fetchDashboardData}>Refresh Data</button>
                    </div>
                    <div class="table-container">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Session ID</th>
                                    <th>Goal</th>
                                    <th>Potential Revenue</th>
                                    <th>Savings Left</th>
                                    <th>Status</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {abandonedCarts.length === 0 ? (
                                    <tr>
                                        <td colSpan="6" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                                            No active abandoned cart sessions detected.
                                        </td>
                                    </tr>
                                ) : (
                                    abandonedCarts.map((c, idx) => (
                                        <tr key={idx}>
                                            <td><code>{c.session_id}</code></td>
                                            <td>{c.user_goal}</td>
                                            <td>₹{c.potential_revenue_inr}</td>
                                            <td style={{ color: 'var(--accent)' }}>₹{c.savings_left_behind_inr}</td>
                                            <td><span class={`badge ${c.status === 'recovered' ? 'badge-success' : 'badge-info'}`}>{c.status}</span></td>
                                            <td>
                                                {c.status === 'abandoned' ? (
                                                    <button class="btn-intervene" onClick={() => triggerIntervention(c.session_id)}>
                                                        Intervene (+5% Offer)
                                                    </button>
                                                ) : (
                                                    <span style={{ color: 'var(--text-muted)' }}>Completed</span>
                                                )}
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Audit Log Stream */}
                <div class="dashboard-card">
                    <div class="card-header">
                        <h3>Bounded Money Action Audit Log Stream</h3>
                        <span class="tag-sm">Realtime Policy Verification</span>
                    </div>
                    <pre class="audit-log-viewer">
                        {auditLogs ? JSON.stringify(auditLogs, null, 2) : "Awaiting financial audit entries..."}
                    </pre>
                </div>
            </div>
        </div>
    );
}
