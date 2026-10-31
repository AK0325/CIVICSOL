import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { AlertTriangle, Clock, Layers, Loader2, MapPin, RefreshCw, ShieldAlert, Sparkles } from "lucide-react";
import AuthorityLayout from "../../components/AuthorityLayout";
import {
    getAuthorityDepartments,
    getAuthorityMapIssues,
} from "../../services/authorityApi";

const DEFAULT_CENTER = [23.0225, 72.5714];
const DEFAULT_ZOOM = 12;

const STATUS_COLORS = {
    Reported: "#fbbf24",
    "Under Review": "#38bdf8",
    Assigned: "#c084fc",
    "In Progress": "#60a5fa",
    Resolved: "#4ade80",
    Rejected: "#f87171",
    Reopened: "#fb923c",
};

function MapAutoFitter({ issues }) {
    const map = useMap();

    useEffect(() => {
        if (!issues || issues.length === 0) {
            map.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
            return;
        }

        const validCoords = issues
            .filter((i) => Number.isFinite(Number(i.latitude)) && Number.isFinite(Number(i.longitude)))
            .map((i) => [Number(i.latitude), Number(i.longitude)]);

        if (validCoords.length > 0) {
            const bounds = L.latLngBounds(validCoords);
            map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
        }
    }, [issues, map]);

    return null;
}

export default function AuthorityMap() {
    const [issues, setIssues] = useState([]);
    const [departments, setDepartments] = useState([]);
    const [selectedDept, setSelectedDept] = useState("");
    const [selectedStatus, setSelectedStatus] = useState("");
    const [selectedAiFilter, setSelectedAiFilter] = useState("");
    const [overdueOnly, setOverdueOnly] = useState(false);
    const [loading, setLoading] = useState(true);

    const fetchMapData = async () => {
        try {
            setLoading(true);
            const [mapData, depts] = await Promise.all([
                getAuthorityMapIssues({
                    department_id: selectedDept ? Number(selectedDept) : undefined,
                    status: selectedStatus || undefined,
                    ai_status:
                        selectedAiFilter === "analyzed"
                            ? "ANALYZED"
                            : selectedAiFilter === "unanalyzed"
                                ? "NOT_ANALYZED"
                                : undefined,
                    overdue_only: overdueOnly ? true : undefined,
                }),
                getAuthorityDepartments().catch(() => []),
            ]);
            setIssues(mapData.issues || []);
            setDepartments(depts || []);
        } catch (err) {
            console.error("Map fetch error:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMapData();
    }, [selectedDept, selectedStatus, selectedAiFilter, overdueOnly]);

    const overdueCount = issues.filter((i) => i.is_overdue).length;

    return (
        <AuthorityLayout title="Municipal GIS Live Command Map">
            <div style={{ display: "flex", flexDirection: "column", gap: "16px", height: "calc(100vh - 128px)" }}>
                {/* MAP CONTROLS BAR */}
                <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", alignItems: "center", background: "#0f172a", padding: "12px 18px", borderRadius: "12px", border: "1px solid rgba(148,163,184,0.12)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "#38bdf8", fontSize: "13px", fontWeight: 700 }}>
                        <Layers size={16} />
                        <span>Layers & Filters:</span>
                    </div>

                    <select
                        className="issue-select"
                        value={selectedDept}
                        onChange={(e) => setSelectedDept(e.target.value)}
                    >
                        <option value="">All Departments</option>
                        {departments.map((d) => (
                            <option key={d.id} value={d.id}>{d.name}</option>
                        ))}
                    </select>

                    <select
                        className="issue-select"
                        value={selectedStatus}
                        onChange={(e) => setSelectedStatus(e.target.value)}
                    >
                        <option value="">All Statuses</option>
                        {Object.keys(STATUS_COLORS).map((s) => (
                            <option key={s} value={s}>{s}</option>
                        ))}
                    </select>

                    <select
                        className="issue-select"
                        value={selectedAiFilter}
                        onChange={(e) => setSelectedAiFilter(e.target.value)}
                    >
                        <option value="">All AI States</option>
                        <option value="analyzed">AI Analyzed Only</option>
                        <option value="unanalyzed">Not Yet Analyzed</option>
                    </select>

                    {/* OVERDUE TOGGLE BUTTON */}
                    <button
                        type="button"
                        onClick={() => setOverdueOnly(!overdueOnly)}
                        style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "6px",
                            padding: "6px 12px",
                            borderRadius: "6px",
                            border: overdueOnly ? "1px solid #ef4444" : "1px solid rgba(148,163,184,0.2)",
                            background: overdueOnly ? "rgba(239,68,68,0.2)" : "rgba(15,23,42,0.6)",
                            color: overdueOnly ? "#f87171" : "#cbd5e1",
                            fontSize: "12px",
                            fontWeight: 600,
                            cursor: "pointer",
                        }}
                    >
                        <AlertTriangle size={14} color={overdueOnly ? "#ef4444" : "#94a3b8"} />
                        <span>Overdue SLA Only {overdueCount > 0 ? `(${overdueCount})` : ""}</span>
                    </button>

                    <div style={{ marginLeft: "auto", fontSize: "12.5px", color: "#94a3b8" }}>
                        Showing <strong>{issues.length}</strong> geocoded incidents
                    </div>
                </div>

                {/* LEAFLET MAP CONTAINER */}
                <div style={{ flex: 1, borderRadius: "14px", overflow: "hidden", border: "1px solid rgba(148,163,184,0.15)", position: "relative" }}>
                    {loading && (
                        <div style={{ position: "absolute", top: 12, right: 12, zIndex: 1000, background: "rgba(15,23,42,0.85)", padding: "6px 14px", borderRadius: "20px", display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#38bdf8" }}>
                            <Loader2 size={14} className="animate-spin" />
                            <span>Syncing coordinates...</span>
                        </div>
                    )}

                    <MapContainer
                        center={DEFAULT_CENTER}
                        zoom={DEFAULT_ZOOM}
                        style={{ width: "100%", height: "100%", background: "#0b1324" }}
                    >
                        <TileLayer
                            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        />
                        <MapAutoFitter issues={issues} />

                        {issues.map((issue) => {
                            const markerColor = STATUS_COLORS[issue.status] || "#38bdf8";
                            const isOverdue = Boolean(issue.is_overdue);

                            return (
                                <CircleMarker
                                    key={issue.id}
                                    center={[issue.latitude, issue.longitude]}
                                    radius={isOverdue ? 10 : 8}
                                    pathOptions={{
                                        color: isOverdue ? "#ef4444" : markerColor,
                                        fillColor: markerColor,
                                        fillOpacity: 0.85,
                                        weight: isOverdue ? 3 : 2,
                                        dashArray: isOverdue ? "4 3" : undefined,
                                    }}
                                >
                                    <Popup>
                                        <div style={{ padding: "6px", color: "#0f172a", minWidth: "230px" }}>
                                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                                                <span style={{ fontSize: "10px", fontWeight: 700, color: "#0284c7", textTransform: "uppercase" }}>
                                                    {issue.category} &bull; #{issue.id}
                                                </span>
                                                {isOverdue && (
                                                    <span style={{ fontSize: "9.5px", fontWeight: 800, padding: "1px 5px", borderRadius: "3px", background: "rgba(239,68,68,0.15)", color: "#dc2626", border: "1px solid rgba(239,68,68,0.3)" }}>
                                                        SLA BREACHED
                                                    </span>
                                                )}
                                            </div>

                                            <h4 style={{ margin: "2px 0 4px", fontSize: "13px", fontWeight: 700 }}>
                                                {issue.title}
                                            </h4>
                                            <p style={{ margin: "2px 0 6px", fontSize: "11px", color: "#475569" }}>
                                                {issue.location}
                                            </p>
                                            <div style={{ fontSize: "11px", marginBottom: "6px" }}>
                                                <strong>Status:</strong> {issue.status} &bull; <strong>Dept:</strong> {issue.department_name}
                                            </div>

                                            {/* SLA INFORMATION */}
                                            {isOverdue && (
                                                <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", padding: "4px 8px", borderRadius: "5px", fontSize: "10.5px", color: "#b91c1c", marginBottom: "6px" }}>
                                                    <strong>SLA Alert:</strong> Overdue by {Math.abs(Math.round(issue.hours_remaining || 0))}h past municipal deadline.
                                                </div>
                                            )}

                                            {/* AI INTELLIGENCE SUMMARY ON MAP */}
                                            <div style={{ background: "#f1f5f9", padding: "6px 8px", borderRadius: "6px", fontSize: "10.5px", marginBottom: "8px", border: "1px solid #cbd5e1" }}>
                                                <div style={{ fontWeight: 700, color: issue.ai_analysis_status !== "NOT_ANALYZED" ? "#0369a1" : "#64748b", marginBottom: "2px" }}>
                                                    AI Status: {issue.ai_analysis_status}
                                                </div>
                                                {issue.ai_analysis_status !== "NOT_ANALYZED" && (
                                                    <>
                                                        <div>
                                                            <strong>Predicted:</strong> {issue.ai_predicted_category || "UNCERTAIN"}
                                                        </div>
                                                        <div>
                                                            <strong>Suggested:</strong> {issue.ai_suggested_severity || "-"} / {issue.ai_suggested_priority || "-"}
                                                        </div>
                                                        {issue.ai_suggested_department && (
                                                            <div>
                                                                <strong>Suggested Dept:</strong> {issue.ai_suggested_department}
                                                            </div>
                                                        )}
                                                        <div>
                                                            <strong>Nearby Similar Reports:</strong> {issue.nearby_similar_count || 0}
                                                        </div>
                                                    </>
                                                )}
                                            </div>

                                            <Link
                                                to={`/authority/issues/${issue.id}`}
                                                style={{
                                                    display: "inline-block",
                                                    padding: "4px 10px",
                                                    background: "#0284c7",
                                                    color: "#ffffff",
                                                    borderRadius: "4px",
                                                    textDecoration: "none",
                                                    fontSize: "11px",
                                                    fontWeight: 600,
                                                }}
                                            >
                                                Open Issue Dossier &rarr;
                                            </Link>
                                        </div>
                                    </Popup>
                                </CircleMarker>
                            );
                        })}
                    </MapContainer>
                </div>
            </div>
        </AuthorityLayout>
    );
}
