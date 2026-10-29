import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
    Activity,
    AlertTriangle,
    ArrowUpRight,
    Building2,
    CheckCircle2,
    Clock,
    FileSpreadsheet,
    Flame,
    History,
    Loader2,
    MapPin,
    RefreshCw,
    ShieldAlert,
    TrendingUp,
    UserCheck,
    Users,
} from "lucide-react";
import AuthorityLayout from "../../components/AuthorityLayout";
import {
    getAuthorityDepartmentStats,
    getAuthorityIssues,
    getAuthorityStatsOverview,
    getOfficerWorkloads,
    getRecentAuthorityActivity,
} from "../../services/authorityApi";
import "./AuthorityDashboard.css";

export default function AuthorityDashboard() {
    const [overview, setOverview] = useState(null);
    const [deptStats, setDeptStats] = useState([]);
    const [officerWorkloads, setOfficerWorkloads] = useState([]);
    const [recentIssues, setRecentIssues] = useState([]);
    const [recentActivity, setRecentActivity] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState("");

    const fetchData = async () => {
        try {
            setError("");
            const [overviewData, deptsData, issuesData, activityData, workloadsData] = await Promise.all([
                getAuthorityStatsOverview(),
                getAuthorityDepartmentStats(),
                getAuthorityIssues({ page: 1, page_size: 5, sort_by: "created_at", sort_order: "desc" }),
                getRecentAuthorityActivity(8),
                getOfficerWorkloads().catch(() => ({ officers: [] })),
            ]);
            setOverview(overviewData);
            setDeptStats(deptsData.departments || []);
            setRecentIssues(issuesData.issues || []);
            setRecentActivity(activityData || []);
            setOfficerWorkloads(workloadsData.officers || []);
        } catch (err) {
            setError("Failed to load dashboard metrics. Ensure the backend server is running.");
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleRefresh = () => {
        setRefreshing(true);
        fetchData();
    };

    const formatActivityTime = (isoString) => {
        if (!isoString) return "";
        const date = new Date(isoString);
        return date.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    };

    return (
        <AuthorityLayout title="Municipal Executive Command Center">
            <div className="auth-dashboard-container">
                <div className="auth-header-section">
                    <div>
                        <h1 className="auth-header-title">Citywide Operations Overview</h1>
                        <p className="auth-header-subtitle">
                            Real-time database-backed civic intelligence, SLA compliance, and dispatch management
                        </p>
                    </div>

                    <button
                        type="button"
                        onClick={handleRefresh}
                        disabled={refreshing}
                        style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "8px",
                            padding: "8px 16px",
                            borderRadius: "8px",
                            background: "rgba(14, 165, 233, 0.12)",
                            color: "#38bdf8",
                            border: "1px solid rgba(14, 165, 233, 0.25)",
                            cursor: "pointer",
                            fontSize: "13px",
                            fontWeight: 600,
                        }}
                    >
                        <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
                        <span>Refresh Telemetry</span>
                    </button>
                </div>

                {error && (
                    <div style={{ padding: "12px 16px", background: "rgba(239,68,68,0.12)", color: "#f87171", borderRadius: "8px", border: "1px solid rgba(239,68,68,0.2)" }}>
                        {error}
                    </div>
                )}

                {loading ? (
                    <div style={{ padding: "80px", textAlign: "center", color: "#64748b" }}>
                        <Loader2 size={36} className="animate-spin" style={{ margin: "0 auto 12px" }} />
                        <p>Aggregating municipal telemetry...</p>
                    </div>
                ) : (
                    <>
                        {/* KPI GRID */}
                        <div className="auth-kpi-grid">
                            <div className="auth-kpi-card">
                                <div className="auth-kpi-icon icon-blue">
                                    <FileSpreadsheet size={22} />
                                </div>
                                <div className="auth-kpi-details">
                                    <span className="auth-kpi-label">Total Reports</span>
                                    <span className="auth-kpi-value">{overview?.total_issues ?? 0}</span>
                                </div>
                            </div>

                            <div className="auth-kpi-card">
                                <div className="auth-kpi-icon icon-amber">
                                    <AlertTriangle size={22} />
                                </div>
                                <div className="auth-kpi-details">
                                    <span className="auth-kpi-label">Pending Review</span>
                                    <span className="auth-kpi-value">
                                        {(overview?.reported ?? 0) + (overview?.under_review ?? 0)}
                                    </span>
                                </div>
                            </div>

                            <div className="auth-kpi-card">
                                <div className="auth-kpi-icon icon-purple">
                                    <Clock size={22} />
                                </div>
                                <div className="auth-kpi-details">
                                    <span className="auth-kpi-label">Assigned & Active</span>
                                    <span className="auth-kpi-value">
                                        {(overview?.assigned ?? 0) + (overview?.in_progress ?? 0)}
                                    </span>
                                </div>
                            </div>

                            <div className="auth-kpi-card">
                                <div className="auth-kpi-icon" style={{ background: "rgba(239, 68, 68, 0.15)", color: "#f87171" }}>
                                    <Flame size={22} />
                                </div>
                                <div className="auth-kpi-details">
                                    <span className="auth-kpi-label">Urgent & Critical</span>
                                    <span className="auth-kpi-value" style={{ color: "#f87171" }}>
                                        {overview?.urgent_count ?? 0}
                                    </span>
                                </div>
                            </div>

                            <div className="auth-kpi-card">
                                <div className="auth-kpi-icon" style={{ background: "rgba(244, 63, 94, 0.15)", color: "#fb7185" }}>
                                    <ShieldAlert size={22} />
                                </div>
                                <div className="auth-kpi-details">
                                    <span className="auth-kpi-label">SLA Overdue</span>
                                    <span className="auth-kpi-value" style={{ color: overview?.overdue_count > 0 ? "#fb7185" : "#e2e8f0" }}>
                                        {overview?.overdue_count ?? 0}
                                    </span>
                                </div>
                            </div>

                            <div className="auth-kpi-card">
                                <div className="auth-kpi-icon icon-green">
                                    <CheckCircle2 size={22} />
                                </div>
                                <div className="auth-kpi-details">
                                    <span className="auth-kpi-label">Resolved Issues</span>
                                    <span className="auth-kpi-value">{overview?.resolved ?? 0}</span>
                                </div>
                            </div>

                            <div className="auth-kpi-card">
                                <div className="auth-kpi-icon icon-cyan">
                                    <TrendingUp size={22} />
                                </div>
                                <div className="auth-kpi-details">
                                    <span className="auth-kpi-label">Resolution Rate</span>
                                    <span className="auth-kpi-value">
                                        {overview?.resolution_rate_percent ?? 0}%
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* TWO-COLUMN WORKLOAD & QUEUE */}
                        <div className="auth-two-col">
                            {/* RECENT INCOMING ISSUES */}
                            <div className="auth-card">
                                <div className="auth-card-header">
                                    <h3 className="auth-card-title">Live Dispatch Queue</h3>
                                    <Link
                                        to="/authority/issues"
                                        style={{ fontSize: "12.5px", color: "#38bdf8", textDecoration: "none", display: "flex", alignItems: "center", gap: "4px" }}
                                    >
                                        <span>View All Issues</span>
                                        <ArrowUpRight size={14} />
                                    </Link>
                                </div>

                                {recentIssues.length === 0 ? (
                                    <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
                                        No active issues reported yet.
                                    </div>
                                ) : (
                                    <table className="auth-table">
                                        <thead>
                                            <tr>
                                                <th>Title / Location</th>
                                                <th>Category</th>
                                                <th>Severity</th>
                                                <th>Status</th>
                                                <th>Action</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {recentIssues.map((issue) => (
                                                <tr key={issue.id}>
                                                    <td>
                                                        <div style={{ fontWeight: 600, color: "#f8fafc" }}>
                                                            {issue.title}
                                                        </div>
                                                        <div style={{ fontSize: "11.5px", color: "#64748b" }}>
                                                            {issue.location}
                                                        </div>
                                                    </td>
                                                    <td>{issue.category}</td>
                                                    <td>
                                                        <span style={{
                                                            fontSize: "11px",
                                                            fontWeight: 700,
                                                            color: issue.severity === "Critical" ? "#f87171" : issue.severity === "High" ? "#fb923c" : "#38bdf8",
                                                        }}>
                                                            {issue.severity}
                                                        </span>
                                                    </td>
                                                    <td>
                                                        <span className={`status-pill status-${issue.status.toLowerCase().replace(" ", "_")}`}>
                                                            {issue.status}
                                                        </span>
                                                    </td>
                                                    <td>
                                                        <Link
                                                            to={`/authority/issues/${issue.id}`}
                                                            style={{
                                                                padding: "4px 10px",
                                                                background: "rgba(56, 189, 248, 0.1)",
                                                                color: "#38bdf8",
                                                                borderRadius: "6px",
                                                                textDecoration: "none",
                                                                fontSize: "12px",
                                                                fontWeight: 600,
                                                            }}
                                                        >
                                                            Dispatch
                                                        </Link>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                )}
                            </div>

                            {/* DEPARTMENT WORKLOAD */}
                            <div className="auth-card">
                                <div className="auth-card-header">
                                    <h3 className="auth-card-title">Department Workloads</h3>
                                    <Link
                                        to="/authority/departments"
                                        style={{ fontSize: "12.5px", color: "#38bdf8", textDecoration: "none", display: "flex", alignItems: "center", gap: "4px" }}
                                    >
                                        <span>Manage</span>
                                        <ArrowUpRight size={14} />
                                    </Link>
                                </div>

                                {deptStats.length === 0 ? (
                                    <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
                                        No departmental metrics available.
                                    </div>
                                ) : (
                                    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                                        {deptStats.map((dept) => (
                                            <div key={dept.department_id} style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                                                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>
                                                    <span style={{ fontWeight: 600, color: "#e2e8f0" }}>{dept.name}</span>
                                                    <span style={{ color: "#94a3b8" }}>
                                                        {dept.resolved_issues} / {dept.total_issues} ({dept.resolution_rate_percent}%)
                                                    </span>
                                                </div>
                                                <div style={{ width: "100%", height: "6px", background: "rgba(148,163,184,0.12)", borderRadius: "3px", overflow: "hidden" }}>
                                                    <div
                                                        style={{
                                                            width: `${dept.resolution_rate_percent}%`,
                                                            height: "100%",
                                                            background: "linear-gradient(90deg, #0284c7, #38bdf8)",
                                                            borderRadius: "3px",
                                                        }}
                                                    />
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* WORKLOAD COMPARISON & RECENT ADMINISTRATIVE ACTIVITY */}
                        <div className="auth-two-col" style={{ marginTop: "24px" }}>
                            {/* OFFICER WORKLOAD COMPARISONS */}
                            <div className="auth-card">
                                <div className="auth-card-header">
                                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                        <Users size={18} style={{ color: "#38bdf8" }} />
                                        <h3 className="auth-card-title">Officer Workload Distribution</h3>
                                    </div>
                                    <span style={{ fontSize: "12px", color: "#64748b" }}>
                                        {officerWorkloads.length} Active Officers
                                    </span>
                                </div>

                                {officerWorkloads.length === 0 ? (
                                    <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
                                        No officer assignments recorded.
                                    </div>
                                ) : (
                                    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                                        {officerWorkloads.slice(0, 6).map((off) => (
                                            <div key={off.officer_id} style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                                                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>
                                                    <div>
                                                        <span style={{ fontWeight: 600, color: "#f1f5f9" }}>{off.officer_name}</span>
                                                        <span style={{ fontSize: "11px", color: "#64748b", marginLeft: "6px" }}>
                                                            ({off.department_name})
                                                        </span>
                                                    </div>
                                                    <span style={{ fontSize: "12px", color: off.open_issues > 3 ? "#fb923c" : "#4ade80" }}>
                                                        {off.open_issues} active / {off.resolved_issues} resolved ({off.resolution_rate}%)
                                                    </span>
                                                </div>
                                                <div style={{ width: "100%", height: "5px", background: "rgba(148,163,184,0.1)", borderRadius: "3px", overflow: "hidden" }}>
                                                    <div
                                                        style={{
                                                            width: `${off.resolution_rate}%`,
                                                            height: "100%",
                                                            background: off.open_issues > 3 ? "linear-gradient(90deg, #f59e0b, #fbbf24)" : "linear-gradient(90deg, #10b981, #34d399)",
                                                            borderRadius: "3px",
                                                        }}
                                                    />
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* RECENT ADMINISTRATIVE ACTIVITY FEED */}
                            <div className="auth-card">
                                <div className="auth-card-header">
                                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                        <History size={18} style={{ color: "#a855f7" }} />
                                        <h3 className="auth-card-title">Recent Administrative Activity</h3>
                                    </div>
                                    <Link
                                        to="/authority/audit-logs"
                                        style={{ fontSize: "12.5px", color: "#38bdf8", textDecoration: "none", display: "flex", alignItems: "center", gap: "4px" }}
                                    >
                                        <span>Full Trail</span>
                                        <ArrowUpRight size={14} />
                                    </Link>
                                </div>

                                {recentActivity.length === 0 ? (
                                    <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
                                        No recent administrative activity recorded.
                                    </div>
                                ) : (
                                    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                                        {recentActivity.map((act) => (
                                            <div
                                                key={act.id}
                                                style={{
                                                    display: "flex",
                                                    alignItems: "flex-start",
                                                    justifyContent: "space-between",
                                                    padding: "10px 12px",
                                                    background: "rgba(15, 23, 42, 0.4)",
                                                    borderRadius: "8px",
                                                    border: "1px solid rgba(148, 163, 184, 0.08)",
                                                }}
                                            >
                                                <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                                                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                                                        <span style={{ fontSize: "12.5px", fontWeight: 600, color: "#f8fafc" }}>
                                                            {act.actor_name || "System"}
                                                        </span>
                                                        <span style={{
                                                            fontSize: "11px",
                                                            padding: "1px 6px",
                                                            borderRadius: "4px",
                                                            background: "rgba(168, 85, 247, 0.15)",
                                                            color: "#c084fc",
                                                            fontWeight: 600,
                                                        }}>
                                                            {act.action}
                                                        </span>
                                                    </div>
                                                    <span style={{ fontSize: "11.5px", color: "#94a3b8" }}>
                                                        {act.details?.slice(0, 70) || `${act.target_type} #${act.target_id || ""}`}
                                                    </span>
                                                </div>
                                                <span style={{ fontSize: "11px", color: "#64748b", whiteSpace: "nowrap" }}>
                                                    {formatActivityTime(act.created_at)}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </>
                )}
            </div>
        </AuthorityLayout>
    );
}
