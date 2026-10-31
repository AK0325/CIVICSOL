import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
    AlertTriangle,
    ArrowLeft,
    BrainCircuit,
    CheckCircle2,
    Clock,
    Cpu,
    ExternalLink,
    FileCheck,
    FileImage,
    History,
    Info,
    Layers,
    Loader2,
    MapPin,
    RefreshCw,
    Shield,
    ShieldAlert,
    Sparkles,
    Tag,
    ThumbsDown,
    ThumbsUp,
    Upload,
    UserCheck,
    X,
    Flag,
    GitMerge,
} from "lucide-react";
import AuthorityLayout from "../../components/AuthorityLayout";
import {
    approveIssueAiRecommendation,
    assignAuthorityIssue,
    flagAiFalsePositive,
    getAuthorityDepartments,
    getAuthorityIssueDetail,
    getAuthorityOfficers,
    getIssueAiAnalysis,
    getIssueAiHistory,
    linkDuplicateIssue,
    reanalyzeIssueAi,
    rejectIssueAiRecommendation,
    resolveAuthorityIssue,
    runIssueAiAnalysis,
    updateAuthorityIssueStatus,
} from "../../services/authorityApi";
import "./IssueDetails.css";

const API_BASE_URL = import.meta.env?.VITE_API_URL || "http://127.0.0.1:8000";

export default function IssueDetails() {
    const { id } = useParams();
    const navigate = useNavigate();

    const [issue, setIssue] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    // AI Intelligence state
    const [aiData, setAiData] = useState(null);
    const [aiLoading, setAiLoading] = useState(false);
    const [aiActionMsg, setAiActionMsg] = useState("");
    const [aiActionError, setAiActionError] = useState("");
    const [aiReviewComment, setAiReviewComment] = useState("");

    // AI History modal state
    const [showHistoryModal, setShowHistoryModal] = useState(false);
    const [historyList, setHistoryList] = useState([]);
    const [historyLoading, setHistoryLoading] = useState(false);

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

    // False Positive Feedback modal state
    const [showFpModal, setShowFpModal] = useState(false);
    const [fpClass, setFpClass] = useState("");
    const [fpReason, setFpReason] = useState("");
    const [fpSubmitting, setFpSubmitting] = useState(false);
    const [fpMsg, setFpMsg] = useState("");
    const [fpError, setFpError] = useState("");

    // Duplicate Linking/Merging modal state
    const [showDupModal, setShowDupModal] = useState(false);
    const [dupTargetId, setDupTargetId] = useState(null);
    const [dupAction, setDupAction] = useState("LINK");
    const [dupNotes, setDupNotes] = useState("");
    const [dupSubmitting, setDupSubmitting] = useState(false);
    const [dupMsg, setDupMsg] = useState("");
    const [dupError, setDupError] = useState("");

    const handleOpenFpModal = (className = "") => {
        setFpClass(className);
        setFpReason("");
        setFpMsg("");
        setFpError("");
        setShowFpModal(true);
    };

    const handleSubmitFp = async () => {
        if (!fpClass || !fpReason.trim()) {
            setFpError("Please specify the detection class and officer justification.");
            return;
        }
        setFpSubmitting(true);
        setFpError("");
        try {
            const res = await flagAiFalsePositive(id, {
                class_name: fpClass,
                reason: fpReason.trim(),
            });
            setAiData(res);
            setFpMsg(`Detection '${fpClass}' flagged as false positive.`);
            setShowFpModal(false);
        } catch (err) {
            setFpError(err.response?.data?.detail || "Failed to submit false positive feedback.");
        } finally {
            setFpSubmitting(false);
        }
    };

    const handleOpenDupModal = (targetIssueId, defaultAction = "LINK") => {
        setDupTargetId(targetIssueId);
        setDupAction(defaultAction);
        setDupNotes("");
        setDupMsg("");
        setDupError("");
        setShowDupModal(true);
    };

    const handleSubmitDuplicateAction = async () => {
        if (!dupTargetId) return;
        setDupSubmitting(true);
        setDupError("");
        try {
            const res = await linkDuplicateIssue(id, {
                primary_issue_id: dupTargetId,
                action: dupAction,
                notes: dupNotes.trim() || undefined,
            });
            setAiData(res);
            setDupMsg(`Issue successfully ${dupAction === "MERGE" ? "merged into" : "linked with"} Issue #${dupTargetId}.`);
            setShowDupModal(false);
            const fresh = await getAuthorityIssueDetail(id);
            setIssue(fresh);
        } catch (err) {
            setDupError(err.response?.data?.detail || "Failed to process duplicate action.");
        } finally {
            setDupSubmitting(false);
        }
    };

    const fetchIssueData = async () => {
        try {
            setLoading(true);
            const data = await getAuthorityIssueDetail(id);
            setIssue(data);
            setSelectedDeptId(data.department_id ? String(data.department_id) : "");
            setSelectedOfficerId(data.assigned_officer_id ? String(data.assigned_officer_id) : "");

            // Preload departments, officers, and AI analysis
            const [depts, offs, aiRes] = await Promise.all([
                getAuthorityDepartments().catch(() => []),
                getAuthorityOfficers({ department_id: data.department_id || undefined }).catch(() => []),
                getIssueAiAnalysis(id).catch(() => ({ has_analysis: false, latest_analysis: null })),
            ]);
            setDepartments(depts || []);
            setOfficers(offs || []);
            setAiData(aiRes || { has_analysis: false, latest_analysis: null });
        } catch (err) {
            setError(err.response?.data?.detail || "Failed to load issue details.");
        } finally {
            setLoading(false);
        }
    };

    const handleRunAiAnalysis = async (isReanalyze = false) => {
        setAiLoading(true);
        setAiActionMsg("");
        setAiActionError("");
        try {
            const res = isReanalyze
                ? await reanalyzeIssueAi(id)
                : await runIssueAiAnalysis(id);
            setAiData(res);
            setAiActionMsg(
                isReanalyze
                    ? "AI re-analysis completed and recorded in audit history."
                    : "AI analysis pipeline executed successfully."
            );
            await fetchIssueData();
        } catch (err) {
            setAiActionError(err.response?.data?.detail || "Failed to execute AI analysis.");
        } finally {
            setAiLoading(false);
        }
    };

    const handleApproveAi = async () => {
        setAiLoading(true);
        setAiActionMsg("");
        setAiActionError("");
        try {
            const res = await approveIssueAiRecommendation(id, {
                apply_category: true,
                apply_severity: true,
                apply_priority: true,
                apply_department: true,
                comment: aiReviewComment.trim() || "Approved AI civic recommendations.",
            });
            setAiData(res);
            setAiReviewComment("");
            setAiActionMsg("AI recommendation approved and applied to official issue values.");
            await fetchIssueData();
        } catch (err) {
            setAiActionError(err.response?.data?.detail || "Failed to approve AI recommendation.");
        } finally {
            setAiLoading(false);
        }
    };

    const handleRejectAi = async () => {
        if (!aiReviewComment.trim()) {
            setAiActionError("Rejection comment/rationale is mandatory when rejecting AI recommendations.");
            return;
        }
        setAiLoading(true);
        setAiActionMsg("");
        setAiActionError("");
        try {
            const res = await rejectIssueAiRecommendation(id, {
                comment: aiReviewComment.trim(),
            });
            setAiData(res);
            setAiReviewComment("");
            setAiActionMsg("AI recommendation rejected. Official issue values remain unchanged.");
            await fetchIssueData();
        } catch (err) {
            setAiActionError(err.response?.data?.detail || "Failed to reject AI recommendation.");
        } finally {
            setAiLoading(false);
        }
    };

    const handleOpenHistory = async () => {
        setShowHistoryModal(true);
        setHistoryLoading(true);
        try {
            const res = await getIssueAiHistory(id);
            setHistoryList(res?.history || []);
        } catch (err) {
            setAiActionError(err.response?.data?.detail || "Failed to retrieve analysis history.");
        } finally {
            setHistoryLoading(false);
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
            <AuthorityLayout title="View Details">
                <div style={{ padding: "80px", textAlign: "center", color: "#64748b" }}>
                    <Loader2 size={36} className="animate-spin" style={{ margin: "0 auto 10px" }} />
                    <p>Loading issue details #{id}...</p>
                </div>
            </AuthorityLayout>
        );
    }

    if (!issue) {
        return (
            <AuthorityLayout title="View Details">
                <div style={{ padding: "40px", color: "#f87171" }}>{error || "Issue not found."}</div>
            </AuthorityLayout>
        );
    }

    const reportPhotoUrl = issue.image_path ? `${API_BASE_URL}/${issue.image_path}` : "";
    const resolvePhotoUrl = issue.resolution_image_path ? `${API_BASE_URL}/${issue.resolution_image_path}` : "";
    const latestAi = aiData?.has_analysis ? (aiData?.analysis || aiData?.latest_analysis) : null;
    const annotatedPhotoUrl = latestAi?.annotated_image_path
        ? `${API_BASE_URL}/${latestAi.annotated_image_path}`
        : "";

    const similarIssues =
        latestAi?.similar_nearby_reports ||
        latestAi?.analysis_metadata?.similar_nearby_reports ||
        latestAi?.analysis_metadata?.similar_issues ||
        [];

    const priorityScore =
        latestAi?.analysis_metadata?.priority_scoring?.composite_score ??
        (issue.priority_score !== null && issue.priority_score !== undefined
            ? Math.round(issue.priority_score)
            : null);

    const priorityBreakdown = latestAi?.analysis_metadata?.priority_scoring?.scoring_breakdown || null;
    const safetyConcerns = latestAi?.analysis_metadata?.safety_concerns || [];
    const scoringFactors = latestAi?.analysis_metadata?.priority_scoring?.factors || [];

    // Duplicate & Suspicious Intelligence derivation
    const duplicateAssessment = latestAi?.analysis_metadata?.duplicate_assessment || {};
    const overallDuplicateClass =
        duplicateAssessment?.overall_classification ||
        (similarIssues.some((s) => s.classification === "EXACT_REPLAY")
            ? "EXACT_REPLAY"
            : similarIssues.some((s) => s.classification === "HIGH_CONFIDENCE_DUPLICATE" || s.duplicate_score >= 70)
            ? "HIGH_CONFIDENCE_DUPLICATE"
            : similarIssues.some((s) => s.classification === "POSSIBLE_DUPLICATE" || s.duplicate_score >= 40)
            ? "POSSIBLE_DUPLICATE"
            : "UNIQUE_REPORT");

    const suspiciousAssessment = latestAi?.analysis_metadata?.suspicious_assessment || null;
    const evidenceConsistency =
        latestAi?.analysis_metadata?.evidence_consistency ||
        (latestAi?.predicted_category && latestAi.predicted_category.toLowerCase() !== issue.category.toLowerCase()
            ? "INCONSISTENT"
            : "CONSISTENT");
    const requiresHumanReview =
        latestAi?.analysis_metadata?.requires_human_review || evidenceConsistency === "INCONSISTENT";
    const isLowConfidence =
        latestAi?.analysis_metadata?.is_low_confidence ||
        (latestAi?.confidence_score !== null &&
            latestAi?.confidence_score !== undefined &&
            Number(latestAi.confidence_score) < 0.45);
    const lowConfidenceWarning =
        latestAi?.analysis_metadata?.low_confidence_warning ||
        (isLowConfidence
            ? `Detection confidence is below 45% (${(Number(latestAi.confidence_score) * 100).toFixed(1)}%). Authority verification recommended.`
            : null);

    const falsePositiveFeedback = latestAi?.analysis_metadata?.false_positive_feedback || [];
    const duplicateLink = latestAi?.analysis_metadata?.duplicate_link || null;

    // Helper color mappings
    const getPriorityColor = (score) => {
        if (score === null || score === undefined) return "#94a3b8";
        if (score >= 75) return "#ef4444"; // red
        if (score >= 52) return "#f97316"; // orange
        if (score >= 30) return "#eab308"; // yellow
        return "#22c55e"; // green
    };

    const getDuplicateBadgeColor = (cls) => {
        switch (cls) {
            case "EXACT_REPLAY":
                return { bg: "rgba(239, 68, 68, 0.2)", border: "#ef4444", text: "#f87171" };
            case "HIGH_CONFIDENCE_DUPLICATE":
                return { bg: "rgba(249, 115, 22, 0.2)", border: "#f97316", text: "#fb923c" };
            case "POSSIBLE_DUPLICATE":
                return { bg: "rgba(234, 179, 8, 0.2)", border: "#eab308", text: "#facc15" };
            default:
                return { bg: "rgba(34, 197, 94, 0.2)", border: "#22c55e", text: "#4ade80" };
        }
    };

    const getRiskColor = (level) => {
        switch (level) {
            case "HIGH_RISK":
            case "INVALID_EVIDENCE":
                return { bg: "rgba(239, 68, 68, 0.2)", border: "#ef4444", text: "#f87171" };
            case "REVIEW_REQUIRED":
                return { bg: "rgba(249, 115, 22, 0.2)", border: "#f97316", text: "#fb923c" };
            case "LOW_RISK":
                return { bg: "rgba(59, 130, 246, 0.2)", border: "#3b82f6", text: "#60a5fa" };
            default:
                return { bg: "rgba(34, 197, 94, 0.2)", border: "#22c55e", text: "#4ade80" };
        }
    };

    return (
        <AuthorityLayout title={`View Details — Issue #${issue.id}`}>
            <div className="issue-details-container">
                {/* HEADER / NAVIGATION */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "10px" }}>
                    <Link
                        to="/authority/issues"
                        style={{ display: "flex", alignItems: "center", gap: "6px", color: "#38bdf8", textDecoration: "none", fontSize: "13px", fontWeight: 600 }}
                    >
                        <ArrowLeft size={16} />
                        <span>Back to Issue Queue</span>
                    </Link>

                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <span className={`status-pill status-${issue.status.toLowerCase().replace(" ", "_")}`}>
                            Status: {issue.status}
                        </span>
                        {latestAi && (
                            <button
                                type="button"
                                onClick={handleOpenHistory}
                                style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "6px",
                                    padding: "6px 12px",
                                    borderRadius: "6px",
                                    background: "rgba(148, 163, 184, 0.12)",
                                    color: "#cbd5e1",
                                    border: "1px solid rgba(148, 163, 184, 0.25)",
                                    fontSize: "12px",
                                    fontWeight: 600,
                                    cursor: "pointer",
                                }}
                            >
                                <History size={14} />
                                <span>AI History</span>
                            </button>
                        )}
                    </div>
                </div>

                {error && (
                    <div style={{ padding: "12px", background: "rgba(239,68,68,0.12)", color: "#f87171", borderRadius: "8px", fontSize: "13px" }}>
                        {error}
                    </div>
                )}
                {assignMsg && (
                    <div style={{ padding: "12px", background: "rgba(34,197,94,0.12)", color: "#4ade80", borderRadius: "8px", fontSize: "13px" }}>
                        {assignMsg}
                    </div>
                )}

                <div className="details-two-col">
                    {/* LEFT COLUMN: SECTIONS A TO F */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>

                        {/* ========================================================
                            SECTION A: CITIZEN EVIDENCE
                        ======================================================== */}
                        <div className="auth-card section-card">
                            <div className="section-header">
                                <div className="section-tag-badge">SECTION A</div>
                                <h3 className="section-title">CITIZEN EVIDENCE</h3>
                            </div>

                            <div style={{ marginBottom: "14px" }}>
                                <h2 style={{ fontSize: "20px", fontWeight: 800, color: "#fff", margin: "0 0 8px" }}>
                                    {issue.title}
                                </h2>
                                <div style={{ display: "flex", flexWrap: "wrap", gap: "14px", fontSize: "12.5px", color: "#94a3b8" }}>
                                    <span><strong>Category:</strong> <span style={{ color: "#e2e8f0" }}>{issue.category}</span></span>
                                    <span><strong>Severity:</strong> <span style={{ color: "#e2e8f0" }}>{issue.severity}</span></span>
                                    <span><strong>Priority:</strong> <span style={{ color: "#e2e8f0" }}>{issue.priority}</span></span>
                                    <span><strong>Reported:</strong> <span style={{ color: "#e2e8f0" }}>{new Date(issue.created_at).toLocaleString()}</span></span>
                                </div>
                            </div>

                            <div style={{ fontSize: "13.5px", lineHeight: "1.6", color: "#cbd5e1", background: "rgba(8,14,26,0.6)", padding: "14px", borderRadius: "8px", border: "1px solid rgba(148,163,184,0.1)", marginBottom: "14px" }}>
                                {issue.description || "No citizen description text provided."}
                            </div>

                            <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#38bdf8", fontSize: "13px", marginBottom: "16px" }}>
                                <MapPin size={16} />
                                <span>{issue.location} &bull; Coordinates: {issue.latitude.toFixed(6)}, {issue.longitude.toFixed(6)}</span>
                            </div>

                            {/* Original vs Resolution photo grid */}
                            <div className="evidence-photos-grid">
                                <div className="photo-card">
                                    <div className="photo-card-header">Original Citizen Upload</div>
                                    {reportPhotoUrl ? (
                                        <img src={reportPhotoUrl} alt="Report evidence" />
                                    ) : (
                                        <div style={{ height: "220px", display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b", fontSize: "13px" }}>
                                            No photo submitted
                                        </div>
                                    )}
                                </div>

                                <div className="photo-card">
                                    <div className="photo-card-header">Resolution Evidence Photo</div>
                                    {resolvePhotoUrl ? (
                                        <img src={resolvePhotoUrl} alt="Resolution evidence" />
                                    ) : (
                                        <div style={{ height: "220px", display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b", fontSize: "13px" }}>
                                            Awaiting municipal resolution
                                        </div>
                                    )}
                                </div>
                            </div>

                            {issue.resolution_notes && (
                                <div style={{ marginTop: "16px", padding: "14px", background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.2)", borderRadius: "8px" }}>
                                    <h4 style={{ color: "#4ade80", margin: "0 0 6px", fontSize: "13px", fontWeight: 700 }}>
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
                                <div style={{ marginTop: "16px", padding: "14px", background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: "8px" }}>
                                    <h4 style={{ color: "#f87171", margin: "0 0 6px", fontSize: "13px", fontWeight: 700 }}>
                                        Rejection Reason
                                    </h4>
                                    <p style={{ margin: 0, fontSize: "13px", color: "#cbd5e1" }}>
                                        {issue.rejection_reason}
                                    </p>
                                </div>
                            )}
                        </div>

                        {/* ========================================================
                            SECTION B: YOLOV8 DETECTION
                        ======================================================== */}
                        <div className="auth-card section-card" style={{ borderColor: isLowConfidence ? "rgba(245, 158, 11, 0.45)" : "rgba(56, 189, 248, 0.35)" }}>
                            <div className="section-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                    <div className="section-tag-badge cv-badge">SECTION B</div>
                                    <h3 className="section-title">COMPUTER VISION & YOLOV8 DETECTION</h3>
                                </div>
                                {latestAi && (
                                    <button
                                        type="button"
                                        onClick={() => handleOpenFpModal(latestAi.detected_objects?.[0]?.label || "")}
                                        style={{
                                            display: "flex",
                                            alignItems: "center",
                                            gap: "5px",
                                            padding: "5px 10px",
                                            borderRadius: "6px",
                                            background: "rgba(239, 68, 68, 0.15)",
                                            border: "1px solid rgba(239, 68, 68, 0.35)",
                                            color: "#f87171",
                                            fontSize: "11.5px",
                                            fontWeight: 600,
                                            cursor: "pointer",
                                        }}
                                    >
                                        <Flag size={12} />
                                        <span>Flag False Positive</span>
                                    </button>
                                )}
                            </div>

                            {latestAi ? (
                                <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                                    {/* Low Confidence Warning Alert */}
                                    {lowConfidenceWarning && (
                                        <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "10px 14px", background: "rgba(245, 158, 11, 0.12)", border: "1px solid rgba(245, 158, 11, 0.35)", borderRadius: "8px", color: "#fbbf24", fontSize: "12.5px" }}>
                                            <AlertTriangle size={16} />
                                            <span><strong>Low Confidence Warning:</strong> {lowConfidenceWarning}</span>
                                        </div>
                                    )}

                                    {/* Detection Status Banner */}
                                    <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "10px", background: "rgba(8,14,26,0.65)", padding: "10px 14px", borderRadius: "8px", border: "1px solid rgba(148,163,184,0.12)" }}>
                                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                            <span style={{ fontSize: "12px", color: "#94a3b8" }}>Vision Status:</span>
                                            <span className={`status-pill status-${(latestAi.analysis_metadata?.vision_status || latestAi.processing_status || "PENDING").toLowerCase()}`}>
                                                {latestAi.analysis_metadata?.vision_status || latestAi.processing_status}
                                            </span>
                                        </div>
                                        <div style={{ fontSize: "12px", color: "#94a3b8" }}>
                                            Model: <strong style={{ color: "#38bdf8" }}>{latestAi.model_name || "CivicYOLO-v8"}</strong> ({latestAi.model_version || "best.pt"})
                                        </div>
                                        <div style={{ fontSize: "12px", color: "#94a3b8" }}>
                                            Detection Confidence:{" "}
                                            <strong style={{ color: isLowConfidence ? "#fbbf24" : latestAi.confidence_score ? "#4ade80" : "#94a3b8" }}>
                                                {latestAi.confidence_score !== null && latestAi.confidence_score !== undefined
                                                    ? `${(Number(latestAi.confidence_score) * 100).toFixed(1)}%`
                                                    : "N/A (No visual bbox)"}
                                            </strong>
                                        </div>
                                    </div>

                                    {/* Detected Objects & Bounding Boxes List */}
                                    <div>
                                        <div style={{ fontSize: "12px", fontWeight: 700, color: "#cbd5e1", marginBottom: "8px" }}>
                                            Detected Objects & Bounding Boxes ({Array.isArray(latestAi.detected_objects) ? latestAi.detected_objects.length : 0}):
                                        </div>
                                        {Array.isArray(latestAi.detected_objects) && latestAi.detected_objects.length > 0 ? (
                                            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                                                {latestAi.detected_objects.map((det, idx) => (
                                                    <div
                                                        key={idx}
                                                        style={{
                                                             display: "flex",
                                                             alignItems: "center",
                                                             gap: "6px",
                                                             padding: "6px 12px",
                                                             borderRadius: "6px",
                                                             background: det.is_low_confidence ? "rgba(245, 158, 11, 0.12)" : "rgba(56, 189, 248, 0.12)",
                                                             border: `1px solid ${det.is_low_confidence ? "rgba(245, 158, 11, 0.35)" : "rgba(56, 189, 248, 0.3)"}`,
                                                             color: det.is_low_confidence ? "#fbbf24" : "#38bdf8",
                                                             fontSize: "12px",
                                                        }}
                                                    >
                                                        <strong style={{ textTransform: "capitalize" }}>
                                                            {det.label || det.class_name || det.display}
                                                        </strong>
                                                        <span style={{ color: "#94a3b8" }}>
                                                            ({(Number(det.confidence) * 100).toFixed(1)}%)
                                                        </span>
                                                        {det.bbox && (
                                                            <span style={{ fontSize: "10.5px", color: "#64748b", fontFamily: "monospace" }}>
                                                                [{det.bbox.map((c) => Math.round(c)).join(", ")}]
                                                            </span>
                                                        )}
                                                        <button
                                                            type="button"
                                                            onClick={() => handleOpenFpModal(det.label || det.class_name)}
                                                            title="Flag this detection as false positive"
                                                            style={{
                                                                background: "transparent",
                                                                border: "none",
                                                                color: "#f87171",
                                                                cursor: "pointer",
                                                                padding: "0 2px",
                                                                display: "flex",
                                                                alignItems: "center",
                                                                marginLeft: "4px",
                                                            }}
                                                        >
                                                            <Flag size={11} />
                                                        </button>
                                                    </div>
                                                ))}
                                            </div>
                                        ) : (
                                            <div style={{ fontSize: "12.5px", color: "#94a3b8", background: "rgba(8,14,26,0.5)", padding: "10px 14px", borderRadius: "6px" }}>
                                                No visual civic hazard bounding boxes detected above confidence threshold ({latestAi.analysis_metadata?.vision_status || "NO_DETECTION"}).
                                            </div>
                                        )}
                                    </div>

                                    {/* Existing False Positive Feedback Records */}
                                    {falsePositiveFeedback.length > 0 && (
                                        <div style={{ padding: "10px 14px", background: "rgba(239, 68, 68, 0.08)", border: "1px solid rgba(239, 68, 68, 0.25)", borderRadius: "8px" }}>
                                            <div style={{ fontSize: "12px", fontWeight: 700, color: "#f87171", marginBottom: "6px", display: "flex", alignItems: "center", gap: "6px" }}>
                                                <Flag size={14} />
                                                <span>Authority False-Positive Feedback ({falsePositiveFeedback.length}):</span>
                                            </div>
                                            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                                                {falsePositiveFeedback.map((fp, i) => (
                                                    <div key={i} style={{ fontSize: "12px", color: "#cbd5e1" }}>
                                                        <strong style={{ color: "#fca5a5" }}>{fp.class_name}:</strong> {fp.reason}
                                                        <span style={{ color: "#64748b", marginLeft: "6px", fontSize: "11px" }}>
                                                            ({fp.officer_email || "Officer"} &bull; {new Date(fp.created_at).toLocaleDateString()})
                                                        </span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Annotated vs Original Image */}
                                    <div className="evidence-photos-grid">
                                        <div className="photo-card">
                                            <div className="photo-card-header">Citizen Input Photo</div>
                                            <img src={reportPhotoUrl} alt="Citizen report" />
                                        </div>
                                        <div className="photo-card">
                                            <div className="photo-card-header">YOLOv8 Annotated Overlay</div>
                                            {annotatedPhotoUrl ? (
                                                <img src={annotatedPhotoUrl} alt="YOLOv8 annotated detection" />
                                            ) : (
                                                <div style={{ height: "220px", display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b", fontSize: "12.5px", padding: "16px", textAlign: "center" }}>
                                                    Annotated image generated when YOLOv8 detects bounding boxes.
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <div style={{ padding: "20px", textAlign: "center", color: "#94a3b8", fontSize: "13px" }}>
                                    Awaiting initial AI execution.
                                </div>
                            )}
                        </div>

                        {/* ========================================================
                            SECTION C: GEMINI CIVIC INTELLIGENCE
                        ======================================================== */}
                        <div className="auth-card section-card" style={{ borderColor: evidenceConsistency === "INCONSISTENT" ? "rgba(239, 68, 68, 0.45)" : "rgba(168, 85, 247, 0.35)" }}>
                            <div className="section-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                    <div className="section-tag-badge gemini-badge">SECTION C</div>
                                    <h3 className="section-title">GEMINI CIVIC INTELLIGENCE</h3>
                                </div>
                                {latestAi && (
                                    <span
                                        style={{
                                            padding: "3px 10px",
                                            borderRadius: "6px",
                                            fontSize: "11px",
                                            fontWeight: 800,
                                            background: evidenceConsistency === "CONSISTENT" ? "rgba(34, 197, 94, 0.2)" : evidenceConsistency === "INCONSISTENT" ? "rgba(239, 68, 68, 0.2)" : "rgba(234, 179, 8, 0.2)",
                                            color: evidenceConsistency === "CONSISTENT" ? "#4ade80" : evidenceConsistency === "INCONSISTENT" ? "#f87171" : "#facc15",
                                            border: `1px solid ${evidenceConsistency === "CONSISTENT" ? "#22c55e" : evidenceConsistency === "INCONSISTENT" ? "#ef4444" : "#eab308"}`,
                                        }}
                                    >
                                        Evidence: {evidenceConsistency}
                                    </span>
                                )}
                            </div>

                            {latestAi ? (
                                <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                                    {/* Human Verification Warning Alert */}
                                    {requiresHumanReview && (
                                        <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "10px 14px", background: "rgba(239, 68, 68, 0.12)", border: "1px solid rgba(239, 68, 68, 0.35)", borderRadius: "8px", color: "#f87171", fontSize: "12.5px" }}>
                                            <AlertTriangle size={16} />
                                            <div>
                                                <strong>Human Verification Required:</strong> Discrepancy detected between computer vision detections and citizen testimony. Official civic issue category has been preserved without automated override.
                                            </div>
                                        </div>
                                    )}

                                    {/* Official vs AI Comparison */}
                                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px" }}>
                                        <div style={{ background: "rgba(15, 23, 42, 0.7)", padding: "12px 14px", borderRadius: "8px", border: "1px solid rgba(148, 163, 184, 0.16)" }}>
                                            <div style={{ fontSize: "11px", fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", marginBottom: "8px" }}>
                                                Current Official Record
                                            </div>
                                            <div style={{ fontSize: "12.5px", color: "#e2e8f0", display: "flex", flexDirection: "column", gap: "5px" }}>
                                                <div><strong>Category:</strong> {issue.category}</div>
                                                <div><strong>Severity:</strong> {issue.severity}</div>
                                                <div><strong>Priority:</strong> {issue.priority}</div>
                                                <div><strong>Department:</strong> {issue.department_name || "Unassigned"}</div>
                                            </div>
                                        </div>

                                        <div style={{ background: "rgba(168, 85, 247, 0.08)", padding: "12px 14px", borderRadius: "8px", border: "1px solid rgba(168, 85, 247, 0.28)" }}>
                                            <div style={{ fontSize: "11px", fontWeight: 700, color: "#c084fc", textTransform: "uppercase", marginBottom: "8px" }}>
                                                AI Recommended Values
                                            </div>
                                            <div style={{ fontSize: "12.5px", color: "#e2e8f0", display: "flex", flexDirection: "column", gap: "5px" }}>
                                                <div><strong>Suggested Category:</strong> {latestAi.predicted_category || "UNCERTAIN"}</div>
                                                <div><strong>Suggested Severity:</strong> {latestAi.suggested_severity || "MEDIUM"}</div>
                                                <div><strong>Suggested Priority:</strong> {latestAi.suggested_priority || "NORMAL"}</div>
                                                <div>
                                                    <strong>Suggested Department:</strong>{" "}
                                                    {latestAi.suggested_department_name
                                                        ? `${latestAi.suggested_department_name} (${latestAi.suggested_department_code || ""})`
                                                        : "Manual Dispatch Required"}
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Safety Observations / Concerns */}
                                    {Array.isArray(safetyConcerns) && safetyConcerns.length > 0 && (
                                        <div style={{ padding: "12px 14px", background: "rgba(239, 68, 68, 0.08)", border: "1px solid rgba(239, 68, 68, 0.25)", borderRadius: "8px" }}>
                                            <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "#f87171", fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>
                                                <ShieldAlert size={15} />
                                                <span>Safety Hazard Observations (Gemini Intelligence):</span>
                                            </div>
                                            <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "12.5px", color: "#fca5a5" }}>
                                                {safetyConcerns.map((concern, idx) => (
                                                    <li key={idx} style={{ marginBottom: "3px" }}>{concern}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}

                                    {/* Full Engineering Reasoning */}
                                    <div style={{ background: "rgba(8,14,26,0.65)", padding: "12px 14px", borderRadius: "8px", border: "1px solid rgba(148,163,184,0.14)" }}>
                                        <div style={{ fontSize: "12px", fontWeight: 700, color: "#c084fc", marginBottom: "6px" }}>
                                            Explainable AI Reasoning & Heuristic Breakdown
                                        </div>
                                        <p style={{ margin: 0, fontSize: "13px", lineHeight: "1.55", color: "#cbd5e1" }}>
                                            {latestAi.explanation || "No automated explanation available."}
                                        </p>
                                    </div>
                                </div>
                            ) : (
                                <div style={{ padding: "20px", textAlign: "center", color: "#94a3b8", fontSize: "13px" }}>
                                    Awaiting initial AI execution.
                                </div>
                            )}
                        </div>

                        {/* ========================================================
                            SECTION D: DUPLICATE DETECTION
                        ======================================================== */}
                        <div className="auth-card section-card" style={{ borderColor: getDuplicateBadgeColor(overallDuplicateClass).border }}>
                            <div className="section-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                    <div className="section-tag-badge dup-badge">SECTION D</div>
                                    <h3 className="section-title">DUPLICATE & PROXIMITY DETECTION</h3>
                                </div>
                                <span
                                    style={{
                                        padding: "3px 10px",
                                        borderRadius: "6px",
                                        fontSize: "11px",
                                        fontWeight: 800,
                                        background: getDuplicateBadgeColor(overallDuplicateClass).bg,
                                        color: getDuplicateBadgeColor(overallDuplicateClass).text,
                                        border: `1px solid ${getDuplicateBadgeColor(overallDuplicateClass).border}`,
                                    }}
                                >
                                    {overallDuplicateClass}
                                </span>
                            </div>

                            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                                {/* Existing Duplicate Association Banner if present */}
                                {duplicateLink && (
                                    <div style={{ padding: "10px 14px", background: "rgba(59, 130, 246, 0.12)", border: "1px solid rgba(59, 130, 246, 0.35)", borderRadius: "8px", color: "#93c5fd", fontSize: "12.5px" }}>
                                        <strong>Duplicate Relationship Active:</strong> Linked to primary{" "}
                                        <Link to={`/authority/issues/${duplicateLink.primary_issue_id}`} style={{ color: "#38bdf8", fontWeight: 700 }}>
                                            Issue #{duplicateLink.primary_issue_id}
                                        </Link>{" "}
                                        (Action: {duplicateLink.action}) by {duplicateLink.officer_email || "Officer"} on {new Date(duplicateLink.linked_at).toLocaleString()}.
                                        {duplicateLink.notes && <div style={{ marginTop: "4px", fontSize: "12px", color: "#cbd5e1" }}>Note: {duplicateLink.notes}</div>}
                                    </div>
                                )}

                                <div style={{ fontSize: "12px", fontWeight: 700, color: "#cbd5e1" }}>
                                    Nearby Matching Civic Reports within 500m Radius ({similarIssues.length}):
                                </div>

                                {similarIssues.length === 0 ? (
                                    <div style={{ fontSize: "12.5px", color: "#94a3b8", background: "rgba(8,14,26,0.5)", padding: "12px 14px", borderRadius: "8px" }}>
                                        No duplicate or corroborating civic reports detected within geographic proximity radius.
                                    </div>
                                ) : (
                                    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                                        {similarIssues.map((sim) => {
                                            const simScore = sim.duplicate_score !== undefined ? sim.duplicate_score : Math.round(Number(sim.similarity_score) * 100);
                                            const simClass = sim.classification || (simScore >= 90 ? "EXACT_REPLAY" : simScore >= 70 ? "HIGH_CONFIDENCE_DUPLICATE" : simScore >= 40 ? "POSSIBLE_DUPLICATE" : "UNIQUE_REPORT");
                                            const badgeColors = getDuplicateBadgeColor(simClass);
                                            return (
                                                <div
                                                    key={sim.issue_id}
                                                    style={{
                                                        display: "flex",
                                                        flexDirection: "column",
                                                        gap: "8px",
                                                        padding: "12px 14px",
                                                        borderRadius: "8px",
                                                        background: "rgba(15, 23, 42, 0.65)",
                                                        border: `1px solid ${badgeColors.border}44`,
                                                        fontSize: "12.5px",
                                                    }}
                                                >
                                                    <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "10px" }}>
                                                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                                            <strong style={{ color: "#fff", fontSize: "13px" }}>Issue #{sim.issue_id}: {sim.title}</strong>
                                                            <span
                                                                style={{
                                                                    padding: "2px 8px",
                                                                    borderRadius: "4px",
                                                                    fontSize: "10.5px",
                                                                    fontWeight: 800,
                                                                    background: badgeColors.bg,
                                                                    color: badgeColors.text,
                                                                    border: `1px solid ${badgeColors.border}`,
                                                                }}
                                                            >
                                                                {simClass} ({simScore}%)
                                                            </span>
                                                        </div>
                                                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                                                            <Link
                                                                to={`/authority/issues/${sim.issue_id}`}
                                                                style={{ display: "flex", alignItems: "center", gap: "4px", color: "#38bdf8", textDecoration: "none", fontWeight: 600, fontSize: "12px", padding: "4px 8px", borderRadius: "5px", background: "rgba(56, 189, 248, 0.12)" }}
                                                            >
                                                                <span>View</span>
                                                                <ExternalLink size={12} />
                                                            </Link>
                                                            <button
                                                                type="button"
                                                                onClick={() => handleOpenDupModal(sim.issue_id, "LINK")}
                                                                style={{
                                                                    display: "flex",
                                                                    alignItems: "center",
                                                                    gap: "4px",
                                                                    padding: "4px 8px",
                                                                    borderRadius: "5px",
                                                                    background: "rgba(59, 130, 246, 0.15)",
                                                                    border: "1px solid rgba(59, 130, 246, 0.35)",
                                                                    color: "#60a5fa",
                                                                    fontSize: "11.5px",
                                                                    fontWeight: 600,
                                                                    cursor: "pointer",
                                                                }}
                                                            >
                                                                <Layers size={12} />
                                                                <span>Link</span>
                                                            </button>
                                                            <button
                                                                type="button"
                                                                onClick={() => handleOpenDupModal(sim.issue_id, "MERGE")}
                                                                style={{
                                                                    display: "flex",
                                                                    alignItems: "center",
                                                                    gap: "4px",
                                                                    padding: "4px 8px",
                                                                    borderRadius: "5px",
                                                                    background: "rgba(168, 85, 247, 0.15)",
                                                                    border: "1px solid rgba(168, 85, 247, 0.35)",
                                                                    color: "#c084fc",
                                                                    fontSize: "11.5px",
                                                                    fontWeight: 600,
                                                                    cursor: "pointer",
                                                                }}
                                                            >
                                                                <GitMerge size={12} />
                                                                <span>Merge</span>
                                                            </button>
                                                        </div>
                                                    </div>

                                                    {/* Signal Breakdown Tiles */}
                                                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))", gap: "6px", fontSize: "11.5px", color: "#94a3b8" }}>
                                                        <div style={{ background: "rgba(8,14,26,0.6)", padding: "4px 8px", borderRadius: "4px" }}>
                                                            GPS: <strong style={{ color: "#e2e8f0" }}>{sim.distance_meters}m</strong>
                                                        </div>
                                                        <div style={{ background: "rgba(8,14,26,0.6)", padding: "4px 8px", borderRadius: "4px" }}>
                                                            Image Match: <strong style={{ color: (sim.image_similarity_percent || 0) >= 80 ? "#4ade80" : "#e2e8f0" }}>
                                                                {sim.image_similarity_percent !== undefined ? `${sim.image_similarity_percent}%` : sim.image_similarity ? `${Math.round(sim.image_similarity * 100)}%` : "0%"}
                                                            </strong>
                                                        </div>
                                                        <div style={{ background: "rgba(8,14,26,0.6)", padding: "4px 8px", borderRadius: "4px" }}>
                                                            Text Match: <strong style={{ color: "#e2e8f0" }}>
                                                                {sim.description_similarity_percent !== undefined ? `${sim.description_similarity_percent}%` : sim.description_similarity ? `${Math.round(sim.description_similarity * 100)}%` : "0%"}
                                                            </strong>
                                                        </div>
                                                        <div style={{ background: "rgba(8,14,26,0.6)", padding: "4px 8px", borderRadius: "4px" }}>
                                                            Category: <strong style={{ color: sim.category_match ? "#4ade80" : "#94a3b8" }}>
                                                                {sim.category_match ? "Match" : sim.category}
                                                            </strong>
                                                        </div>
                                                    </div>

                                                    {Array.isArray(sim.match_reasons) && sim.match_reasons.length > 0 && (
                                                        <div style={{ fontSize: "11px", color: "#64748b" }}>
                                                            Reasons: {sim.match_reasons.join(" • ")}
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* ========================================================
                            SECTION E: SUSPICIOUS SUBMISSION RISK ASSESSMENT
                        ======================================================== */}
                        <div className="auth-card section-card" style={{ borderColor: getRiskColor(suspiciousAssessment?.risk_level || "NORMAL").border }}>
                            <div className="section-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                    <div className="section-tag-badge suspicious-badge">SECTION E</div>
                                    <h3 className="section-title">SUSPICIOUS SUBMISSION RISK ASSESSMENT</h3>
                                </div>
                                <span
                                    style={{
                                        padding: "3px 10px",
                                        borderRadius: "6px",
                                        fontSize: "11px",
                                        fontWeight: 800,
                                        background: getRiskColor(suspiciousAssessment?.risk_level || "NORMAL").bg,
                                        color: getRiskColor(suspiciousAssessment?.risk_level || "NORMAL").text,
                                        border: `1px solid ${getRiskColor(suspiciousAssessment?.risk_level || "NORMAL").border}`,
                                    }}
                                >
                                    Risk: {suspiciousAssessment?.risk_level || "NORMAL"}
                                </span>
                            </div>

                            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                                {/* Risk score meter */}
                                <div style={{ background: "rgba(8,14,26,0.65)", padding: "12px 14px", borderRadius: "8px", border: "1px solid rgba(148,163,184,0.12)" }}>
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                                        <span style={{ fontSize: "12.5px", color: "#cbd5e1" }}>
                                            Anomaly Risk Metric: <strong style={{ color: getRiskColor(suspiciousAssessment?.risk_level || "NORMAL").text }}>{suspiciousAssessment?.risk_score || 0} / 100</strong>
                                        </span>
                                        <span style={{ fontSize: "11.5px", color: "#94a3b8" }}>
                                            {suspiciousAssessment?.recommendation || "Standard municipal verification."}
                                        </span>
                                    </div>
                                    <div style={{ width: "100%", height: "8px", background: "rgba(15, 23, 42, 0.8)", borderRadius: "4px", overflow: "hidden" }}>
                                        <div
                                            style={{
                                                width: `${Math.min(100, Math.max(0, suspiciousAssessment?.risk_score || 0))}%`,
                                                height: "100%",
                                                background: `linear-gradient(90deg, #22c55e 0%, #eab308 35%, #f97316 65%, #ef4444 100%)`,
                                                transition: "width 0.4s ease",
                                            }}
                                        />
                                    </div>
                                </div>

                                {/* Identified Risk Factors */}
                                <div>
                                    <div style={{ fontSize: "12px", fontWeight: 700, color: "#cbd5e1", marginBottom: "6px" }}>
                                        Risk Evaluation Factors:
                                    </div>
                                    {Array.isArray(suspiciousAssessment?.risk_factors) && suspiciousAssessment.risk_factors.length > 0 ? (
                                        <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "12.5px", color: "#fb923c" }}>
                                            {suspiciousAssessment.risk_factors.map((factor, idx) => (
                                                <li key={idx} style={{ marginBottom: "3px" }}>{factor}</li>
                                            ))}
                                        </ul>
                                    ) : (
                                        <div style={{ fontSize: "12px", color: "#94a3b8", background: "rgba(8,14,26,0.5)", padding: "8px 12px", borderRadius: "6px" }}>
                                            ✓ No suspicious manipulation indicators detected. Evidence conforms to authentic citizen submission patterns.
                                        </div>
                                    )}
                                </div>

                                {/* Advisory Governance Notice */}
                                <div style={{ fontSize: "11.5px", color: "#64748b", fontStyle: "italic", borderTop: "1px solid rgba(148,163,184,0.1)", paddingTop: "8px" }}>
                                    Notice: AI risk scores are advisory heuristics for municipal inspection and do not prove misconduct. Official report decisions strictly require authorized officer evaluation.
                                </div>
                            </div>
                        </div>

                        {/* ========================================================
                            SECTION F: SEVERITY & PRIORITY RECOMMENDATION
                        ======================================================== */}
                        <div className="auth-card section-card" style={{ borderColor: "rgba(245, 158, 11, 0.35)" }}>
                            <div className="section-header">
                                <div className="section-tag-badge priority-badge">SECTION F</div>
                                <h3 className="section-title">SEVERITY & PRIORITY RECOMMENDATION</h3>
                            </div>

                            {priorityScore !== null ? (
                                <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                                    {/* Score Meter & Level */}
                                    <div style={{ background: "rgba(8,14,26,0.65)", padding: "14px", borderRadius: "8px", border: "1px solid rgba(148,163,184,0.14)" }}>
                                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                                            <span style={{ fontSize: "13px", fontWeight: 700, color: "#cbd5e1" }}>
                                                Composite Risk Score:{" "}
                                                <strong style={{ color: getPriorityColor(priorityScore), fontSize: "16px" }}>
                                                    {priorityScore} / 100
                                                </strong>
                                            </span>
                                            <span
                                                style={{
                                                    padding: "3px 10px",
                                                    borderRadius: "6px",
                                                    fontSize: "11px",
                                                    fontWeight: 800,
                                                    letterSpacing: "0.05em",
                                                    background: `${getPriorityColor(priorityScore)}22`,
                                                    color: getPriorityColor(priorityScore),
                                                    border: `1px solid ${getPriorityColor(priorityScore)}55`,
                                                }}
                                            >
                                                {latestAi?.suggested_priority || issue.priority || "NORMAL"}
                                            </span>
                                        </div>

                                        {/* Progress Bar Meter */}
                                        <div style={{ width: "100%", height: "10px", background: "rgba(15, 23, 42, 0.8)", borderRadius: "5px", overflow: "hidden", border: "1px solid rgba(148, 163, 184, 0.15)" }}>
                                            <div
                                                style={{
                                                    width: `${Math.min(100, Math.max(0, priorityScore))}%`,
                                                    height: "100%",
                                                    background: `linear-gradient(90deg, #22c55e 0%, #eab308 50%, #f97316 75%, #ef4444 100%)`,
                                                    transition: "width 0.5s ease-in-out",
                                                }}
                                            />
                                        </div>
                                    </div>

                                    {/* Factor Breakdown */}
                                    {priorityBreakdown && (
                                        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "8px" }}>
                                            <div className="factor-tile">
                                                <span className="factor-label">Base Hazard</span>
                                                <span className="factor-value">+{priorityBreakdown.category_base || 0} pts</span>
                                            </div>
                                            <div className="factor-tile">
                                                <span className="factor-label">Safety Evidence</span>
                                                <span className="factor-value">+{priorityBreakdown.safety_risk_evidence || 0} pts</span>
                                            </div>
                                            <div className="factor-tile">
                                                <span className="factor-label">Location</span>
                                                <span className="factor-value">+{priorityBreakdown.location_sensitivity || 0} pts</span>
                                            </div>
                                            <div className="factor-tile">
                                                <span className="factor-label">Report Volume</span>
                                                <span className="factor-value">+{priorityBreakdown.community_report_volume || 0} pts</span>
                                            </div>
                                            <div className="factor-tile">
                                                <span className="factor-label">Age Factor</span>
                                                <span className="factor-value">+{priorityBreakdown.report_age_factor || 0} pts</span>
                                            </div>
                                        </div>
                                    )}

                                    {/* Factor Explanations */}
                                    {scoringFactors.length > 0 && (
                                        <div style={{ fontSize: "12px", color: "#94a3b8" }}>
                                            <strong>Contributing Factors:</strong> {scoringFactors.join("; ")}.
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div style={{ padding: "20px", textAlign: "center", color: "#94a3b8", fontSize: "13px" }}>
                                    Priority score calculated upon AI pipeline execution.
                                </div>
                            )}
                        </div>

                    </div>

                    {/* RIGHT COLUMN: SECTIONS G, H, I & CITIZEN PROFILE */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                        {/* ========================================================
                            SECTION G: DEPARTMENT RECOMMENDATION & DISPATCH
                        ======================================================== */}
                        <div className="auth-card section-card" style={{ borderColor: "rgba(14, 165, 233, 0.35)" }}>
                            <div className="section-header">
                                <div className="section-tag-badge dept-badge">SECTION G</div>
                                <h3 className="section-title">DEPARTMENT RECOMMENDATION & DISPATCH</h3>
                            </div>

                            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                                {latestAi?.suggested_department_name && (
                                    <div style={{ background: "rgba(14, 165, 233, 0.08)", border: "1px solid rgba(14, 165, 233, 0.25)", borderRadius: "8px", padding: "10px 12px", fontSize: "12.5px" }}>
                                        <span style={{ color: "#94a3b8" }}>AI Recommended Department: </span>
                                        <strong style={{ color: "#38bdf8" }}>{latestAi.suggested_department_name}</strong>
                                        {latestAi.suggested_department_code && (
                                            <span style={{ color: "#64748b", marginLeft: "6px" }}>({latestAi.suggested_department_code})</span>
                                        )}
                                    </div>
                                )}

                                <div>
                                    <label style={{ fontSize: "12px", color: "#94a3b8" }}>Official Assigned Department</label>
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
                                    <label style={{ fontSize: "12px", color: "#94a3b8" }}>Assigned Field Officer</label>
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
                                        marginTop: "4px",
                                    }}
                                >
                                    {assigning ? "Updating Assignment..." : "Update Official Assignment"}
                                </button>
                            </div>
                        </div>

                        {/* ========================================================
                            SECTION H: AI PROCESSING & REVIEW CONTROLS
                        ======================================================== */}
                        <div className="auth-card section-card" style={{ borderColor: "rgba(34, 197, 94, 0.4)" }}>
                            <div className="section-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                    <div className="section-tag-badge review-badge">SECTION H</div>
                                    <h3 className="section-title">AI PROCESSING & REVIEW CONTROLS</h3>
                                </div>
                                {latestAi && (
                                    <button
                                        type="button"
                                        onClick={handleOpenHistory}
                                        style={{
                                            display: "flex",
                                            alignItems: "center",
                                            gap: "5px",
                                            padding: "4px 8px",
                                            borderRadius: "5px",
                                            background: "rgba(148, 163, 184, 0.15)",
                                            border: "1px solid rgba(148, 163, 184, 0.25)",
                                            color: "#cbd5e1",
                                            fontSize: "11px",
                                            fontWeight: 600,
                                            cursor: "pointer",
                                        }}
                                    >
                                        <History size={12} />
                                        <span>History</span>
                                    </button>
                                )}
                            </div>

                            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                                <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "10px", background: "rgba(8,14,26,0.65)", padding: "10px 14px", borderRadius: "8px" }}>
                                    <div style={{ fontSize: "12.5px", color: "#cbd5e1" }}>
                                        Current Review Decision:{" "}
                                        <strong style={{
                                            color: latestAi?.review_status === "APPROVED"
                                                ? "#4ade80"
                                                : latestAi?.review_status === "REJECTED"
                                                    ? "#f87171"
                                                    : "#fbbf24"
                                        }}>
                                            {latestAi?.review_status || "PENDING"}
                                        </strong>
                                    </div>
                                    {latestAi?.reviewed_by_name && (
                                        <div style={{ fontSize: "11.5px", color: "#94a3b8" }}>
                                            Reviewed by <strong>{latestAi.reviewed_by_name}</strong> on {new Date(latestAi.reviewed_at).toLocaleString()}
                                        </div>
                                    )}
                                </div>

                                {latestAi?.review_comment && (
                                    <div style={{ padding: "10px 12px", background: "rgba(148,163,184,0.08)", borderRadius: "6px", fontSize: "12.5px", color: "#cbd5e1", borderLeft: "3px solid #38bdf8" }}>
                                        <strong>Reviewer Note:</strong> {latestAi.review_comment}
                                    </div>
                                )}

                                {/* Proposed Changes Delta Table */}
                                {latestAi && (
                                    <div style={{ background: "rgba(15, 23, 42, 0.75)", border: "1px solid rgba(148, 163, 184, 0.15)", borderRadius: "8px", padding: "12px 14px", overflowX: "auto" }}>
                                        <div style={{ fontSize: "11px", fontWeight: 700, color: "#38bdf8", textTransform: "uppercase", marginBottom: "8px" }}>
                                            Proposed Official Changes (Approval Impact Delta)
                                        </div>
                                        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
                                            <thead>
                                                <tr style={{ color: "#94a3b8", borderBottom: "1px solid rgba(148,163,184,0.15)", textAlign: "left" }}>
                                                    <th style={{ padding: "6px 8px" }}>Field</th>
                                                    <th style={{ padding: "6px 8px" }}>Current Official</th>
                                                    <th style={{ padding: "6px 8px" }}>AI Recommendation</th>
                                                    <th style={{ padding: "6px 8px" }}>Status</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr style={{ borderBottom: "1px solid rgba(148,163,184,0.08)" }}>
                                                    <td style={{ padding: "6px 8px", color: "#94a3b8" }}>Category</td>
                                                    <td style={{ padding: "6px 8px", color: "#e2e8f0" }}>{issue.category}</td>
                                                    <td style={{ padding: "6px 8px", color: "#38bdf8", fontWeight: 600 }}>{latestAi.predicted_category || "Unchanged"}</td>
                                                    <td style={{ padding: "6px 8px" }}>
                                                        {issue.category === latestAi.predicted_category ? (
                                                            <span style={{ color: "#4ade80", fontSize: "11px" }}>✓ In Sync</span>
                                                        ) : (
                                                            <span style={{ color: "#fbbf24", fontSize: "11px" }}>Delta Update</span>
                                                        )}
                                                    </td>
                                                </tr>
                                                <tr style={{ borderBottom: "1px solid rgba(148,163,184,0.08)" }}>
                                                    <td style={{ padding: "6px 8px", color: "#94a3b8" }}>Severity</td>
                                                    <td style={{ padding: "6px 8px", color: "#e2e8f0" }}>{issue.severity}</td>
                                                    <td style={{ padding: "6px 8px", color: "#c084fc", fontWeight: 600 }}>{latestAi.suggested_severity || "Unchanged"}</td>
                                                    <td style={{ padding: "6px 8px" }}>
                                                        {issue.severity === latestAi.suggested_severity ? (
                                                            <span style={{ color: "#4ade80", fontSize: "11px" }}>✓ In Sync</span>
                                                        ) : (
                                                            <span style={{ color: "#fbbf24", fontSize: "11px" }}>Delta Update</span>
                                                        )}
                                                    </td>
                                                </tr>
                                                <tr style={{ borderBottom: "1px solid rgba(148,163,184,0.08)" }}>
                                                    <td style={{ padding: "6px 8px", color: "#94a3b8" }}>Priority</td>
                                                    <td style={{ padding: "6px 8px", color: "#e2e8f0" }}>{issue.priority}</td>
                                                    <td style={{ padding: "6px 8px", color: "#fbbf24", fontWeight: 600 }}>{latestAi.suggested_priority || "Unchanged"}</td>
                                                    <td style={{ padding: "6px 8px" }}>
                                                        {issue.priority === latestAi.suggested_priority ? (
                                                            <span style={{ color: "#4ade80", fontSize: "11px" }}>✓ In Sync</span>
                                                        ) : (
                                                            <span style={{ color: "#fbbf24", fontSize: "11px" }}>Delta Update</span>
                                                        )}
                                                    </td>
                                                </tr>
                                                <tr>
                                                    <td style={{ padding: "6px 8px", color: "#94a3b8" }}>Department</td>
                                                    <td style={{ padding: "6px 8px", color: "#e2e8f0" }}>{issue.department_name || "Unassigned"}</td>
                                                    <td style={{ padding: "6px 8px", color: "#60a5fa", fontWeight: 600 }}>{latestAi.suggested_department_name || "Unassigned"}</td>
                                                    <td style={{ padding: "6px 8px" }}>
                                                        {issue.department_name === latestAi.suggested_department_name ? (
                                                            <span style={{ color: "#4ade80", fontSize: "11px" }}>✓ In Sync</span>
                                                        ) : (
                                                            <span style={{ color: "#fbbf24", fontSize: "11px" }}>Dispatch Update</span>
                                                        )}
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                )}

                                {aiActionMsg && (
                                    <div style={{ padding: "10px 12px", background: "rgba(34,197,94,0.12)", color: "#4ade80", borderRadius: "6px", fontSize: "12.5px" }}>
                                        {aiActionMsg}
                                    </div>
                                )}
                                {aiActionError && (
                                    <div style={{ padding: "10px 12px", background: "rgba(239,68,68,0.12)", color: "#f87171", borderRadius: "6px", fontSize: "12.5px" }}>
                                        {aiActionError}
                                    </div>
                                )}

                                <div>
                                    <label style={{ fontSize: "12px", color: "#cbd5e1", display: "block", marginBottom: "6px" }}>
                                        Authority Review Note / Rejection Reason (Mandatory for rejection):
                                    </label>
                                    <input
                                        type="text"
                                        className="issue-search-input"
                                        placeholder="Enter officer notes or reason for modifying/rejecting AI recommendation..."
                                        value={aiReviewComment}
                                        onChange={(e) => setAiReviewComment(e.target.value)}
                                        style={{ width: "100%" }}
                                    />
                                </div>

                                <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
                                    <button
                                        type="button"
                                        onClick={handleApproveAi}
                                        disabled={aiLoading}
                                        style={{
                                            display: "flex",
                                            alignItems: "center",
                                            gap: "6px",
                                            padding: "9px 16px",
                                            borderRadius: "7px",
                                            background: "rgba(34, 197, 94, 0.18)",
                                            color: "#4ade80",
                                            border: "1px solid rgba(34, 197, 94, 0.4)",
                                            fontWeight: 600,
                                            fontSize: "12.5px",
                                            cursor: aiLoading ? "not-allowed" : "pointer",
                                        }}
                                    >
                                        <ThumbsUp size={14} />
                                        <span>Approve Recommendation</span>
                                    </button>

                                    <button
                                        type="button"
                                        onClick={handleRejectAi}
                                        disabled={aiLoading}
                                        style={{
                                            display: "flex",
                                            alignItems: "center",
                                            gap: "6px",
                                            padding: "9px 16px",
                                            borderRadius: "7px",
                                            background: "rgba(239, 68, 68, 0.16)",
                                            color: "#f87171",
                                            border: "1px solid rgba(239, 68, 68, 0.35)",
                                            fontWeight: 600,
                                            fontSize: "12.5px",
                                            cursor: aiLoading ? "not-allowed" : "pointer",
                                        }}
                                    >
                                        <ThumbsDown size={14} />
                                        <span>Reject Recommendation</span>
                                    </button>

                                    <button
                                        type="button"
                                        onClick={() => handleRunAiAnalysis(true)}
                                        disabled={aiLoading}
                                        style={{
                                            display: "flex",
                                            alignItems: "center",
                                            gap: "6px",
                                            padding: "9px 16px",
                                            borderRadius: "7px",
                                            background: "rgba(56, 189, 248, 0.14)",
                                            color: "#38bdf8",
                                            border: "1px solid rgba(56, 189, 248, 0.35)",
                                            fontSize: "12.5px",
                                            fontWeight: 600,
                                            cursor: aiLoading ? "not-allowed" : "pointer",
                                        }}
                                    >
                                        <RefreshCw size={14} className={aiLoading ? "animate-spin" : ""} />
                                        <span>Reanalyse Image</span>
                                    </button>

                                    <button
                                        type="button"
                                        onClick={() => handleRunAiAnalysis(false)}
                                        disabled={aiLoading}
                                        style={{
                                            display: "flex",
                                            alignItems: "center",
                                            gap: "6px",
                                            padding: "9px 16px",
                                            borderRadius: "7px",
                                            background: "linear-gradient(135deg, #0284c7, #0369a1)",
                                            color: "#ffffff",
                                            border: "none",
                                            fontSize: "12.5px",
                                            fontWeight: 600,
                                            cursor: aiLoading ? "not-allowed" : "pointer",
                                        }}
                                    >
                                        <Cpu size={14} />
                                        <span>{aiLoading ? "Running Pipeline..." : "Run AI Pipeline"}</span>
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* ========================================================
                            SECTION I: AUTHORITY DECISION & STATUS AUDIT HISTORY
                        ======================================================== */}
                        <div className="auth-card section-card" style={{ borderColor: "rgba(236, 72, 153, 0.35)" }}>
                            <div className="section-header">
                                <div className="section-tag-badge decision-badge">SECTION I</div>
                                <h3 className="section-title">AUTHORITY DECISION & STATUS AUDIT HISTORY</h3>
                            </div>

                            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                                {/* STATUS LIFECYCLE TRANSITION CONTROLS */}
                                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                                    <div style={{ fontSize: "12px", fontWeight: 700, color: "#cbd5e1" }}>
                                        Official Lifecycle Status Transitions:
                                    </div>
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
                                        <div style={{ marginTop: "6px", paddingTop: "10px", borderTop: "1px solid rgba(148,163,184,0.1)" }}>
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

                                {/* CHRONOLOGICAL STATUS AUDIT TIMELINE */}
                                <div style={{ borderTop: "1px solid rgba(148,163,184,0.12)", paddingTop: "14px" }}>
                                    <div style={{ fontSize: "12px", fontWeight: 700, color: "#cbd5e1", marginBottom: "14px" }}>
                                        Chronological Status Audit Trail ({issue.status_history?.length || 0}):
                                    </div>
                                    <div className="timeline-container">
                                        {issue.status_history?.map((hist) => (
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

                {/* AI ANALYSIS HISTORY MODAL */}
                {showHistoryModal && (
                    <div className="modal-overlay">
                        <div className="modal-content" style={{ maxWidth: "680px", maxHeight: "85vh", overflowY: "auto" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                    <History size={20} color="#38bdf8" />
                                    <h3 className="modal-title" style={{ margin: 0 }}>
                                        AI Analysis Audit History (Issue #{issue.id})
                                    </h3>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => setShowHistoryModal(false)}
                                    style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer" }}
                                >
                                    <X size={18} />
                                </button>
                            </div>

                            {historyLoading ? (
                                <div style={{ padding: "40px", textAlign: "center", color: "#64748b" }}>
                                    <Loader2 size={28} className="animate-spin" style={{ margin: "0 auto 8px" }} />
                                    <p>Loading analysis history records...</p>
                                </div>
                            ) : historyList.length === 0 ? (
                                <div style={{ padding: "20px", textAlign: "center", color: "#94a3b8", fontSize: "13px" }}>
                                    No historical analysis runs found for this issue.
                                </div>
                            ) : (
                                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                                    {historyList.map((hist, idx) => (
                                        <div
                                            key={hist.id || idx}
                                            style={{
                                                padding: "12px 14px",
                                                background: "rgba(15, 23, 42, 0.75)",
                                                border: "1px solid rgba(148, 163, 184, 0.15)",
                                                borderRadius: "8px",
                                                fontSize: "12.5px",
                                                color: "#cbd5e1",
                                            }}
                                        >
                                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                                                <strong style={{ color: "#fff" }}>
                                                    Run #{hist.id} &bull; {hist.model_name}
                                                </strong>
                                                <span style={{
                                                    fontSize: "11px",
                                                    fontWeight: 700,
                                                    padding: "2px 8px",
                                                    borderRadius: "4px",
                                                    background: hist.review_status === "APPROVED"
                                                        ? "rgba(34,197,94,0.15)"
                                                        : hist.review_status === "REJECTED"
                                                            ? "rgba(239,68,68,0.15)"
                                                            : "rgba(245,158,11,0.15)",
                                                    color: hist.review_status === "APPROVED"
                                                        ? "#4ade80"
                                                        : hist.review_status === "REJECTED"
                                                            ? "#f87171"
                                                            : "#fbbf24",
                                                }}>
                                                    {hist.review_status || "PENDING"}
                                                </span>
                                            </div>
                                            <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", color: "#94a3b8", fontSize: "11.5px", marginBottom: "6px" }}>
                                                <span>Category: <strong style={{ color: "#38bdf8" }}>{hist.predicted_category || "N/A"}</strong></span>
                                                <span>Severity: <strong style={{ color: "#e2e8f0" }}>{hist.suggested_severity || "N/A"}</strong></span>
                                                <span>Priority: <strong style={{ color: "#e2e8f0" }}>{hist.suggested_priority || "N/A"}</strong></span>
                                                <span>Timestamp: {new Date(hist.created_at).toLocaleString()}</span>
                                            </div>
                                            {hist.review_comment && (
                                                <div style={{ fontSize: "11.5px", color: "#94a3b8", fontStyle: "italic", marginTop: "4px" }}>
                                                    Officer note: "{hist.review_comment}" (by {hist.reviewed_by_name || "Officer"})
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}

                            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "16px" }}>
                                <button
                                    type="button"
                                    className="pagination-btn"
                                    onClick={() => setShowHistoryModal(false)}
                                >
                                    Close History
                                </button>
                            </div>
                        </div>
                    </div>
                )}

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

                {/* FALSE POSITIVE FEEDBACK MODAL */}
                {showFpModal && (
                    <div className="modal-overlay">
                        <div className="modal-content" style={{ maxWidth: "500px" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                    <Flag size={18} color="#f87171" />
                                    <h3 className="modal-title" style={{ margin: 0, color: "#f87171" }}>
                                        Flag False-Positive Detection
                                    </h3>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => setShowFpModal(false)}
                                    style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer" }}
                                >
                                    <X size={18} />
                                </button>
                            </div>

                            <p style={{ fontSize: "12.5px", color: "#94a3b8", margin: "0 0 14px" }}>
                                Record municipal officer feedback on incorrect or spurious YOLO detections to improve future training datasets.
                            </p>

                            {fpError && (
                                <div style={{ padding: "10px", background: "rgba(239,68,68,0.12)", color: "#f87171", borderRadius: "6px", marginBottom: "14px", fontSize: "12px" }}>
                                    {fpError}
                                </div>
                            )}

                            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                                <div>
                                    <label style={{ fontSize: "12px", color: "#cbd5e1", display: "block", marginBottom: "6px" }}>
                                        Detected Class to Flag
                                    </label>
                                    <input
                                        type="text"
                                        className="issue-search-input"
                                        placeholder="e.g. fallen_tree, water_leakage"
                                        value={fpClass}
                                        onChange={(e) => setFpClass(e.target.value)}
                                        required
                                    />
                                </div>

                                <div>
                                    <label style={{ fontSize: "12px", color: "#cbd5e1", display: "block", marginBottom: "6px" }}>
                                        Officer Justification / Observed Reality (Mandatory)
                                    </label>
                                    <textarea
                                        rows={3}
                                        className="issue-search-input"
                                        placeholder="Explain why this detection is incorrect (e.g. background shrub mistaken for fallen tree, shadows mistaken for water)..."
                                        value={fpReason}
                                        onChange={(e) => setFpReason(e.target.value)}
                                        required
                                    />
                                </div>

                                <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "6px" }}>
                                    <button
                                        type="button"
                                        className="pagination-btn"
                                        onClick={() => setShowFpModal(false)}
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="button"
                                        onClick={handleSubmitFp}
                                        disabled={fpSubmitting}
                                        style={{
                                            padding: "8px 16px",
                                            borderRadius: "6px",
                                            background: "rgba(239, 68, 68, 0.2)",
                                            color: "#f87171",
                                            border: "1px solid rgba(239, 68, 68, 0.4)",
                                            fontWeight: 700,
                                            cursor: fpSubmitting ? "not-allowed" : "pointer",
                                        }}
                                    >
                                        {fpSubmitting ? "Submitting..." : "Submit False-Positive Feedback"}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* DUPLICATE LINK / MERGE MODAL */}
                {showDupModal && (
                    <div className="modal-overlay">
                        <div className="modal-content" style={{ maxWidth: "520px" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                    <GitMerge size={18} color="#38bdf8" />
                                    <h3 className="modal-title" style={{ margin: 0, color: "#38bdf8" }}>
                                        {dupAction === "MERGE" ? "Merge Duplicate Civic Report" : "Link Duplicate Civic Report"}
                                    </h3>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => setShowDupModal(false)}
                                    style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer" }}
                                >
                                    <X size={18} />
                                </button>
                            </div>

                            <p style={{ fontSize: "12.5px", color: "#94a3b8", margin: "0 0 14px" }}>
                                {dupAction === "MERGE"
                                    ? `Merging Issue #${issue.id} into primary Issue #${dupTargetId} will mark this report as Resolved/Duplicate while preserving citizen evidence and audit history.`
                                    : `Linking Issue #${issue.id} as a corroborating report to primary Issue #${dupTargetId}.`}
                            </p>

                            {dupError && (
                                <div style={{ padding: "10px", background: "rgba(239,68,68,0.12)", color: "#f87171", borderRadius: "6px", marginBottom: "14px", fontSize: "12px" }}>
                                    {dupError}
                                </div>
                            )}

                            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                                <div>
                                    <label style={{ fontSize: "12px", color: "#cbd5e1", display: "block", marginBottom: "6px" }}>
                                        Action Mode
                                    </label>
                                    <div style={{ display: "flex", gap: "16px" }}>
                                        <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12.5px", color: "#cbd5e1", cursor: "pointer" }}>
                                            <input
                                                type="radio"
                                                name="dupActionMode"
                                                value="LINK"
                                                checked={dupAction === "LINK"}
                                                onChange={() => setDupAction("LINK")}
                                            />
                                            <span>Associate as Related/Duplicate</span>
                                        </label>
                                        <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12.5px", color: "#cbd5e1", cursor: "pointer" }}>
                                            <input
                                                type="radio"
                                                name="dupActionMode"
                                                value="MERGE"
                                                checked={dupAction === "MERGE"}
                                                onChange={() => setDupAction("MERGE")}
                                            />
                                            <span>Merge & Resolve (Close this report)</span>
                                        </label>
                                    </div>
                                </div>

                                <div>
                                    <label style={{ fontSize: "12px", color: "#cbd5e1", display: "block", marginBottom: "6px" }}>
                                        Primary Issue Target ID
                                    </label>
                                    <input
                                        type="number"
                                        className="issue-search-input"
                                        value={dupTargetId || ""}
                                        onChange={(e) => setDupTargetId(parseInt(e.target.value, 10))}
                                        required
                                    />
                                </div>

                                <div>
                                    <label style={{ fontSize: "12px", color: "#cbd5e1", display: "block", marginBottom: "6px" }}>
                                        Officer Action Notes (Optional)
                                    </label>
                                    <textarea
                                        rows={3}
                                        className="issue-search-input"
                                        placeholder="Add notes explaining duplicate relationship or dispatch coordination..."
                                        value={dupNotes}
                                        onChange={(e) => setDupNotes(e.target.value)}
                                    />
                                </div>

                                <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "6px" }}>
                                    <button
                                        type="button"
                                        className="pagination-btn"
                                        onClick={() => setShowDupModal(false)}
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="button"
                                        onClick={handleSubmitDuplicateAction}
                                        disabled={dupSubmitting}
                                        style={{
                                            padding: "8px 18px",
                                            borderRadius: "6px",
                                            background: dupAction === "MERGE" ? "rgba(168, 85, 247, 0.25)" : "rgba(56, 189, 248, 0.25)",
                                            color: dupAction === "MERGE" ? "#c084fc" : "#38bdf8",
                                            border: `1px solid ${dupAction === "MERGE" ? "rgba(168, 85, 247, 0.45)" : "rgba(56, 189, 248, 0.45)"}`,
                                            fontWeight: 700,
                                            cursor: dupSubmitting ? "not-allowed" : "pointer",
                                        }}
                                    >
                                        {dupSubmitting ? "Processing..." : dupAction === "MERGE" ? "Confirm Merge" : "Confirm Link"}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </AuthorityLayout>
    );
}
