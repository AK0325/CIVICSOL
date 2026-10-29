import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
    AlertTriangle,
    ArrowLeft,
    CheckCircle2,
    Clock,
    FileCheck,
    FileImage,
    Loader2,
    MapPin,
    Shield,
    Upload,
    UserCheck,
    X,
} from "lucide-react";
import AuthorityLayout from "../../components/AuthorityLayout";
import {
    assignAuthorityIssue,
    getAuthorityDepartments,
    getAuthorityIssueDetail,
    getAuthorityOfficers,
    resolveAuthorityIssue,
    updateAuthorityIssueStatus,
} from "../../services/authorityApi";
import "./IssueDetails.css";

const API_BASE_URL = "http://127.0.0.1:8000";

export default function IssueDetails() {
    const { id } = useParams();
    const navigate = useNavigate();

    const [issue, setIssue] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    // Assignment state
    const [departments, setDepartments] = useState([]);
    const [officers, setOfficers] = useState([]);
    const [selectedDeptId, setSelectedDeptId] = useState("");
    const [selectedOfficerId, setSelectedOfficerId] = useState("");
    const [assigning, setAssigning] = useState(false);
    const [assignMsg, setAssignMsg] = useState("");

    // Status action state
    const [statusComment, setStatusComment] = useState("");
    const [rejectionReason, setRejectionReason] = useState("");
    const [statusUpdating, setStatusUpdating] = useState(false);

    // Resolution modal state
    const [showResolveModal, setShowResolveModal] = useState(false);
    const [resolutionNotes, setResolutionNotes] = useState("");
    const [resolutionImage, setResolutionImage] = useState(null);
    const [resolving, setResolving] = useState(false);
    const [resolveError, setResolveError] = useState("");

    const fetchIssueData = async () => {
        try {
            setLoading(true);
            const data = await getAuthorityIssueDetail(id);
            setIssue(data);
            setSelectedDeptId(data.department_id ? String(data.department_id) : "");
            setSelectedOfficerId(data.assigned_officer_id ? String(data.assigned_officer_id) : "");

            // Preload departments & officers
            const [depts, offs] = await Promise.all([
                getAuthorityDepartments(),
                getAuthorityOfficers({ department_id: data.department_id || undefined }),
            ]);
            setDepartments(depts || []);
            setOfficers(offs || []);
        } catch (err) {
            setError(err.response?.data?.detail || "Failed to load issue details.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchIssueData();
    }, [id]);

    const handleDeptChange = async (e) => {
        const dId = e.target.value;
        setSelectedDeptId(dId);
        setSelectedOfficerId("");
        if (dId) {
            try {
                const offs = await getAuthorityOfficers({ department_id: Number(dId) });
                setOfficers(offs || []);
            } catch {
                setOfficers([]);
            }
        } else {
            setOfficers([]);
        }
    };

    const handleSaveAssignment = async () => {
        setAssigning(true);
        setAssignMsg("");
        setError("");
        try {
            await assignAuthorityIssue(id, {
                department_id: selectedDeptId ? Number(selectedDeptId) : undefined,
                assigned_officer_id: selectedOfficerId ? Number(selectedOfficerId) : undefined,
            });
            setAssignMsg("Assignment updated successfully.");
            fetchIssueData();
        } catch (err) {
            setError(err.response?.data?.detail || "Assignment update failed.");
        } finally {
            setAssigning(false);
        }
    };

    const handleStatusTransition = async (targetStatus) => {
        setStatusUpdating(true);
        setError("");
        try {
            await updateAuthorityIssueStatus(id, {
                status: targetStatus,
                comment: statusComment.trim() || undefined,
                rejection_reason: targetStatus === "Rejected" ? rejectionReason.trim() : undefined,
            });
            setStatusComment("");
            setRejectionReason("");
            fetchIssueData();
        } catch (err) {
            setError(err.response?.data?.detail || "Status transition failed.");
        } finally {
            setStatusUpdating(false);
        }
    };

    const handleResolveSubmit = async (e) => {
        e.preventDefault();
        if (!resolutionNotes.trim()) {
            setResolveError("Resolution notes are mandatory.");
            return;
        }
        if (!resolutionImage) {
            setResolveError("Resolution photo evidence is required.");
            return;
        }

        setResolving(true);
        setResolveError("");
        try {
            const formData = new FormData();
            formData.append("resolution_notes", resolutionNotes.trim());
            formData.append("image", resolutionImage);

            await resolveAuthorityIssue(id, formData);
            setShowResolveModal(false);
            setResolutionNotes("");
            setResolutionImage(null);
            fetchIssueData();
        } catch (err) {
            setResolveError(err.response?.data?.detail || "Failed to resolve issue.");
        } finally {
            setResolving(false);
        }
    };

    if (loading) {
        return (
            <AuthorityLayout title="Issue Dossier">
                <div style={{ padding: "80px", textAlign: "center", color: "#64748b" }}>
                    <Loader2 size={36} className="animate-spin" style={{ margin: "0 auto 10px" }} />
                    <p>Loading issue dossier #{id}...</p>
                </div>
            </AuthorityLayout>
        );
    }

    if (!issue) {
        return (
            <AuthorityLayout title="Issue Dossier">
                <div style={{ padding: "40px", color: "#f87171" }}>{error || "Issue not found."}</div>
            </AuthorityLayout>
        );
    }

    const reportPhotoUrl = issue.image_path ? `${API_BASE_URL}/${issue.image_path}` : "";
    const resolvePhotoUrl = issue.resolution_image_path ? `${API_BASE_URL}/${issue.resolution_image_path}` : "";

    return (
        <AuthorityLayout title={`Issue Dossier #${issue.id}`}>
            <div className="issue-details-container">
                {/* BACK LINK & TITLE */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <Link
                        to="/authority/issues"
                        style={{ display: "flex", alignItems: "center", gap: "6px", color: "#38bdf8", textDecoration: "none", fontSize: "13px", fontWeight: 600 }}
                    >
                        <ArrowLeft size={16} />
                        <span>Back to Issue Queue</span>
                    </Link>

                    <span className={`status-pill status-${issue.status.toLowerCase().replace(" ", "_")}`}>
                        Status: {issue.status}
                    </span>
                </div>

                {error && (
                    <div style={{ padding: "12px", background: "rgba(239,68,68,0.12)", color: "#f87171", borderRadius: "8px" }}>
                        {error}
                    </div>
                )}
                {assignMsg && (
                    <div style={{ padding: "12px", background: "rgba(34,197,94,0.12)", color: "#4ade80", borderRadius: "8px" }}>
                        {assignMsg}
                    </div>
                )}

                <div className="details-two-col">
                    {/* LEFT COLUMN: ISSUE DETAILS & EVIDENCE PHOTOS */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                        <div className="auth-card">
                            <h2 style={{ fontSize: "20px", fontWeight: 800, color: "#fff", margin: "0 0 10px" }}>
                                {issue.title}
                            </h2>

                            <div style={{ display: "flex", flexWrap: "wrap", gap: "16px", fontSize: "13px", color: "#94a3b8", marginBottom: "16px" }}>
                                <span><strong>Category:</strong> {issue.category}</span>
                                <span><strong>Severity:</strong> {issue.severity}</span>
                                <span><strong>Priority:</strong> {issue.priority}</span>
                                <span><strong>Reported:</strong> {new Date(issue.created_at).toLocaleString()}</span>
                            </div>

                            <p style={{ fontSize: "14px", lineHeight: "1.6", color: "#cbd5e1", background: "rgba(8,14,26,0.6)", padding: "14px", borderRadius: "8px", border: "1px solid rgba(148,163,184,0.1)" }}>
                                {issue.description || "No detailed description provided by citizen."}
                            </p>

                            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "14px", color: "#38bdf8", fontSize: "13px" }}>
                                <MapPin size={16} />
                                <span>{issue.location} &bull; Coordinates: {issue.latitude.toFixed(6)}, {issue.longitude.toFixed(6)}</span>
                            </div>

                            {/* EVIDENCE PHOTOS BEFORE & AFTER */}
                            <div className="evidence-photos-grid">
                                <div className="photo-card">
                                    <div className="photo-card-header">Citizen Report Photo</div>
                                    <img src={reportPhotoUrl} alt="Report evidence" />
                                </div>

                                <div className="photo-card">
                                    <div className="photo-card-header">Resolution Evidence Photo</div>
                                    {resolvePhotoUrl ? (
                                        <img src={resolvePhotoUrl} alt="Resolution evidence" />
                                    ) : (
                                        <div style={{ height: "220px", display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b", fontSize: "13px" }}>
                                            Awaiting resolution upload
                                        </div>
                                    )}
                                </div>
                            </div>

                            {issue.resolution_notes && (
                                <div style={{ marginTop: "18px", padding: "14px", background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.2)", borderRadius: "8px" }}>
                                    <h4 style={{ color: "#4ade80", margin: "0 0 6px", fontSize: "13.5px", fontWeight: 700 }}>
                                        Official Resolution Notes
                                    </h4>
                                    <p style={{ margin: 0, fontSize: "13px", color: "#cbd5e1" }}>
                                        {issue.resolution_notes}
                                    </p>
                                    <span style={{ fontSize: "11px", color: "#64748b", marginTop: "4px", display: "inline-block" }}>
                                        Resolved by {issue.resolved_by_name || "Officer"} on {new Date(issue.resolved_at).toLocaleString()}
                                    </span>
                                </div>
                            )}

                            {issue.rejection_reason && (
                                <div style={{ marginTop: "18px", padding: "14px", background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: "8px" }}>
                                    <h4 style={{ color: "#f87171", margin: "0 0 6px", fontSize: "13.5px", fontWeight: 700 }}>
                                        Rejection Reason
                                    </h4>
                                    <p style={{ margin: 0, fontSize: "13px", color: "#cbd5e1" }}>
                                        {issue.rejection_reason}
                                    </p>
                                </div>
                            )}
                        </div>

                        {/* STATUS HISTORY TIMELINE */}
                        <div className="auth-card">
                            <h3 className="auth-card-title" style={{ marginBottom: "20px" }}>
                                Chronological Status Audit Timeline
                            </h3>

                            <div className="timeline-container">
                                {issue.status_history.map((hist) => (
                                    <div key={hist.id} className="timeline-item">
                                        <div className="timeline-dot" />
                                        <div className="timeline-header">
                                            <span className="timeline-user">
                                                {hist.changed_by_name} &bull; <span style={{ color: "#38bdf8" }}>{hist.to_status}</span>
                                            </span>
                                            <span className="timeline-time">
                                                {new Date(hist.created_at).toLocaleString()}
                                            </span>
                                        </div>
                                        {hist.comment && (
                                            <div className="timeline-comment">{hist.comment}</div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* RIGHT COLUMN: ACTIONS, DISPATCH, & CITIZEN CONTACT */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                        {/* DISPATCH & ASSIGNMENT */}
                        <div className="auth-card">
                            <h3 className="auth-card-title" style={{ marginBottom: "16px" }}>
                                Municipal Dispatch & Assignment
                            </h3>

                            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                                <div>
                                    <label style={{ fontSize: "12px", color: "#94a3b8" }}>Department</label>
                                    <select
                                        className="issue-select"
                                        style={{ width: "100%", marginTop: "4px" }}
                                        value={selectedDeptId}
                                        onChange={handleDeptChange}
                                    >
                                        <option value="">-- Unassigned Department --</option>
                                        {departments.map((d) => (
                                            <option key={d.id} value={d.id}>{d.name}</option>
                                        ))}
                                    </select>
                                </div>

                                <div>
                                    <label style={{ fontSize: "12px", color: "#94a3b8" }}>Field Officer</label>
                                    <select
                                        className="issue-select"
                                        style={{ width: "100%", marginTop: "4px" }}
                                        value={selectedOfficerId}
                                        onChange={(e) => setSelectedOfficerId(e.target.value)}
                                    >
                                        <option value="">-- Unassigned Officer --</option>
                                        {officers.map((o) => (
                                            <option key={o.id} value={o.id}>
                                                {o.name} ({o.role.replace("_", " ")})
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <button
                                    type="button"
                                    onClick={handleSaveAssignment}
                                    disabled={assigning}
                                    style={{
                                        padding: "10px",
                                        borderRadius: "8px",
                                        background: "#0284c7",
                                        color: "#fff",
                                        border: "none",
                                        cursor: "pointer",
                                        fontWeight: 600,
                                        marginTop: "6px",
                                    }}
                                >
                                    {assigning ? "Updating..." : "Update Assignment"}
                                </button>
                            </div>
                        </div>

                        {/* STATUS TRANSITIONS */}
                        <div className="auth-card">
                            <h3 className="auth-card-title" style={{ marginBottom: "16px" }}>
                                Status Lifecycle Actions
                            </h3>

                            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                                {issue.status === "Reported" && (
                                    <button
                                        type="button"
                                        onClick={() => handleStatusTransition("Under Review")}
                                        disabled={statusUpdating}
                                        style={{ padding: "10px", borderRadius: "8px", background: "rgba(14,165,233,0.15)", color: "#38bdf8", border: "1px solid rgba(14,165,233,0.3)", cursor: "pointer", fontWeight: 600 }}
                                    >
                                        Advance to Under Review
                                    </button>
                                )}

                                {["Assigned", "Under Review"].includes(issue.status) && (
                                    <button
                                        type="button"
                                        onClick={() => handleStatusTransition("In Progress")}
                                        disabled={statusUpdating}
                                        style={{ padding: "10px", borderRadius: "8px", background: "rgba(59,130,246,0.15)", color: "#60a5fa", border: "1px solid rgba(59,130,246,0.3)", cursor: "pointer", fontWeight: 600 }}
                                    >
                                        Mark In Progress (Work Commenced)
                                    </button>
                                )}

                                {["In Progress", "Assigned"].includes(issue.status) && (
                                    <button
                                        type="button"
                                        onClick={() => setShowResolveModal(true)}
                                        style={{ padding: "10px", borderRadius: "8px", background: "linear-gradient(135deg, #16a34a, #15803d)", color: "#ffffff", border: "none", cursor: "pointer", fontWeight: 700 }}
                                    >
                                        Complete & Upload Resolution Evidence
                                    </button>
                                )}

                                {issue.status === "Resolved" && (
                                    <button
                                        type="button"
                                        onClick={() => handleStatusTransition("Reopened")}
                                        disabled={statusUpdating}
                                        style={{ padding: "10px", borderRadius: "8px", background: "rgba(249,115,22,0.15)", color: "#fb923c", border: "1px solid rgba(249,115,22,0.3)", cursor: "pointer", fontWeight: 600 }}
                                    >
                                        Reopen Issue (Resolution Disputed)
                                    </button>
                                )}

                                {issue.status !== "Rejected" && issue.status !== "Resolved" && (
                                    <div style={{ marginTop: "10px", paddingTop: "12px", borderTop: "1px solid rgba(148,163,184,0.1)" }}>
                                        <input
                                            type="text"
                                            placeholder="Reason for rejection..."
                                            className="issue-search-input"
                                            style={{ marginBottom: "8px" }}
                                            value={rejectionReason}
                                            onChange={(e) => setRejectionReason(e.target.value)}
                                        />
                                        <button
                                            type="button"
                                            onClick={() => handleStatusTransition("Rejected")}
                                            disabled={statusUpdating || !rejectionReason.trim()}
                                            style={{ width: "100%", padding: "8px", borderRadius: "6px", background: "rgba(239,68,68,0.1)", color: "#f87171", border: "1px solid rgba(239,68,68,0.2)", cursor: "pointer", fontWeight: 600 }}
                                        >
                                            Reject Civic Report
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* CITIZEN PROFILE */}
                        <div className="auth-card">
                            <h3 className="auth-card-title" style={{ marginBottom: "14px" }}>
                                Reporting Citizen Profile
                            </h3>
                            <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "13px", color: "#cbd5e1" }}>
                                <div><strong>Name:</strong> {issue.reporter_name}</div>
                                <div><strong>Citizen ID:</strong> {issue.reporter_citizen_id || "Unregistered"}</div>
                                <div><strong>Contact (Masked):</strong> {issue.reporter_mobile_masked || "Unavailable"}</div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* RESOLUTION EVIDENCE MODAL */}
                {showResolveModal && (
                    <div className="modal-overlay">
                        <div className="modal-content" style={{ maxWidth: "540px" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                                <h3 className="modal-title" style={{ margin: 0, color: "#4ade80" }}>
                                    Submit Resolution Evidence
                                </h3>
                                <button
                                    type="button"
                                    onClick={() => setShowResolveModal(false)}
                                    style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer" }}
                                >
                                    <X size={18} />
                                </button>
                            </div>

                            <p style={{ fontSize: "13px", color: "#94a3b8", margin: "0 0 16px" }}>
                                Uploading verified resolution evidence closes the issue and awards <strong>+20 Civic Credits</strong> to the reporting citizen.
                            </p>

                            {resolveError && (
                                <div style={{ padding: "10px", background: "rgba(239,68,68,0.12)", color: "#f87171", borderRadius: "6px", marginBottom: "16px", fontSize: "12.5px" }}>
                                    {resolveError}
                                </div>
                            )}

                            <form onSubmit={handleResolveSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                                <div>
                                    <label style={{ fontSize: "12.5px", color: "#cbd5e1", display: "block", marginBottom: "6px" }}>
                                        Work Completion Notes (Mandatory)
                                    </label>
                                    <textarea
                                        rows={3}
                                        className="issue-search-input"
                                        placeholder="Describe the physical repair, materials used, and on-site clearance..."
                                        value={resolutionNotes}
                                        onChange={(e) => setResolutionNotes(e.target.value)}
                                        required
                                    />
                                </div>

                                <div>
                                    <label style={{ fontSize: "12.5px", color: "#cbd5e1", display: "block", marginBottom: "6px" }}>
                                        Resolution Evidence Photo (Mandatory)
                                    </label>
                                    <input
                                        type="file"
                                        accept="image/jpeg,image/png,image/webp"
                                        onChange={(e) => setResolutionImage(e.target.files?.[0] || null)}
                                        required
                                        style={{ fontSize: "13px", color: "#94a3b8" }}
                                    />
                                </div>

                                <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
                                    <button
                                        type="button"
                                        className="pagination-btn"
                                        onClick={() => setShowResolveModal(false)}
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={resolving}
                                        style={{
                                            padding: "9px 20px",
                                            borderRadius: "8px",
                                            background: "linear-gradient(135deg, #16a34a, #15803d)",
                                            color: "#fff",
                                            border: "none",
                                            cursor: "pointer",
                                            fontWeight: 700,
                                        }}
                                    >
                                        {resolving ? "Verifying..." : "Confirm & Award +20 Credits"}
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
