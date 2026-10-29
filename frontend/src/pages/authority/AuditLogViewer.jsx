import { useState, useEffect } from "react";
import {
    AlertCircle,
    ChevronLeft,
    ChevronRight,
    History,
    RefreshCw,
    Search,
    ShieldAlert,
} from "lucide-react";
import AuthorityLayout from "../../components/AuthorityLayout";
import { getAuthorityAuditLogs } from "../../services/authorityApi";
import "./AuditLogViewer.css";

export default function AuditLogViewer() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [actionFilter, setActionFilter] = useState("");
    const [entityFilter, setEntityFilter] = useState("");
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalRecords, setTotalRecords] = useState(0);

    const loadAuditLogs = async (targetPage = page) => {
        setLoading(true);
        setError("");
        try {
            const params = {
                page: targetPage,
                page_size: 25,
            };
            if (actionFilter.trim()) params.action = actionFilter.trim();
            if (entityFilter) params.entity_type = entityFilter;

            const data = await getAuthorityAuditLogs(params);
            setLogs(data.logs || []);
            setTotalPages(data.pages || 1);
            setTotalRecords(data.total || 0);
            setPage(data.page || 1);
        } catch (err) {
            console.error("Failed to load audit logs:", err);
            setError(err.response?.data?.detail || "Failed to load audit logs. Permission restricted to Super Admin.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadAuditLogs(1);
    }, [actionFilter, entityFilter]);

    const getActionBadgeClass = (action) => {
        const act = (action || "").toLowerCase();
        if (act.includes("create") || act.includes("provision") || act.includes("bootstrap")) return "action-create";
        if (act.includes("assign")) return "action-assign";
        if (act.includes("resolve")) return "action-resolve";
        if (act.includes("status")) return "action-status";
        return "action-default";
    };

    return (
        <AuthorityLayout title="Administrative Audit Trail">
            <div className="audit-container">
                <div className="audit-header">
                    <div>
                        <h1 className="audit-title">Municipal Audit Log</h1>
                        <p className="audit-subtitle">
                            Immutable chronological record of administrative actions, officer provisioning, and lifecycle state changes.
                        </p>
                    </div>
                    <button
                        type="button"
                        onClick={() => loadAuditLogs(page)}
                        className="analytics-refresh-btn"
                        disabled={loading}
                    >
                        <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
                        <span>Refresh Trail</span>
                    </button>
                </div>

                {error && (
                    <div style={{ background: "rgba(239, 68, 68, 0.15)", border: "1px solid rgba(239, 68, 68, 0.3)", padding: "14px 18px", borderRadius: "10px", color: "#f87171", display: "flex", alignItems: "center", gap: "10px" }}>
                        <ShieldAlert size={18} />
                        <span>{error}</span>
                    </div>
                )}

                {/* FILTER BAR */}
                <div className="audit-filter-bar">
                    <input
                        type="text"
                        placeholder="Search action by keyword (e.g. resolve, assign, create)..."
                        value={actionFilter}
                        onChange={(e) => setActionFilter(e.target.value)}
                        className="audit-search-input"
                    />

                    <select
                        value={entityFilter}
                        onChange={(e) => setEntityFilter(e.target.value)}
                        className="audit-select"
                    >
                        <option value="">All Entity Types</option>
                        <option value="CIVIC_ISSUE">Civic Issues</option>
                        <option value="DEPARTMENT">Departments</option>
                        <option value="USER">User / Officer</option>
                    </select>

                    <div style={{ fontSize: "12px", color: "#94a3b8", marginLeft: "auto" }}>
                        Showing {logs.length} of {totalRecords} records
                    </div>
                </div>

                {/* AUDIT LOG TABLE */}
                <div className="audit-table-card">
                    <div style={{ overflowX: "auto" }}>
                        <table className="audit-table">
                            <thead>
                                <tr>
                                    <th>Timestamp</th>
                                    <th>Actor</th>
                                    <th>Action</th>
                                    <th>Entity</th>
                                    <th>Details</th>
                                    <th>IP Address</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading && logs.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
                                            Loading audit records...
                                        </td>
                                    </tr>
                                ) : logs.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
                                            No administrative audit logs found matching criteria.
                                        </td>
                                    </tr>
                                ) : (
                                    logs.map((log) => (
                                        <tr key={log.id}>
                                            <td style={{ whiteSpace: "nowrap", fontSize: "12px", color: "#94a3b8" }}>
                                                {new Date(log.created_at).toLocaleString()}
                                            </td>
                                            <td>
                                                <div style={{ fontWeight: 600, color: "#ffffff" }}>{log.user_name}</div>
                                                <div style={{ fontSize: "10px", color: "#64748b" }}>{log.user_role}</div>
                                            </td>
                                            <td>
                                                <span className={`action-badge ${getActionBadgeClass(log.action)}`}>
                                                    {log.action}
                                                </span>
                                            </td>
                                            <td>
                                                <span style={{ fontSize: "12px", color: "#cbd5e1" }}>
                                                    {log.entity_type} {log.entity_id ? `#${log.entity_id}` : ""}
                                                </span>
                                            </td>
                                            <td>
                                                {log.details ? (
                                                    <pre className="audit-details-json">
                                                        {typeof log.details === "object" ? JSON.stringify(log.details, null, 1) : log.details}
                                                    </pre>
                                                ) : (
                                                    <span style={{ color: "#64748b", fontSize: "11px" }}>—</span>
                                                )}
                                            </td>
                                            <td style={{ fontFamily: "monospace", fontSize: "11px", color: "#64748b" }}>
                                                {log.ip_address || "local"}
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>

                    {/* PAGINATION */}
                    <div className="audit-pagination">
                        <span style={{ fontSize: "12px", color: "#94a3b8" }}>
                            Page {page} of {totalPages}
                        </span>
                        <div style={{ display: "flex", gap: "8px" }}>
                            <button
                                type="button"
                                disabled={page <= 1 || loading}
                                onClick={() => loadAuditLogs(page - 1)}
                                className="audit-page-btn"
                            >
                                <ChevronLeft size={14} style={{ display: "inline", verticalAlign: "middle" }} /> Previous
                            </button>
                            <button
                                type="button"
                                disabled={page >= totalPages || loading}
                                onClick={() => loadAuditLogs(page + 1)}
                                className="audit-page-btn"
                            >
                                Next <ChevronRight size={14} style={{ display: "inline", verticalAlign: "middle" }} />
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </AuthorityLayout>
    );
}
