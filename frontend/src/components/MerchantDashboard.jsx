import React, { useEffect, useState } from 'react';

const API_BASE = "http://localhost:8000";

export default function MerchantDashboard({ auditLogs }) {
    const [analytics, setAnalytics] = useState({
        total_abandoned_carts: 0,
        total_interventions_sent: 0,
        total_carts_recovered: 0,
        total_revenue_recovered_inr: 0,
        recovery_conversion_rate_percent: 0
    });
    const [merchantStats, setMerchantStats] = useState({
        merchant_count: 4,
        total_products: 0,
        total_catalog_value_inr: 0,
        active_policy_caps: "15% Max Discount | Min Margin 80% Guaranteed",
        merchant_breakdown: []
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

            const resMerch = await fetch(`${API_BASE}/ai/merchant-analytics`);
            const dataMerch = await resMerch.json();
            setMerchantStats(dataMerch);
        } catch (err) {
            console.error("Dashboard fetch error:", err);
        }
    };

    useEffect(() => {
        fetchDashboardData();
        const interval = setInterval(fetchDashboardData, 3000);
        return () => clearInterval(interval);
    }, [auditLogs]);

    const triggerIntervention = async (sessionId) => {
        try {
            const res = await fetch(`${API_BASE}/recovery/intervene`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: sessionId })
            });
            const data = await res.json();
            alert(data.message || "Intervention sent!");
            fetchDashboardData();
        } catch (err) {
            console.error(err);
        }
    };

    const completeRecovery = async (sessionId) => {
        try {
            const res = await fetch(`${API_BASE}/recovery/complete`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: sessionId })
            });
            const data = await res.json();
            alert(data.message || "Recovery completed!");
            fetchDashboardData();
        } catch (err) {
            console.error(err);
        }
    };

    // Total live merchant revenue = recovered revenue + active catalog value baseline fraction
    const totalLiveRevenue = Math.round(
        (analytics.total_revenue_recovered_inr || 0) + (merchantStats.total_catalog_value_inr ? merchantStats.total_catalog_value_inr * 0.12 : 18520)
    );

    return (
        <div className="merchant-dashboard">
            {/* Metrics Bar */}
            <div className="metrics-grid">
                <div className="metric-card glass">
                    <div className="metric-title">Total Merchant GMV</div>
                    <div className="metric-value">₹{totalLiveRevenue.toLocaleString('en-IN')}</div>
                    <div className="metric-sub">Across {merchantStats.merchant_count || 4} Partner Merchants</div>
                </div>
                <div className="metric-card glass highlight-card">
                    <div className="metric-title">AI Recovered Revenue</div>
                    <div className="metric-value">₹{(analytics.total_revenue_recovered_inr || 0).toLocaleString('en-IN')}</div>
                    <div className="metric-sub">From {analytics.total_carts_recovered} Recovered Sessions</div>
                </div>
                <div className="metric-card glass">
                    <div className="metric-title">Recovery Rate</div>
                    <div className="metric-value">{analytics.recovery_conversion_rate_percent}%</div>
                    <div className="metric-sub">{analytics.total_interventions_sent} Interventions Sent (Max 1 Rule)</div>
                </div>
                <div className="metric-card glass">
                    <div className="metric-title">Active Policy Caps</div>
                    <div className="metric-value" style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--accent)' }}>
                        {merchantStats.active_policy_caps}
                    </div>
                    <div className="metric-sub">Dynamically Enforced from DB</div>
                </div>
            </div>

            <div className="dashboard-sections">
                {/* Partner Merchants Inventory Breakdown */}
                {merchantStats.merchant_breakdown && merchantStats.merchant_breakdown.length > 0 && (
                    <div className="dashboard-card" style={{ marginBottom: '1.5rem' }}>
                        <div className="card-header">
                            <h3>Partner Merchants & Catalog Overview</h3>
                            <span className="tag-sm">{merchantStats.total_products} Active SKUs</span>
                        </div>
                        <div className="table-container">
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th>Merchant Partner</th>
                                        <th>Category</th>
                                        <th>Min Margin</th>
                                        <th>Max Discount</th>
                                        <th>Product Count</th>
                                        <th>Total Stock</th>
                                        <th>Inventory Valuation</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {merchantStats.merchant_breakdown.map((m) => (
                                        <tr key={m.id}>
                                            <td><strong>{m.name}</strong></td>
                                            <td><span className="badge badge-info">{m.category}</span></td>
                                            <td>{m.min_margin > 1 ? m.min_margin.toFixed(0) : (m.min_margin * 100).toFixed(0)}%</td>
                                            <td>{m.max_discount > 1 ? m.max_discount.toFixed(0) : (m.max_discount * 100).toFixed(0)}%</td>
                                            <td>{m.product_count} items</td>
                                            <td>{m.total_stock} units</td>
                                            <td style={{ color: 'var(--accent)', fontWeight: 600 }}>₹{m.catalog_value_inr.toLocaleString('en-IN')}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {/* Abandoned Carts Table */}
                <div className="dashboard-card">
                    <div className="card-header">
                        <h3>Abandoned Cart Interventions & Recovery</h3>
                        <button className="btn-sm" onClick={fetchDashboardData}>Refresh Data</button>
                    </div>
                    <div className="table-container">
                        <table className="data-table">
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
                                            <td>₹{c.potential_revenue_inr.toLocaleString('en-IN')}</td>
                                            <td style={{ color: 'var(--accent)' }}>₹{c.savings_left_behind_inr.toLocaleString('en-IN')}</td>
                                            <td>
                                                <span className={`badge ${c.status === 'recovered' ? 'badge-success' : c.status === 'intervened' ? 'badge-warning' : 'badge-info'}`}>
                                                    {c.status}
                                                </span>
                                            </td>
                                            <td>
                                                {c.status === 'abandoned' ? (
                                                    <button className="btn-intervene" onClick={() => triggerIntervention(c.session_id)}>
                                                        Intervene (+5% Offer)
                                                    </button>
                                                ) : c.status === 'intervened' ? (
                                                    <button className="btn-intervene" style={{ background: '#10b981' }} onClick={() => completeRecovery(c.session_id)}>
                                                        Complete Payment
                                                    </button>
                                                ) : (
                                                    <span style={{ color: 'var(--text-muted)' }}>Recovered</span>
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
                <div className="dashboard-card" style={{ marginTop: '1.5rem' }}>
                    <div className="card-header">
                        <h3>Bounded Money Action Audit Log Stream</h3>
                        <span className="tag-sm">Realtime Policy Verification</span>
                    </div>
                    <pre className="audit-log-viewer">
                        {auditLogs ? JSON.stringify(auditLogs, null, 2) : "Awaiting financial audit entries..."}
                    </pre>
                </div>
            </div>
        </div>
    );
}
