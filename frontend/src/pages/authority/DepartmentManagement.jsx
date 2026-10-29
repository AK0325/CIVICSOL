import { useEffect, useState } from "react";
import { Building2, Loader2, Plus, RefreshCw, X } from "lucide-react";
import AuthorityLayout from "../../components/AuthorityLayout";
import {
    createAuthorityDepartment,
    getAuthorityDepartments,
    updateAuthorityDepartment,
} from "../../services/authorityApi";

export default function DepartmentManagement() {
    const [departments, setDepartments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [showCreateModal, setShowCreateModal] = useState(false);

    // Form state
    const [name, setName] = useState("");
    const [code, setCode] = useState("");
    const [description, setDescription] = useState("");
    const [contactEmail, setContactEmail] = useState("");
    const [contactPhone, setContactPhone] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [formError, setFormError] = useState("");

    const fetchDepts = async () => {
        try {
            setLoading(true);
            const data = await getAuthorityDepartments();
            setDepartments(data || []);
        } catch (err) {
            setError("Failed to load departments.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDepts();
    }, []);

    const handleCreateSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        setFormError("");
        try {
            await createAuthorityDepartment({
                name: name.trim(),
                code: code.trim().toUpperCase(),
                description: description.trim() || undefined,
                contact_email: contactEmail.trim() || undefined,
                contact_phone: contactPhone.trim() || undefined,
            });
            setShowCreateModal(false);
            setName("");
            setCode("");
            setDescription("");
            setContactEmail("");
            setContactPhone("");
            fetchDepts();
        } catch (err) {
            setFormError(err.response?.data?.detail || "Failed to create department.");
        } finally {
            setSubmitting(false);
        }
    };

    const handleToggleActive = async (dept) => {
        try {
            await updateAuthorityDepartment(dept.id, {
                is_active: !dept.is_active,
            });
            fetchDepts();
        } catch (err) {
            alert(err.response?.data?.detail || "Action failed.");
        }
    };

    return (
        <AuthorityLayout title="Municipal Departments Administration">
            <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                        <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#fff", margin: "0 0 6px" }}>
                            Municipal Departments
                        </h1>
                        <p style={{ fontSize: "14px", color: "#94a3b8", margin: 0 }}>
                            Manage administrative departments, dispatch boundaries, and contact coordinators
                        </p>
                    </div>

                    <button
                        type="button"
                        onClick={() => setShowCreateModal(true)}
                        style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "8px",
                            padding: "9px 18px",
                            borderRadius: "8px",
                            background: "linear-gradient(135deg, #0284c7, #0369a1)",
                            color: "#fff",
                            border: "none",
                            cursor: "pointer",
                            fontSize: "13.5px",
                            fontWeight: 700,
                        }}
                    >
                        <Plus size={16} />
                        <span>Add Department</span>
                    </button>
                </div>

                {error && (
                    <div style={{ padding: "12px", background: "rgba(239,68,68,0.12)", color: "#f87171", borderRadius: "8px" }}>
                        {error}
                    </div>
                )}

                <div className="auth-card" style={{ padding: 0, overflow: "hidden" }}>
                    {loading ? (
                        <div style={{ padding: "60px", textAlign: "center", color: "#64748b" }}>
                            <Loader2 size={32} className="animate-spin" style={{ margin: "0 auto 10px" }} />
                            <p>Loading departments...</p>
                        </div>
                    ) : (
                        <table className="auth-table">
                            <thead>
                                <tr>
                                    <th>Department Name</th>
                                    <th>Code</th>
                                    <th>Active Officers</th>
                                    <th>Open Issues</th>
                                    <th>Contact Information</th>
                                    <th>Status</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {departments.map((d) => (
                                    <tr key={d.id}>
                                        <td>
                                            <div style={{ fontWeight: 700, color: "#f8fafc" }}>{d.name}</div>
                                            <div style={{ fontSize: "11.5px", color: "#64748b" }}>{d.description}</div>
                                        </td>
                                        <td>
                                            <code style={{ background: "rgba(148,163,184,0.1)", padding: "2px 6px", borderRadius: "4px", color: "#38bdf8" }}>
                                                {d.code}
                                            </code>
                                        </td>
                                        <td>{d.active_officers_count} officers</td>
                                        <td>
                                            <span style={{ color: d.open_issues_count > 0 ? "#fbbf24" : "#4ade80", fontWeight: 700 }}>
                                                {d.open_issues_count} open
                                            </span>
                                        </td>
                                        <td>
                                            <div style={{ fontSize: "12px" }}>{d.contact_email || "No email"}</div>
                                            <div style={{ fontSize: "11px", color: "#64748b" }}>{d.contact_phone || "No phone"}</div>
                                        </td>
                                        <td>
                                            <span style={{
                                                padding: "3px 8px",
                                                borderRadius: "4px",
                                                fontSize: "11px",
                                                fontWeight: 700,
                                                background: d.is_active ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)",
                                                color: d.is_active ? "#4ade80" : "#f87171",
                                            }}>
                                                {d.is_active ? "ACTIVE" : "INACTIVE"}
                                            </span>
                                        </td>
                                        <td>
                                            <button
                                                type="button"
                                                onClick={() => handleToggleActive(d)}
                                                style={{
                                                    padding: "4px 10px",
                                                    borderRadius: "6px",
                                                    background: "rgba(148,163,184,0.1)",
                                                    color: "#cbd5e1",
                                                    border: "1px solid rgba(148,163,184,0.2)",
                                                    cursor: "pointer",
                                                    fontSize: "12px",
                                                }}
                                            >
                                                {d.is_active ? "Deactivate" : "Activate"}
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>

                {/* CREATE MODAL */}
                {showCreateModal && (
                    <div className="modal-overlay">
                        <div className="modal-content">
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                                <h3 className="modal-title" style={{ margin: 0 }}>Create Municipal Department</h3>
                                <button type="button" onClick={() => setShowCreateModal(false)} style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer" }}>
                                    <X size={18} />
                                </button>
                            </div>

                            {formError && (
                                <div style={{ padding: "10px", background: "rgba(239,68,68,0.12)", color: "#f87171", borderRadius: "6px", marginBottom: "14px", fontSize: "12.5px" }}>
                                    {formError}
                                </div>
                            )}

                            <form onSubmit={handleCreateSubmit} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                                <div>
                                    <label style={{ fontSize: "12.5px", color: "#cbd5e1" }}>Department Name</label>
                                    <input
                                        type="text"
                                        className="issue-search-input"
                                        placeholder="e.g. Health & Sanitation"
                                        value={name}
                                        onChange={(e) => setName(e.target.value)}
                                        required
                                    />
                                </div>

                                <div>
                                    <label style={{ fontSize: "12.5px", color: "#cbd5e1" }}>Unique Department Code</label>
                                    <input
                                        type="text"
                                        className="issue-search-input"
                                        placeholder="e.g. HEALTH_SANITATION"
                                        value={code}
                                        onChange={(e) => setCode(e.target.value)}
                                        required
                                    />
                                </div>

                                <div>
                                    <label style={{ fontSize: "12.5px", color: "#cbd5e1" }}>Description</label>
                                    <textarea
                                        rows={2}
                                        className="issue-search-input"
                                        placeholder="Brief description of municipal duties..."
                                        value={description}
                                        onChange={(e) => setDescription(e.target.value)}
                                    />
                                </div>

                                <div>
                                    <label style={{ fontSize: "12.5px", color: "#cbd5e1" }}>Contact Email</label>
                                    <input
                                        type="email"
                                        className="issue-search-input"
                                        placeholder="dept@civicsol.gov.in"
                                        value={contactEmail}
                                        onChange={(e) => setContactEmail(e.target.value)}
                                    />
                                </div>

                                <div>
                                    <label style={{ fontSize: "12.5px", color: "#cbd5e1" }}>Contact Phone</label>
                                    <input
                                        type="text"
                                        className="issue-search-input"
                                        placeholder="+91 79 2555 ..."
                                        value={contactPhone}
                                        onChange={(e) => setContactPhone(e.target.value)}
                                    />
                                </div>

                                <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
                                    <button type="button" className="pagination-btn" onClick={() => setShowCreateModal(false)}>
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={submitting}
                                        style={{ padding: "8px 18px", borderRadius: "6px", background: "#0284c7", color: "#fff", border: "none", cursor: "pointer", fontWeight: 600 }}
                                    >
                                        {submitting ? "Creating..." : "Save Department"}
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
