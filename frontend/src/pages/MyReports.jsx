import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
    ArrowLeft,
    ArrowRight,
    CalendarDays,
    Camera,
    CheckCircle2,
    Clock3,
    FileText,
    MapPin,
    RefreshCw,
    ShieldCheck,
    TriangleAlert,
    History,
    X,
    Send,
    Sparkles,
} from "lucide-react";

import {
    getMyIssues,
    getIssueTimeline,
    requestIssueReopen,
} from "../services/api";

import "./MyReports.css";


const MyReports = () => {

    const navigate = useNavigate();

    const [issues, setIssues] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const [filter, setFilter] = useState("All");

    // Timeline Modal State
    const [selectedTimeline, setSelectedTimeline] = useState(null);
    const [timelineLoading, setTimelineLoading] = useState(false);
    const [showTimelineModal, setShowTimelineModal] = useState(false);
    const [reopenReason, setReopenReason] = useState("");
    const [reopenSubmitting, setReopenSubmitting] = useState(false);
    const [reopenError, setReopenError] = useState("");
    const [reopenSuccess, setReopenSuccess] = useState("");

    const openTimeline = async (issueId) => {
        setShowTimelineModal(true);
        setTimelineLoading(true);
        setReopenError("");
        setReopenSuccess("");
        setReopenReason("");
        try {
            const data = await getIssueTimeline(issueId);
            setSelectedTimeline(data);
        } catch (err) {
            console.error("Failed to load timeline:", err);
            setReopenError("Unable to fetch report timeline.");
        } finally {
            setTimelineLoading(false);
        }
    };

    const handleReopenSubmit = async () => {
        if (!selectedTimeline || !reopenReason.trim() || reopenReason.trim().length < 5) {
            setReopenError("Please provide a meaningful reason (at least 5 characters).");
            return;
        }

        setReopenSubmitting(true);
        setReopenError("");
        setReopenSuccess("");
        try {
            const res = await requestIssueReopen(selectedTimeline.id, reopenReason.trim());
            setReopenSuccess(res.message || "Reopen request submitted successfully.");
            setReopenReason("");
            // Refresh modal dossier
            const refreshed = await getIssueTimeline(selectedTimeline.id);
            setSelectedTimeline(refreshed);
            // Refresh list in background
            loadReports();
        } catch (err) {
            console.error("Reopen request failed:", err);
            setReopenError(err.response?.data?.detail || "Failed to submit reopen request.");
        } finally {
            setReopenSubmitting(false);
        }
    };


    // =====================================================
    // LOAD MY REPORTS
    // =====================================================

    const loadReports = async () => {

        try {

            setLoading(true);
            setError("");

            const data = await getMyIssues();

            setIssues(
                Array.isArray(data)
                    ? data
                    : []
            );

        } catch (err) {

            console.error(
                "My reports error:",
                err
            );

            if (
                err.response?.status === 401 ||
                err.response?.status === 403
            ) {

                localStorage.removeItem(
                    "civicsol_access_token"
                );

                localStorage.removeItem(
                    "civicsol_citizen"
                );

                navigate("/signin");

                return;
            }

            setError(
                "Unable to load your reports."
            );

        } finally {

            setLoading(false);

        }

    };


    useEffect(() => {

        loadReports();

    }, []);


    // =====================================================
    // FILTERS
    // =====================================================

    const filteredIssues = useMemo(() => {

        if (filter === "All") {
            return issues;
        }

        return issues.filter(
            (issue) =>
                String(issue.status || "")
                    .toLowerCase()
                === filter.toLowerCase()
        );

    }, [issues, filter]);


    // =====================================================
    // STATUS COUNTS
    // =====================================================

    const reportedCount = issues.filter(
        (issue) =>
            String(issue.status || "")
                .toLowerCase()
            === "reported"
    ).length;


    const verifiedCount = issues.filter(
        (issue) =>
            String(issue.status || "")
                .toLowerCase()
            === "verified"
    ).length;


    const resolvedCount = issues.filter(
        (issue) =>
            String(issue.status || "")
                .toLowerCase()
            === "resolved"
    ).length;


    // =====================================================
    // DATE
    // =====================================================

    const formatDate = (value) => {

        if (!value) {
            return "Date unavailable";
        }

        const date = new Date(value);

        if (Number.isNaN(date.getTime())) {
            return "Date unavailable";
        }

        return date.toLocaleDateString(
            "en-IN",
            {
                day: "numeric",
                month: "short",
                year: "numeric",
            }
        );

    };


    // =====================================================
    // IMAGE URL
    // =====================================================

    const getImageUrl = (path) => {

        if (!path) {
            return null;
        }

        if (path.startsWith("http")) {
            return path;
        }

        return `http://127.0.0.1:8000/${path}`;
    };


    // =====================================================
    // STATUS CLASS
    // =====================================================

    const getStatusClass = (status) => {

        return String(status || "Reported")
            .toLowerCase()
            .replace(/\s+/g, "-");

    };


    // =====================================================
    // LOADING
    // =====================================================

    if (loading) {

        return (

            <main className="my-reports-page">

                <div className="my-reports-loading">

                    <RefreshCw size={28} />

                    <p>
                        Loading your reports...
                    </p>

                </div>

            </main>

        );

    }


    // =====================================================
    // ERROR
    // =====================================================

    if (error) {

        return (

            <main className="my-reports-page">

                <div className="my-reports-error">

                    <ShieldCheck size={32} />

                    <h2>
                        Unable to load reports
                    </h2>

                    <p>
                        {error}
                    </p>

                    <button
                        onClick={loadReports}
                    >
                        <RefreshCw size={15} />
                        Try Again
                    </button>

                </div>

            </main>

        );

    }


    return (

        <main className="my-reports-page">


            {/* =================================================
                HEADER
            ================================================= */}

            <section className="my-reports-header">

                <div>

                    <Link
                        to="/citizen-dashboard"
                        className="reports-back-link"
                    >

                        <ArrowLeft size={16} />

                        Dashboard

                    </Link>


                    <p className="reports-eyebrow">
                        CITIZEN ACTIVITY
                    </p>


                    <h1>
                        My Reports
                    </h1>


                    <p className="reports-subtitle">

                        Track the civic issues you have
                        reported and follow their progress.

                    </p>

                </div>


                <Link
                    to="/report"
                    className="new-report-button"
                >

                    <Camera size={17} />

                    Report New Issue

                </Link>

            </section>


            {/* =================================================
                STATS
            ================================================= */}

            <section className="reports-stats">


                <div className="reports-stat">

                    <FileText size={19} />

                    <div>

                        <span>
                            Total Reports
                        </span>

                        <strong>
                            {issues.length}
                        </strong>

                    </div>

                </div>


                <div className="reports-stat">

                    <Clock3 size={19} />

                    <div>

                        <span>
                            Under Review
                        </span>

                        <strong>
                            {reportedCount}
                        </strong>

                    </div>

                </div>


                <div className="reports-stat">

                    <ShieldCheck size={19} />

                    <div>

                        <span>
                            Verified
                        </span>

                        <strong>
                            {verifiedCount}
                        </strong>

                    </div>

                </div>


                <div className="reports-stat">

                    <CheckCircle2 size={19} />

                    <div>

                        <span>
                            Resolved
                        </span>

                        <strong>
                            {resolvedCount}
                        </strong>

                    </div>

                </div>

            </section>


            {/* =================================================
                FILTER BAR
            ================================================= */}

            <section className="reports-toolbar">

                <div>

                    <span>
                        SHOW
                    </span>

                    <button
                        className={
                            filter === "All"
                                ? "active"
                                : ""
                        }
                        onClick={() =>
                            setFilter("All")
                        }
                    >
                        All
                    </button>

                    <button
                        className={
                            filter === "Reported"
                                ? "active"
                                : ""
                        }
                        onClick={() =>
                            setFilter("Reported")
                        }
                    >
                        Reported
                    </button>

                    <button
                        className={
                            filter === "Verified"
                                ? "active"
                                : ""
                        }
                        onClick={() =>
                            setFilter("Verified")
                        }
                    >
                        Verified
                    </button>

                    <button
                        className={
                            filter === "Resolved"
                                ? "active"
                                : ""
                        }
                        onClick={() =>
                            setFilter("Resolved")
                        }
                    >
                        Resolved
                    </button>

                </div>


                <span className="reports-count">

                    {filteredIssues.length}
                    {" "}
                    {filteredIssues.length === 1
                        ? "report"
                        : "reports"}

                </span>

            </section>


            {/* =================================================
                EMPTY STATE
            ================================================= */}

            {filteredIssues.length === 0 ? (

                <section className="reports-empty">

                    <div className="empty-report-icon">

                        <FileText size={30} />

                    </div>


                    <h2>

                        {issues.length === 0
                            ? "You haven't reported any civic issues yet."
                            : "No reports match this filter."}

                    </h2>


                    <p>

                        {issues.length === 0
                            ? "Your image and GPS-based civic reports will appear here."
                            : "Try selecting another status filter."}

                    </p>


                    {issues.length === 0 && (

                        <Link
                            to="/report"
                            className="empty-report-button"
                        >

                            Report Your First Issue

                            <ArrowRight size={16} />

                        </Link>

                    )}

                </section>

            ) : (

                /* =================================================
                   REPORT LIST
                ================================================= */

                <section className="reports-list">

                    {filteredIssues.map(
                        (issue) => {

                            const imageUrl =
                                getImageUrl(
                                    issue.image_path
                                );


                            return (

                                <article
                                    className="report-card"
                                    key={issue.id}
                                >


                                    {/* IMAGE */}

                                    <div className="report-image">

                                        {imageUrl ? (

                                            <img
                                                src={imageUrl}
                                                alt={
                                                    issue.title ||
                                                    "Civic issue"
                                                }
                                            />

                                        ) : (

                                            <div className="no-report-image">

                                                <Camera size={25} />

                                                <span>
                                                    No image
                                                </span>

                                            </div>

                                        )}

                                    </div>


                                    {/* CONTENT */}

                                    <div className="report-main">

                                        <div className="report-topline">

                                            <span className="report-id">
                                                ISSUE #
                                                {issue.id}
                                            </span>


                                            <span
                                                className={
                                                    `report-status ${getStatusClass(
                                                        issue.status
                                                    )
                                                    }`
                                                }
                                            >

                                                <span />

                                                {
                                                    issue.status ||
                                                    "Reported"
                                                }

                                            </span>

                                        </div>


                                        <h2>

                                            {
                                                issue.title ||
                                                "Civic Issue"
                                            }

                                        </h2>


                                        <p className="report-category">

                                            {issue.category ||
                                                "General"}

                                            {" • "}

                                            {issue.severity ||
                                                "Medium"}

                                        </p>


                                        {issue.description && (

                                            <p className="report-description">

                                                {issue.description}

                                            </p>

                                        )}


                                        <div className="report-meta">


                                            <div>

                                                <MapPin size={14} />

                                                <span>

                                                    {
                                                        issue.location ||
                                                        "Location unavailable"
                                                    }

                                                </span>

                                            </div>


                                            <div>

                                                <CalendarDays size={14} />

                                                <span>

                                                    {
                                                        formatDate(
                                                            issue.created_at
                                                        )
                                                    }

                                                </span>

                                            </div>

                                        </div>

                                        <div
                                            style={{
                                                marginTop: "10px",
                                                display: "inline-flex",
                                                flexWrap: "wrap",
                                                alignItems: "center",
                                                gap: "8px",
                                                padding: "5px 10px",
                                                borderRadius: "6px",
                                                background: "rgba(14, 165, 233, 0.09)",
                                                border: "1px solid rgba(56, 189, 248, 0.22)",
                                                fontSize: "11.5px",
                                                color: "#94a3b8",
                                            }}
                                        >
                                            <strong style={{ color: "#38bdf8" }}>
                                                AI Status: {issue.ai_analysis?.processing_status || "PENDING"}
                                            </strong>
                                            {issue.ai_analysis?.predicted_category && (
                                                <span>
                                                    &bull; Predicted: {issue.ai_analysis.predicted_category}
                                                </span>
                                            )}
                                            {issue.ai_analysis?.suggested_department_name && (
                                                <span>
                                                    &bull; Suggested Dept: {issue.ai_analysis.suggested_department_name}
                                                </span>
                                            )}
                                        </div>

                                    </div>


                                    {/* RIGHT SIDE */}

                                    <div className="report-side">


                                        <div className="priority-box">

                                            <span>
                                                PRIORITY
                                            </span>

                                            <strong>

                                                {
                                                    issue.priority ||
                                                    "Medium"
                                                }

                                            </strong>

                                        </div>


                                        <div className="coordinates">

                                            <span>
                                                GPS
                                            </span>

                                            <small>

                                                {
                                                    Number(
                                                        issue.latitude
                                                    ).toFixed(4)
                                                }

                                                {" , "}

                                                {
                                                    Number(
                                                        issue.longitude
                                                    ).toFixed(4)
                                                }

                                            </small>

                                        </div>

                                        <button
                                            type="button"
                                            className="timeline-btn"
                                            onClick={() => openTimeline(issue.id)}
                                        >
                                            <History size={13} />
                                            <span>View Timeline</span>
                                        </button>

                                    </div>

                                </article>

                            );

                        }
                    )}

                </section>

            )}


            {/* =================================================
                INFORMATION
            ================================================= */}

            <section className="reports-info">

                <TriangleAlert size={19} />

                <div>

                    <strong>
                        CIVICSOL evidence policy
                    </strong>

                    <p>

                        Reports require image evidence and
                        GPS location so civic authorities can
                        validate and prioritize reported issues.

                    </p>

                </div>

            </section>

            {/* =================================================
                CHRONOLOGICAL TIMELINE & REOPEN MODAL
            ================================================= */}
            {showTimelineModal && (
                <div className="modal-backdrop" onClick={() => setShowTimelineModal(false)}>
                    <div className="timeline-modal" onClick={(e) => e.stopPropagation()}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                <History size={20} color="#38bdf8" />
                                <h3 style={{ margin: 0, fontSize: "17px", color: "#ffffff" }}>
                                    Report #{selectedTimeline?.id} Timeline & Status
                                </h3>
                            </div>
                            <button
                                type="button"
                                onClick={() => setShowTimelineModal(false)}
                                style={{ background: "transparent", border: "none", color: "#94a3b8", cursor: "pointer" }}
                            >
                                <X size={20} />
                            </button>
                        </div>

                        {timelineLoading ? (
                            <div style={{ padding: "40px", textAlign: "center", color: "#94a3b8" }}>
                                Loading status history...
                            </div>
                        ) : selectedTimeline ? (
                            <div>
                                <div style={{ background: "rgba(30, 41, 59, 0.5)", padding: "14px", borderRadius: "10px", marginBottom: "16px" }}>
                                    <h4 style={{ margin: "0 0 6px", color: "#ffffff", fontSize: "15px" }}>
                                        {selectedTimeline.title}
                                    </h4>
                                    <div style={{ display: "flex", gap: "10px", fontSize: "12px", color: "#94a3b8", flexWrap: "wrap" }}>
                                        <span><strong>Category:</strong> {selectedTimeline.category}</span>
                                        <span>&bull;</span>
                                        <span><strong>Status:</strong> <span className={`status-pill status-${getStatusClass(selectedTimeline.status)}`}>{selectedTimeline.status}</span></span>
                                        <span>&bull;</span>
                                        <span><strong>Department:</strong> {selectedTimeline.department_name}</span>
                                    </div>
                                </div>

                                {/* Chronological Track */}
                                <h4 style={{ fontSize: "13px", color: "#cbd5e1", textTransform: "uppercase", letterSpacing: "0.05em", margin: "16px 0 8px" }}>
                                    Chronological Status Progression
                                </h4>

                                {(!selectedTimeline.status_timeline || selectedTimeline.status_timeline.length === 0) ? (
                                    <p style={{ color: "#94a3b8", fontSize: "13px" }}>Report registered. Initial authority dispatch pending.</p>
                                ) : (
                                    <div className="timeline-track">
                                        {selectedTimeline.status_timeline.map((step, idx) => (
                                            <div key={step.id || idx} className="timeline-item">
                                                <div className="timeline-dot" />
                                                <div className="timeline-title">
                                                    {step.from_status ? `${step.from_status} → ` : ""}{step.to_status}
                                                </div>
                                                <div className="timeline-date">
                                                    {new Date(step.created_at).toLocaleString()}
                                                </div>
                                                {step.comment && (
                                                    <div className="timeline-comment">
                                                        {step.comment}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {/* Automated AI Triage & Verification Dossier */}
                                {selectedTimeline.ai_analysis && (
                                    <div style={{ background: "rgba(14, 165, 233, 0.08)", border: "1px solid rgba(56, 189, 248, 0.25)", padding: "14px", borderRadius: "10px", margin: "16px 0" }}>
                                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px", flexWrap: "wrap", gap: "8px" }}>
                                            <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "#38bdf8", fontWeight: 700, fontSize: "13px" }}>
                                                <Sparkles size={16} />
                                                <span>AI Verification & Automated Triage</span>
                                            </div>
                                            <span style={{ fontSize: "11px", fontWeight: 700, padding: "2px 8px", borderRadius: "4px", background: selectedTimeline.ai_analysis.processing_status === "COMPLETED" ? "rgba(34,197,94,0.2)" : "rgba(245,158,11,0.2)", color: selectedTimeline.ai_analysis.processing_status === "COMPLETED" ? "#4ade80" : "#fbbf24" }}>
                                                Status: {selectedTimeline.ai_analysis.processing_status}
                                            </span>
                                        </div>
                                        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "8px", fontSize: "12px", color: "#cbd5e1" }}>
                                            <div><strong>Identified Hazard:</strong> {selectedTimeline.ai_analysis.predicted_category || "In Analysis"}</div>
                                            <div><strong>Vision Confidence:</strong> {selectedTimeline.ai_analysis.confidence_score ? `${(Number(selectedTimeline.ai_analysis.confidence_score) * 100).toFixed(1)}%` : "N/A"}</div>
                                            <div><strong>Severity:</strong> {selectedTimeline.ai_analysis.suggested_severity || "Standard"}</div>
                                            <div><strong>Dispatched Dept:</strong> {selectedTimeline.ai_analysis.suggested_department_name || selectedTimeline.department_name}</div>
                                        </div>
                                        {selectedTimeline.ai_analysis.annotated_image_path && (
                                            <div style={{ marginTop: "10px" }}>
                                                <span style={{ fontSize: "11px", color: "#94a3b8", display: "block", marginBottom: "4px" }}>Visual Detection Overlay:</span>
                                                <img
                                                    src={getImageUrl(selectedTimeline.ai_analysis.annotated_image_path)}
                                                    alt="AI Detection Overlay"
                                                    style={{ maxWidth: "100%", maxHeight: "180px", borderRadius: "6px", objectFit: "cover" }}
                                                />
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Resolution Evidence Display */}
                                {selectedTimeline.status === "Resolved" && (
                                    <div style={{ background: "rgba(34, 197, 94, 0.08)", border: "1px solid rgba(34, 197, 94, 0.2)", padding: "14px", borderRadius: "10px", margin: "16px 0" }}>
                                        <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "#4ade80", fontWeight: 700, fontSize: "13px", marginBottom: "6px" }}>
                                            <CheckCircle2 size={16} />
                                            <span>Resolution Verified (+20 Civic Credits Earned)</span>
                                        </div>
                                        {selectedTimeline.resolution_notes && (
                                            <p style={{ margin: "4px 0 10px", fontSize: "12.5px", color: "#cbd5e1" }}>
                                                <strong>Officer Notes:</strong> {selectedTimeline.resolution_notes}
                                            </p>
                                        )}
                                        {selectedTimeline.resolution_image_path && (
                                            <img
                                                src={getImageUrl(selectedTimeline.resolution_image_path)}
                                                alt="Resolution proof"
                                                style={{ maxWidth: "100%", maxHeight: "200px", borderRadius: "8px", objectFit: "cover" }}
                                            />
                                        )}
                                    </div>
                                )}

                                {/* Reopen Workflow */}
                                {(selectedTimeline.status === "Resolved" || selectedTimeline.status === "Rejected") && (
                                    <div className="reopen-box">
                                        <h4 style={{ margin: "0 0 6px", fontSize: "13px", color: "#fb923c" }}>
                                            Issue Not Resolved Satisfactorily?
                                        </h4>
                                        <p style={{ margin: "0 0 10px", fontSize: "12px", color: "#cbd5e1" }}>
                                            Citizens can submit an authorized request to reopen this report for municipal re-investigation.
                                        </p>

                                        {reopenSuccess && (
                                            <div style={{ color: "#4ade80", fontSize: "12px", marginBottom: "8px" }}>
                                                {reopenSuccess}
                                            </div>
                                        )}
                                        {reopenError && (
                                            <div style={{ color: "#f87171", fontSize: "12px", marginBottom: "8px" }}>
                                                {reopenError}
                                            </div>
                                        )}

                                        <textarea
                                            placeholder="Please describe why this issue requires reopening..."
                                            value={reopenReason}
                                            onChange={(e) => setReopenReason(e.target.value)}
                                            style={{ width: "100%", minHeight: "60px", background: "#020817", border: "1px solid rgba(148,163,184,0.2)", borderRadius: "6px", color: "#ffffff", padding: "8px", fontSize: "12.5px", resize: "vertical", boxSizing: "border-box" }}
                                        />

                                        <button
                                            type="button"
                                            className="reopen-btn"
                                            disabled={reopenSubmitting}
                                            onClick={handleReopenSubmit}
                                            style={{ marginTop: "8px" }}
                                        >
                                            {reopenSubmitting ? "Submitting..." : "Submit Reopen Request"}
                                        </button>
                                    </div>
                                )}
                            </div>
                        ) : null}
                    </div>
                </div>
            )}

        </main>

    );


};


export default MyReports;