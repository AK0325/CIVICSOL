import { Link, NavLink, useNavigate } from "react-router-dom";
import {
    Activity,
    AlertCircle,
    Building2,
    FileSpreadsheet,
    FileText,
    History,
    LayoutDashboard,
    LogOut,
    MapPin,
    Shield,
    Users,
} from "lucide-react";
import { logoutAuthority } from "../services/authorityApi";
import NotificationCenter from "./NotificationCenter";
import "./AuthorityLayout.css";

export default function AuthorityLayout({ children, title }) {
    const navigate = useNavigate();

    const rawUser = localStorage.getItem("civicsol_authority_user");
    let officer = {
        name: "Authorized Officer",
        role: "FIELD_OFFICER",
        employee_id: "OFF-00000",
        department_name: "Municipal Office",
    };

    if (rawUser) {
        try {
            officer = { ...officer, ...JSON.parse(rawUser) };
        } catch {
            // fallback
        }
    }

    const handleSignout = () => {
        logoutAuthority();
        navigate("/authority/login", { replace: true });
    };

    const isSuperAdmin = officer.role === "SUPER_ADMIN";
    const isDeptOfficer = officer.role === "DEPARTMENT_OFFICER" || isSuperAdmin;

    return (
        <div className="authority-layout">
            {/* SIDEBAR */}
            <aside className="authority-sidebar">
                <div className="authority-sidebar-brand">
                    <div className="authority-brand-icon">
                        <Shield size={22} strokeWidth={2.4} />
                    </div>
                    <div>
                        <h2 className="authority-brand-title">CIVICSOL</h2>
                        <p className="authority-brand-subtitle">Authority Center</p>
                    </div>
                </div>

                <nav className="authority-sidebar-nav">
                    <NavLink
                        to="/authority/dashboard"
                        className={({ isActive }) => `authority-nav-link ${isActive ? "active" : ""}`}
                    >
                        <LayoutDashboard size={18} />
                        <span>Command Center</span>
                    </NavLink>

                    <NavLink
                        to="/authority/issues"
                        className={({ isActive }) => `authority-nav-link ${isActive ? "active" : ""}`}
                    >
                        <FileSpreadsheet size={18} />
                        <span>Issue Dispatch</span>
                    </NavLink>

                    <NavLink
                        to="/authority/map"
                        className={({ isActive }) => `authority-nav-link ${isActive ? "active" : ""}`}
                    >
                        <MapPin size={18} />
                        <span>GIS Live Map</span>
                    </NavLink>

                    {isSuperAdmin && (
                        <NavLink
                            to="/authority/departments"
                            className={({ isActive }) => `authority-nav-link ${isActive ? "active" : ""}`}
                        >
                            <Building2 size={18} />
                            <span>Departments</span>
                        </NavLink>
                    )}

                    {isDeptOfficer && (
                        <NavLink
                            to="/authority/officers"
                            className={({ isActive }) => `authority-nav-link ${isActive ? "active" : ""}`}
                        >
                            <Users size={18} />
                            <span>Officers</span>
                        </NavLink>
                    )}

                    <NavLink
                        to="/authority/analytics"
                        className={({ isActive }) => `authority-nav-link ${isActive ? "active" : ""}`}
                    >
                        <Activity size={18} />
                        <span>Analytics</span>
                    </NavLink>

                    {isSuperAdmin && (
                        <NavLink
                            to="/authority/audit-logs"
                            className={({ isActive }) => `authority-nav-link ${isActive ? "active" : ""}`}
                        >
                            <History size={18} />
                            <span>Audit Trail</span>
                        </NavLink>
                    )}
                </nav>

                <div className="authority-sidebar-footer">
                    <div className="authority-officer-card">
                        <span className="authority-officer-name">{officer.name}</span>
                        <span className={`authority-officer-role-badge badge-${officer.role.toLowerCase()}`}>
                            {officer.role.replace("_", " ")}
                        </span>
                        {officer.department_name && (
                            <span style={{ fontSize: "11px", color: "#64748b" }}>
                                {officer.department_name}
                            </span>
                        )}
                    </div>
                </div>
            </aside>

            {/* MAIN CONTENT AREA */}
            <div className="authority-main-container">
                <header className="authority-topbar">
                    <div className="authority-topbar-title">
                        <span>{title || "Municipal Command Center"}</span>
                    </div>

                    <div className="authority-topbar-actions" style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <NotificationCenter isAuthority={true} />

                        <button
                            type="button"
                            onClick={handleSignout}
                            className="authority-signout-btn"
                            title="Sign out of Authority Center"
                        >
                            <LogOut size={15} />
                            <span>Sign Out</span>
                        </button>
                    </div>
                </header>

                <main className="authority-page-content">{children}</main>
            </div>
        </div>
    );
}
