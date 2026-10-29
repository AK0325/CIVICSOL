import { useEffect, useState } from "react";
import { Loader2, Plus, Shield, UserCheck, UserX, X } from "lucide-react";
import AuthorityLayout from "../../components/AuthorityLayout";
import {
    createAuthorityOfficer,
    getAuthorityDepartments,
    getAuthorityOfficers,
    updateAuthorityOfficer,
} from "../../services/authorityApi";

export default function OfficerManagement() {
    const [officers, setOfficers] = useState([]);
    const [departments, setDepartments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [roleFilter, setRoleFilter] = useState("");
    const [deptFilter, setDeptFilter] = useState("");
    const [showModal, setShowModal] = useState(false);

    // Form state
    const [name, setName] = useState("");
    const [mobile, setMobile] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [role, setRole] = useState("FIELD_OFFICER");
    const [departmentId, setDepartmentId] = useState("");
    const [designation, setDesignation] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [formError, setFormError] = useState("");

    const fetchData = async () => {
        try {
            setLoading(true);
            const [depts, offs] = await Promise.all([
                getAuthorityDepartments(),
                getAuthorityOfficers({
                    role: roleFilter || undefined,
                    department_id: deptFilter ? Number(deptFilter) : undefined,
                }),
            ]);
            setDepartments(depts || []);
            setOfficers(offs || []);
        } catch (err) {
            setError("Failed to load officers directory.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [roleFilter, deptFilter]);

    const handleCreateOfficer = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        setFormError("");
        try {
            await createAuthorityOfficer({
                name: name.trim(),
                mobile: mobile.trim(),
                email: email.trim() || undefined,
                password,
                role,
                department_id: departmentId ? Number(departmentId) : undefined,
                designation: designation.trim() || undefined,
            });
            setShowModal(false);
            setName("");
            setMobile("");
            setEmail("");
            setPassword("");
            setDesignation("");
            fetchData();
        } catch (err) {
            setFormError(err.response?.data?.detail || "Provisioning failed.");
        } finally {
            setSubmitting(false);
        }
    };

    const handleToggleActive = async (officer) => {
        try {
            await updateAuthorityOfficer(officer.id, {
                is_active: !officer.is_active,
            });
            fetchData();
        } catch (err) {
            alert(err.response?.data?.detail || "Action failed.");
        }
    };

    return (
        <AuthorityLayout title="Municipal Officers & Personnel">
            <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                        <h1 style={{ fontSize: "24px", fontWeight: 800, color: "#fff", margin: "0 0 6px" }}>
                            Authority Officers Directory
                        </h1>
                        <p style={{ fontSize: "14px", color: "#94a3b8", margin: 0 }}>
                            Provision department heads, dispatch coordinators, and field inspectors
                        </p>
                    </div>

                    <button
                        type="button"
                        onClick={() => setShowModal(true)}
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
                        <span>Provision Officer</span>
                    </button>
                </div>

                {/* FILTERS */}
                <div className="issue-filter-bar">
                    <select
                        className="issue-select"
                        value={roleFilter}
                        onChange={(e) => setRoleFilter(e.target.value)}
                    >
                        <option value="">All Roles</option>
                        <option value="SUPER_ADMIN">Super Admin</option>
                        <option value="DEPARTMENT_OFFICER">Department Officer</option>
                        <option value="FIELD_OFFICER">Field Officer</option>
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
                            <p>Loading officer accounts...</p>
                        </div>
                    ) : (
                        <table className="auth-table">
                            <thead>
                                <tr>
                                    <th>Name & Employee ID</th>
                                    <th>Role</th>
                                    <th>Department</th>
                                    <th>Designation</th>
                                    <th>Contact Details</th>
                                    <th>Status</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {officers.map((o) => (
                                    <tr key={o.id}>
                                        <td>
                                            <div style={{ fontWeight: 700, color: "#f8fafc" }}>{o.name}</div>
                                            <div style={{ fontSize: "11.5px", color: "#38bdf8" }}>{o.employee_id}</div>
                                        </td>
                                        <td>
                                            <span className={`authority-officer-role-badge badge-${o.role.toLowerCase()}`}>
                                                {o.role.replace("_", " ")}
                                            </span>
                                        </td>
                                        <td>
                                            <span style={{ color: o.department_name ? "#cbd5e1" : "#64748b" }}>
                                                {o.department_name || "Central / All"}
                                            </span>
                                        </td>
                                        <td>{o.designation || "Municipal Staff"}</td>
                                        <td>
                                            <div style={{ fontSize: "12px" }}>{o.mobile}</div>
                                            <div style={{ fontSize: "11px", color: "#64748b" }}>{o.email || "No email"}</div>
                                        </td>
                                        <td>
                                            <span style={{
                                                padding: "3px 8px",
                                                borderRadius: "4px",
                                                fontSize: "11px",
                                                fontWeight: 700,
                                                background: o.is_active ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)",
                                                color: o.is_active ? "#4ade80" : "#f87171",
                                            }}>
                                                {o.is_active ? "ACTIVE" : "INACTIVE"}
                                            </span>
                                        </td>
                                        <td>
                                            <button
                                                type="button"
                                                onClick={() => handleToggleActive(o)}
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
                                                {o.is_active ? "Deactivate" : "Activate"}
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>

                {/* PROVISION MODAL */}
                {showModal && (
                    <div className="modal-overlay">
                        <div className="modal-content">
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                                <h3 className="modal-title" style={{ margin: 0 }}>Provision Authority Officer</h3>
                                <button type="button" onClick={() => setShowModal(false)} style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer" }}>
                                    <X size={18} />
                                </button>
                            </div>

                            {formError && (
                                <div style={{ padding: "10px", background: "rgba(239,68,68,0.12)", color: "#f87171", borderRadius: "6px", marginBottom: "14px", fontSize: "12.5px" }}>
                                    {formError}
                                </div>
                            )}

                            <form onSubmit={handleCreateOfficer} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                                <div>
                                    <label style={{ fontSize: "12.5px", color: "#cbd5e1" }}>Full Name</label>
                                    <input
                                        type="text"
                                        className="issue-search-input"
                                        placeholder="Officer Name"
                                        value={name}
                                        onChange={(e) => setName(e.target.value)}
                                        required
                                    />
                                </div>

                                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                                    <div>
                                        <label style={{ fontSize: "12.5px", color: "#cbd5e1" }}>Mobile Number</label>
                                        <input
                                            type="text"
                                            className="issue-search-input"
                                            placeholder="10-digit mobile"
                                            value={mobile}
                                            onChange={(e) => setMobile(e.target.value)}
                                            required
                                        />
                                    </div>
                                    <div>
                                        <label style={{ fontSize: "12.5px", color: "#cbd5e1" }}>Email Address</label>
                                        <input
                                            type="email"
                                            className="issue-search-input"
                                            placeholder="officer@civicsol.gov.in"
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                        />
                                    </div>
                                </div>

                                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                                    <div>
                                        <label style={{ fontSize: "12.5px", color: "#cbd5e1" }}>Role</label>
                                        <select
                                            className="issue-select"
                                            style={{ width: "100%" }}
                                            value={role}
                                            onChange={(e) => setRole(e.target.value)}
                                        >
                                            <option value="FIELD_OFFICER">Field Officer</option>
                                            <option value="DEPARTMENT_OFFICER">Department Officer</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label style={{ fontSize: "12.5px", color: "#cbd5e1" }}>Department</label>
                                        <select
                                            className="issue-select"
                                            style={{ width: "100%" }}
                                            value={departmentId}
                                            onChange={(e) => setDepartmentId(e.target.value)}
                                        >
                                            <option value="">-- No Department --</option>
                                            {departments.map((d) => (
                                                <option key={d.id} value={d.id}>{d.name}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>

                                <div>
                                    <label style={{ fontSize: "12.5px", color: "#cbd5e1" }}>Designation</label>
                                    <input
                                        type="text"
                                        className="issue-search-input"
                                        placeholder="e.g. Zonal Road Inspector"
                                        value={designation}
                                        onChange={(e) => setDesignation(e.target.value)}
                                    />
                                </div>

                                <div>
                                    <label style={{ fontSize: "12.5px", color: "#cbd5e1" }}>Temporary Password (min 8 chars)</label>
                                    <input
                                        type="password"
                                        className="issue-search-input"
                                        placeholder="Enter password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        required
                                        minLength={8}
                                    />
                                </div>

                                <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
                                    <button type="button" className="pagination-btn" onClick={() => setShowModal(false)}>
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={submitting}
                                        style={{ padding: "8px 18px", borderRadius: "6px", background: "#0284c7", color: "#fff", border: "none", cursor: "pointer", fontWeight: 600 }}
                                    >
                                        {submitting ? "Provisioning..." : "Provision Account"}
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
