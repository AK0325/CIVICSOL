import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
    AlertCircle,
    AlertTriangle,
    CheckCircle2,
    Download,
    Eye,
    FileSpreadsheet,
    Filter,
    Flame,
    Loader2,
    Search,
    ShieldAlert,
    UserCheck,
    X,
} from "lucide-react";
import AuthorityLayout from "../../components/AuthorityLayout";
import {
    assignAuthorityIssue,
    exportAuthorityIssuesCsv,
    getAuthorityDepartments,
    getAuthorityIssues,
    getAuthorityOfficers,
    updateAuthorityIssueStatus,
} from "../../services/authorityApi";
import "./IssueManagement.css";

const CATEGORIES = [
    "Road Damage",
    "Garbage",
    "Street Light",
    "Water Leakage",
    "Tree / Greenery",
    "Traffic",
    "Drainage",
    "Public Infrastructure",
];

const STATUSES = [
    "Reported",
    "Under Review",
    "Assigned",
    "In Progress",
    "Resolved",
    "Rejected",
    "Reopened",
];

export default function IssueManagement() {
    const [issues, setIssues] = useState([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [pages, setPages] = useState(1);
    const [search, setSearch] = useState("");
    const [statusFilter, setStatusFilter] = useState("");
    const [categoryFilter, setCategoryFilter] = useState("");
    const [deptFilter, setDeptFilter] = useState("");
    const [urgentFilter, setUrgentFilter] = useState(false);
    const [unresolvedFilter, setUnresolvedFilter] = useState(false);
    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");
    const [departments, setDepartments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [exporting, setExporting] = useState(false);

    // Modal state for quick assign
    const [assignModalIssue, setAssignModalIssue] = useState(null);
    const [assignDeptId, setAssignDeptId] = useState("");
    const [assignOfficerId, setAssignOfficerId] = useState("");
    const [assignComment, setAssignComment] = useState("");
    const [availableOfficers, setAvailableOfficers] = useState([]);
    const [modalSubmitting, setModalSubmitting] = useState(false);
    const [modalError, setModalError] = useState("");

    const fetchDepartments = async () => {
        try {
            const depts = await getAuthorityDepartments();
            setDepartments(depts || []);
        } catch {
            // ignore
        }
    };

    const fetchIssues = async (targetPage = page) => {
        try {
            setLoading(true);
            const params = {
                page: targetPage,
                page_size: 15,
                search: search.trim() || undefined,
                status: statusFilter || undefined,
                category: categoryFilter || undefined,
                department_id: deptFilter ? Number(deptFilter) : undefined,
                urgent: urgentFilter ? true : undefined,
                unresolved: unresolvedFilter ? true : undefined,
                start_date: startDate || undefined,
                end_date: endDate || undefined,
                sort_by: "created_at",
                sort_order: "desc",
            };
            const data = await getAuthorityIssues(params);
            setIssues(data.issues || []);
            setTotal(data.total || 0);
            setPage(data.page || 1);
            setPages(data.pages || 1);
        } catch (err) {
            console.error("Failed to fetch issues:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDepartments();
    }, []);

    useEffect(() => {
        fetchIssues(1);
    }, [statusFilter, categoryFilter, deptFilter, urgentFilter, unresolvedFilter, startDate, endDate]);

    const handleSearchSubmit = (e) => {
        e.preventDefault();
        fetchIssues(1);
    };

    const handleExportCsv = async () => {
        try {
            setExporting(true);
            const blob = await exportAuthorityIssuesCsv({
                status: statusFilter || undefined,
                category: categoryFilter || undefined,
                department_id: deptFilter ? Number(deptFilter) : undefined,
                start_date: startDate || undefined,
                end_date: endDate || undefined,
            });
            const url = window.URL.createObjectURL(new Blob([blob]));
            const link = document.createElement("a");
            link.href = url;
            link.setAttribute("download", `civic_issues_export_${new Date().toISOString().slice(0, 10)}.csv`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            alert("CSV Export failed. Ensure you have appropriate authority permissions.");
        } finally {
            setExporting(false);
        }
    };

    // Open Assign Modal
    const openAssignModal = async (issue) => {
        setAssignModalIssue(issue);
        setAssignDeptId(issue.department_id ? String(issue.department_id) : "");
        setAssignOfficerId(issue.assigned_officer_id ? String(issue.assigned_officer_id) : "");
        setAssignComment("");
        setModalError("");

        try {
            const officers = await getAuthorityOfficers({
                department_id: issue.department_id || undefined,
            });
            setAvailableOfficers(officers || []);
        } catch {
            setAvailableOfficers([]);
        }
    };

    const handleDeptChangeInModal = async (e) => {
        const dId = e.target.value;
        setAssignDeptId(dId);
        setAssignOfficerId("");
        if (dId) {
            try {
                const officers = await getAuthorityOfficers({ department_id: Number(dId) });
                setAvailableOfficers(officers || []);
            } catch {
                setAvailableOfficers([]);
            }
        } else {
            setAvailableOfficers([]);
        }
    };

    const handleAssignSubmit = async (e) => {
        e.preventDefault();
        if (!assignModalIssue) return;
        setModalSubmitting(true);
        setModalError("");

        try {
            await assignAuthorityIssue(assignModalIssue.id, {
                department_id: assignDeptId ? Number(assignDeptId) : undefined,
                assigned_officer_id: assignOfficerId ? Number(assignOfficerId) : undefined,
                comment: assignComment.trim() || undefined,
            });
            setAssignModalIssue(null);
            fetchIssues(page);
        } catch (err) {
            setModalError(err.response?.data?.detail || "Assignment failed.");
        } finally {
            setModalSubmitting(false);
        }
    };

    return (
        <AuthorityLayout title="Civic Issue Dispatch & Administration">
            <div className="issue-mgmt-container">
                {/* FILTER & SEARCH BAR */}
                <form onSubmit={handleSearchSubmit} className="issue-filter-bar">
                    <div style={{ display: "flex", flex: 1, minWidth: "240px", position: "relative" }}>
                        <input
                            type="text"
                            placeholder="Search by title, location, description..."
                            className="issue-search-input"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    </div>

                    <select
                        className="issue-select"
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value)}
                    >
                        <option value="">All Statuses</option>
                        {STATUSES.map((s) => (
                            <option key={s} value={s}>{s}</option>
                        ))}
                    </select>

                    <select
                        className="issue-select"
                        value={categoryFilter}
                        onChange={(e) => setCategoryFilter(e.target.value)}
                    >
                        <option value="">All Categories</option>
                        {CATEGORIES.map((c) => (
                            <option key={c} value={c}>{c}</option>
                        ))}
                    </select>

                    <select
                        className="issue-select"
                        value={deptFilter}
                        onChange={(e) => setDeptFilter(e.target.value)}
                    >
                        <option value="">All Departments</option>
                        {departments.map((d) => (
                            <option key={d.id} value={d.id}>{d.name}</option>
                        ))}
                    </select>

                    {/* DATE RANGE FILTERS */}
                    <input
                        type="date"
                        className="issue-select"
                        title="Start Date"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                        style={{ maxWidth: "135px" }}
                    />

                    <input
                        type="date"
                        className="issue-select"
                        title="End Date"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                        style={{ maxWidth: "135px" }}
                    />

                    <button
                        type="submit"
                        style={{
                            padding: "10px 16px",
                            borderRadius: "8px",
                            background: "#0284c7",
                            color: "#fff",
                            border: "none",
                            cursor: "pointer",
                            fontSize: "13px",
                            fontWeight: 600,
                        }}
                    >
                        Filter
                    </button>

                    <button
                        type="button"
                        onClick={handleExportCsv}
                        disabled={exporting}
                        style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "6px",
                            padding: "10px 14px",
                            borderRadius: "8px",
                            background: "rgba(16, 185, 129, 0.12)",
                            color: "#34d399",
                            border: "1px solid rgba(16, 185, 129, 0.3)",
                            cursor: "pointer",
                            fontSize: "13px",
                            fontWeight: 600,
                        }}
                        title="Export current filtered view as CSV"
                    >
                        <Download size={14} className={exporting ? "animate-spin" : ""} />
                        <span>{exporting ? "Exporting..." : "Export CSV"}</span>
                    </button>
                </form>

                {/* QUICK TOGGLE CHIPS */}
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginTop: "12px", marginBottom: "8px" }}>
                    <button
                        type="button"
                        onClick={() => setUrgentFilter(!urgentFilter)}
                        style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "6px",
                            padding: "6px 14px",
                            borderRadius: "20px",
                            fontSize: "12px",
                            fontWeight: 600,
                            cursor: "pointer",
                            background: urgentFilter ? "rgba(239, 68, 68, 0.2)" : "rgba(148, 163, 184, 0.08)",
                            color: urgentFilter ? "#f87171" : "#94a3b8",
                            border: urgentFilter ? "1px solid rgba(239, 68, 68, 0.4)" : "1px solid rgba(148, 163, 184, 0.15)",
                            transition: "all 0.15s ease",
                        }}
                    >
                        <Flame size={13} />
                        <span>Urgent Only</span>
                    </button>

                    <button
                        type="button"
                        onClick={() => setUnresolvedFilter(!unresolvedFilter)}
                        style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "6px",
                            padding: "6px 14px",
                            borderRadius: "20px",
                            fontSize: "12px",
                            fontWeight: 600,
                            cursor: "pointer",
                            background: unresolvedFilter ? "rgba(245, 158, 11, 0.2)" : "rgba(148, 163, 184, 0.08)",
                            color: unresolvedFilter ? "#fbbf24" : "#94a3b8",
                            border: unresolvedFilter ? "1px solid rgba(245, 158, 11, 0.4)" : "1px solid rgba(148, 163, 184, 0.15)",
                            transition: "all 0.15s ease",
                        }}
                    >
                        <AlertCircle size={13} />
                        <span>Unresolved Backlog</span>
                    </button>

                    {(urgentFilter || unresolvedFilter || statusFilter || categoryFilter || deptFilter || startDate || endDate) && (
                        <button
                            type="button"
                            onClick={() => {
                                setUrgentFilter(false);
                                setUnresolvedFilter(false);
                                setStatusFilter("");
                                setCategoryFilter("");
                                setDeptFilter("");
                                setStartDate("");
                                setEndDate("");
                                setSearch("");
                            }}
                            style={{
                                background: "none",
                                border: "none",
                                color: "#64748b",
                                fontSize: "12px",
                                cursor: "pointer",
                                textDecoration: "underline",
                            }}
                        >
                            Reset filters
                        </button>
                    )}
                </div>

                {/* TABLE OF ISSUES */}
                <div className="issue-table-card">
                    {loading ? (
                        <div style={{ padding: "60px", textAlign: "center", color: "#64748b" }}>
                            <Loader2 size={32} className="animate-spin" style={{ margin: "0 auto 10px" }} />
                            <p>Loading civic issues...</p>
                        </div>
                    ) : issues.length === 0 ? (
                        <div style={{ padding: "60px", textAlign: "center", color: "#64748b" }}>
                            No civic issues match the active filter criteria.
                        </div>
                    ) : (
                        <table className="auth-table">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Title & Location</th>
                                    <th>Category</th>
                                    <th>Department</th>
                                    <th>Assigned Officer</th>
                                    <th>Severity / SLA</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {issues.map((issue) => (
                                    <tr key={issue.id}>
                                        <td style={{ color: "#64748b", fontWeight: 700 }}>#{issue.id}</td>
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
                                            <span style={{ color: issue.department_name ? "#38bdf8" : "#94a3b8" }}>
                                                {issue.department_name || "Unassigned"}
                                            </span>
                                        </td>
                                        <td>
                                            <span style={{ color: issue.assigned_officer_name ? "#4ade80" : "#64748b" }}>
                                                {issue.assigned_officer_name || "Unassigned"}
                                            </span>
                                        </td>
                                        <td>
                                            <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                                                <span style={{
                                                    fontWeight: 700,
                                                    fontSize: "11.5px",
                                                    color: issue.severity === "Critical" ? "#f87171" : issue.severity === "High" ? "#fb923c" : "#38bdf8",
                                                }}>
                                                    {issue.severity}
                                                </span>
                                                {issue.sla_target_hours && (
                                                    <span style={{ fontSize: "10.5px", color: "#64748b" }}>
                                                        {issue.sla_target_hours}h SLA
                                                    </span>
                                                )}
                                                {issue.is_overdue && (
                                                    <span style={{
                                                        display: "inline-flex",
                                                        alignItems: "center",
                                                        gap: "3px",
                                                        fontSize: "10px",
                                                        fontWeight: 700,
                                                        padding: "1px 6px",
                                                        borderRadius: "4px",
                                                        background: "rgba(239, 68, 68, 0.15)",
                                                        color: "#f87171",
                                                        border: "1px solid rgba(239, 68, 68, 0.3)",
                                                        width: "fit-content",
                                                    }}>
                                                        <AlertTriangle size={10} />
                                                        OVERDUE
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        <td>
                                            <span className={`status-pill status-${issue.status.toLowerCase().replace(" ", "_")}`}>
                                                {issue.status}
                                            </span>
                                        </td>
                                        <td>
                                            <div style={{ display: "flex", gap: "8px" }}>
                                                <button
                                                    type="button"
                                                    onClick={() => openAssignModal(issue)}
                                                    style={{
                                                        padding: "4px 10px",
                                                        borderRadius: "6px",
                                                        background: "rgba(168, 85, 247, 0.12)",
                                                        color: "#c084fc",
                                                        border: "1px solid rgba(168, 85, 247, 0.2)",
                                                        cursor: "pointer",
                                                        fontSize: "12px",
                                                        fontWeight: 600,
                                                    }}
                                                >
                                                    Assign
                                                </button>
                                                <Link
                                                    to={`/authority/issues/${issue.id}`}
                                                    style={{
                                                        padding: "4px 10px",
                                                        borderRadius: "6px",
                                                        background: "rgba(14, 165, 233, 0.12)",
                                                        color: "#38bdf8",
                                                        border: "1px solid rgba(14, 165, 233, 0.2)",
                                                        textDecoration: "none",
                                                        fontSize: "12px",
                                                        fontWeight: 600,
                                                    }}
                                                >
                                                    Dossier
                                                </Link>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}

                    {/* PAGINATION */}
                    <div className="issue-pagination">
                        <span>
                            Showing {issues.length} of {total} total issues
                        </span>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <button
                                type="button"
                                className="pagination-btn"
                                disabled={page <= 1}
                                onClick={() => fetchIssues(page - 1)}
                            >
                                Previous
                            </button>
                            <span>
                                Page {page} of {pages}
                            </span>
                            <button
                                type="button"
                                className="pagination-btn"
                                disabled={page >= pages}
                                onClick={() => fetchIssues(page + 1)}
                            >
                                Next
                            </button>
                        </div>
                    </div>
                </div>

                {/* QUICK ASSIGN MODAL */}
                {assignModalIssue && (
                    <div className="modal-overlay">
                        <div className="modal-content">
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                                <h3 className="modal-title" style={{ margin: 0 }}>
                                    Assign Issue #{assignModalIssue.id}
                                </h3>
                                <button
                                    type="button"
                                    onClick={() => setAssignModalIssue(null)}
                                    style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer" }}
                                >
                                    <X size={18} />
                                </button>
                            </div>

                            <p style={{ fontSize: "13px", color: "#94a3b8", margin: "0 0 16px" }}>
                                {assignModalIssue.title} &bull; {assignModalIssue.location}
                            </p>

                            {modalError && (
                                <div style={{ padding: "10px", background: "rgba(239,68,68,0.12)", color: "#f87171", borderRadius: "6px", marginBottom: "16px", fontSize: "12.5px" }}>
                                    {modalError}
                                </div>
                            )}

                            <form onSubmit={handleAssignSubmit} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                                    <label style={{ fontSize: "12.5px", color: "#cbd5e1" }}>Target Department</label>
                                    <select
                                        className="issue-select"
                                        value={assignDeptId}
                                        onChange={handleDeptChangeInModal}
                                    >
                                        <option value="">-- Select Department --</option>
                                        {departments.map((d) => (
                                            <option key={d.id} value={d.id}>{d.name}</option>
                                        ))}
                                    </select>
                                </div>

                                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                                    <label style={{ fontSize: "12.5px", color: "#cbd5e1" }}>Assign to Officer</label>
                                    <select
                                        className="issue-select"
                                        value={assignOfficerId}
                                        onChange={(e) => setAssignOfficerId(e.target.value)}
                                    >
                                        <option value="">-- Unassigned / Department Queue --</option>
                                        {availableOfficers.map((o) => (
                                            <option key={o.id} value={o.id}>
                                                {o.name} ({o.role.replace("_", " ")})
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                                    <label style={{ fontSize: "12.5px", color: "#cbd5e1" }}>Assignment Remarks</label>
                                    <textarea
                                        rows={3}
                                        className="issue-search-input"
                                        placeholder="Add dispatch instructions or notes..."
                                        value={assignComment}
                                        onChange={(e) => setAssignComment(e.target.value)}
                                    />
                                </div>

                                <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
                                    <button
                                        type="button"
                                        className="pagination-btn"
                                        onClick={() => setAssignModalIssue(null)}
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={modalSubmitting}
                                        style={{
                                            padding: "8px 18px",
                                            borderRadius: "6px",
                                            background: "#0284c7",
                                            color: "#fff",
                                            border: "none",
                                            cursor: "pointer",
                                            fontWeight: 600,
                                        }}
                                    >
                                        {modalSubmitting ? "Assigning..." : "Confirm Assignment"}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}
            </div>
        </AuthorityLayout>
    );
}
