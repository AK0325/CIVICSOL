import { useState, useEffect } from "react";
import {
    Activity,
    AlertCircle,
    BarChart3,
    CheckCircle2,
    Clock,
    FileText,
    RefreshCw,
    TrendingUp,
    Users,
} from "lucide-react";
import AuthorityLayout from "../../components/AuthorityLayout";
import {
    getAuthorityStatsOverview,
    getAuthorityDepartmentStats,
    getAuthorityTrends,
} from "../../services/authorityApi";
import "./AnalyticsDashboard.css";

export default function AnalyticsDashboard() {
    const [overview, setOverview] = useState(null);
    const [deptStats, setDeptStats] = useState([]);
    const [trends, setTrends] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const loadAnalyticsData = async () => {
        setLoading(true);
        setError("");
        try {
            const [overviewData, deptData, trendData] = await Promise.all([
                getAuthorityStatsOverview(),
                getAuthorityDepartmentStats(),
                getAuthorityTrends(30),
            ]);

            setOverview(overviewData);
            setDeptStats(deptData?.departments || []);
            setTrends(trendData?.trend || []);
        } catch (err) {
            console.error("Failed to load analytics data:", err);
            setError(err.response?.data?.detail || "Failed to load municipal analytics. Please check network connection.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadAnalyticsData();
    }, []);

    const totalIssues = overview?.total_issues || 0;
    const resolvedIssues = overview?.resolved || 0;
    const openIssues = (overview?.reported || 0) + (overview?.under_review || 0) + (overview?.assigned || 0) + (overview?.in_progress || 0);
    const resolutionRate = totalIssues > 0 ? ((resolvedIssues / totalIssues) * 100).toFixed(1) : "0.0";
    const avgTime = overview?.avg_resolution_time_hours != null
        ? `${overview.avg_resolution_time_hours.toFixed(1)} hrs`
        : "N/A";

    const statusItems = [
        { label: "Reported", count: overview?.reported || 0, color: "#fbbf24" },
        { label: "Under Review", count: overview?.under_review || 0, color: "#38bdf8" },
        { label: "Assigned", count: overview?.assigned || 0, color: "#c084fc" },
        { label: "In Progress", count: overview?.in_progress || 0, color: "#60a5fa" },
        { label: "Resolved", count: overview?.resolved || 0, color: "#4ade80" },
        { label: "Rejected", count: overview?.rejected || 0, color: "#f87171" },
        { label: "Reopened", count: overview?.reopened || 0, color: "#fb923c" },
    ];

    // Calculate max value for trend normalization
    const maxDailyCount = Math.max(
        ...trends.map((t) => Math.max(t.reported_count || 0, t.resolved_count || 0)),
        5
    );

    return (
        <AuthorityLayout title="Municipal Analytics & Reporting">
            <div className="analytics-container">
                <div className="analytics-header">
                    <div>
                        <h1 className="analytics-title">Civic Operations Intelligence</h1>
                        <p className="analytics-subtitle">
                            Database-backed operational metrics, departmental KPIs, and 30-day resolution velocity.
                        </p>
                    </div>
                    <button
                        type="button"
                        onClick={loadAnalyticsData}
                        className="analytics-refresh-btn"
                        disabled={loading}
                    >
                        <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
                        <span>Refresh Metrics</span>
                    </button>
                </div>

                {error && (
                    <div style={{ background: "rgba(239, 68, 68, 0.15)", border: "1px solid rgba(239, 68, 68, 0.3)", padding: "14px 18px", borderRadius: "10px", color: "#f87171", display: "flex", alignItems: "center", gap: "10px" }}>
                        <AlertCircle size={18} />
                        <span>{error}</span>
                    </div>
                )}

                {/* KPIS */}
                <div className="analytics-grid-kpis">
                    <div className="analytics-kpi-card">
                        <div className="analytics-kpi-icon" style={{ background: "rgba(14, 165, 233, 0.15)", color: "#38bdf8" }}>
                            <FileText size={22} />
                        </div>
                        <div>
                            <div className="analytics-kpi-label">Total Submissions</div>
                            <div className="analytics-kpi-value">{totalIssues}</div>
                        </div>
                    </div>

                    <div className="analytics-kpi-card">
                        <div className="analytics-kpi-icon" style={{ background: "rgba(245, 158, 11, 0.15)", color: "#fbbf24" }}>
                            <Activity size={22} />
                        </div>
                        <div>
                            <div className="analytics-kpi-label">Active / Open</div>
                            <div className="analytics-kpi-value">{openIssues}</div>
                        </div>
                    </div>

                    <div className="analytics-kpi-card">
                        <div className="analytics-kpi-icon" style={{ background: "rgba(34, 197, 94, 0.15)", color: "#4ade80" }}>
                            <CheckCircle2 size={22} />
                        </div>
                        <div>
                            <div className="analytics-kpi-label">Resolution Rate</div>
                            <div className="analytics-kpi-value">{resolutionRate}%</div>
                        </div>
                    </div>

                    <div className="analytics-kpi-card">
                        <div className="analytics-kpi-icon" style={{ background: "rgba(168, 85, 247, 0.15)", color: "#c084fc" }}>
                            <Clock size={22} />
                        </div>
                        <div>
                            <div className="analytics-kpi-label">Avg Resolution Time</div>
                            <div className="analytics-kpi-value">{avgTime}</div>
                        </div>
                    </div>
                </div>

                {/* TWO COLUMN: STATUS BREAKDOWN & 30-DAY TREND */}
                <div className="analytics-grid-two">
                    {/* Status Breakdown */}
                    <div className="analytics-card">
                        <div className="analytics-card-header">
                            <h2 className="analytics-card-title">
                                <BarChart3 size={17} />
                                <span>Lifecycle Status Distribution</span>
                            </h2>
                            <span style={{ fontSize: "12px", color: "#64748b" }}>
                                {totalIssues} Total
                            </span>
                        </div>

                        <div style={{ marginTop: "8px" }}>
                            {statusItems.map((item) => {
                                const pct = totalIssues > 0 ? ((item.count / totalIssues) * 100).toFixed(0) : 0;
                                return (
                                    <div key={item.label} className="bar-chart-row">
                                        <div className="bar-chart-label">{item.label}</div>
                                        <div className="bar-chart-track">
                                            <div
                                                className="bar-chart-fill"
                                                style={{
                                                    width: `${pct}%`,
                                                    backgroundColor: item.color,
                                                }}
                                            />
                                        </div>
                                        <div className="bar-chart-count">{item.count}</div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* 30-Day Activity Trends */}
                    <div className="analytics-card">
                        <div className="analytics-card-header">
                            <h2 className="analytics-card-title">
                                <TrendingUp size={17} />
                                <span>30-Day Reporting & Velocity Trend</span>
                            </h2>
                            <div style={{ display: "flex", gap: "12px", fontSize: "11px" }}>
                                <span style={{ display: "flex", alignItems: "center", gap: "4px", color: "#38bdf8" }}>
                                    <span style={{ width: "8px", height: "8px", borderRadius: "2px", background: "#38bdf8" }}></span> Reported
                                </span>
                                <span style={{ display: "flex", alignItems: "center", gap: "4px", color: "#4ade80" }}>
                                    <span style={{ width: "8px", height: "8px", borderRadius: "2px", background: "#4ade80" }}></span> Resolved
                                </span>
                            </div>
                        </div>

                        {trends.length === 0 ? (
                            <div style={{ padding: "40px 0", textAlign: "center", color: "#64748b", fontSize: "13px" }}>
                                No historical trend records in current window.
                            </div>
                        ) : (
                            <div className="trend-chart-container">
                                {trends.slice(-15).map((t, idx) => {
                                    const reportedHeight = Math.max((t.reported_count / maxDailyCount) * 150, 4);
                                    const resolvedHeight = Math.max((t.resolved_count / maxDailyCount) * 150, 4);
                                    const dateStr = t.date ? t.date.split("-").slice(1).join("/") : `${idx}`;
                                    return (
                                        <div key={t.date || idx} className="trend-bar-wrapper" title={`${t.date}: ${t.reported_count} reported, ${t.resolved_count} resolved`}>
                                            <div style={{ display: "flex", width: "100%", gap: "2px", alignItems: "flex-end" }}>
                                                <div
                                                    className="trend-bar-fill"
                                                    style={{ height: `${reportedHeight}px` }}
                                                />
                                                <div
                                                    className="trend-bar-fill resolved-bar"
                                                    style={{ height: `${resolvedHeight}px` }}
                                                />
                                            </div>
                                            <span className="trend-date-label">{dateStr}</span>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </div>

                {/* DEPARTMENT PERFORMANCE TABLE */}
                <div className="analytics-card">
                    <div className="analytics-card-header">
                        <h2 className="analytics-card-title">
                            <Users size={17} />
                            <span>Departmental Workload & Resolution Performance</span>
                        </h2>
                        <span style={{ fontSize: "12px", color: "#64748b" }}>
                            {deptStats.length} Registered Departments
                        </span>
                    </div>

                    <div style={{ overflowX: "auto" }}>
                        <table className="dept-perf-table">
                            <thead>
                                <tr>
                                    <th>Department Name</th>
                                    <th>Code</th>
                                    <th>Total Assigned</th>
                                    <th>Active Open</th>
                                    <th>Resolved</th>
                                    <th>Resolution Rate</th>
                                </tr>
                            </thead>
                            <tbody>
                                {deptStats.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} style={{ textAlign: "center", padding: "30px", color: "#64748b" }}>
                                            No department statistics available yet.
                                        </td>
                                    </tr>
                                ) : (
                                    deptStats.map((dept) => {
                                        const rate = dept.resolution_rate != null ? dept.resolution_rate : (dept.total_issues > 0 ? (dept.resolved_issues / dept.total_issues) * 100 : 0);
                                        const rateClass = rate >= 70 ? "rate-high" : rate >= 40 ? "rate-mid" : "rate-low";
                                        return (
                                            <tr key={dept.department_id || dept.code}>
                                                <td style={{ fontWeight: 600, color: "#ffffff" }}>{dept.department_name}</td>
                                                <td>
                                                    <span style={{ fontFamily: "monospace", color: "#94a3b8", fontSize: "11px" }}>
                                                        {dept.code}
                                                    </span>
                                                </td>
                                                <td style={{ fontWeight: 600 }}>{dept.total_issues}</td>
                                                <td style={{ color: "#fbbf24" }}>{dept.open_issues}</td>
                                                <td style={{ color: "#4ade80" }}>{dept.resolved_issues}</td>
                                                <td>
                                                    <span className={`rate-badge ${rateClass}`}>
                                                        {rate.toFixed(1)}%
                                                    </span>
                                                </td>
                                            </tr>
                                        );
                                    })
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </AuthorityLayout>
    );
}
