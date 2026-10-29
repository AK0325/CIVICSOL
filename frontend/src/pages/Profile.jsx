import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
    ArrowLeft,
    Award,
    BadgeCheck,
    Bell,
    CheckCircle2,
    ChevronRight,
    CircleHelp,
    Edit3,
    FileText,
    Globe,
    Lock,
    LogOut,
    Mail,
    MapPin,
    Pencil,
    Phone,
    ShieldCheck,
    Trash2,
    User,
    X,
} from "lucide-react";

import {
    getCurrentUser,
    getMyIssues,
    getRewardSummary,
    getCitizenBadges,
    updateCitizenProfile,
    changeCitizenPassword,
    logoutCitizen,
} from "../services/api";

import "./Profile.css";


/* =========================================================
   PROFILE
========================================================= */

const Profile = () => {

    const navigate = useNavigate();

    const [user, setUser] = useState(null);
    const [issues, setIssues] = useState([]);
    const [rewardSummary, setRewardSummary] = useState(null);
    const [badges, setBadges] = useState([]);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const [showEdit, setShowEdit] = useState(false);
    const [showDelete, setShowDelete] = useState(false);
    const [showPassword, setShowPassword] = useState(false);


    /* =====================================================
       LOAD PROFILE
    ===================================================== */

    useEffect(() => {

        let mounted = true;

        const loadProfile = async () => {

            try {

                setLoading(true);
                setError("");

                const [
                    userData,
                    issueData,
                    rewardData,
                    badgeData,
                ] = await Promise.all([
                    getCurrentUser(),
                    getMyIssues(),
                    getRewardSummary(),
                    getCitizenBadges(),
                ]);

                if (!mounted) {
                    return;
                }

                setUser(userData);

                setIssues(
                    Array.isArray(issueData)
                        ? issueData
                        : []
                );

                setRewardSummary(
                    rewardData || null
                );

                setBadges(
                    Array.isArray(badgeData)
                        ? badgeData
                        : []
                );


                /* =========================================
                   KEEP NAVBAR USER DATA SYNCHRONIZED
                ========================================= */

                if (userData) {

                    localStorage.setItem(
                        "civicsol_citizen",
                        JSON.stringify({
                            citizen_id:
                                userData.citizen_id,
                            name:
                                userData.name,
                        })
                    );

                }

            } catch (err) {

                console.error(
                    "Profile loading error:",
                    err
                );

                if (
                    err.response?.status === 401 ||
                    err.response?.status === 403
                ) {

                    logoutCitizen();

                    navigate("/signin", {
                        replace: true,
                    });

                    return;
                }

                if (mounted) {

                    setError(
                        err.response?.data?.detail ||
                        "Unable to load your profile."
                    );

                }

            } finally {

                if (mounted) {
                    setLoading(false);
                }

            }
        };


        loadProfile();


        return () => {
            mounted = false;
        };

    }, [navigate]);


    /* =====================================================
       STATISTICS
    ===================================================== */

    const verifiedCount = issues.filter(
        (issue) =>
            String(issue.status || "")
                .toLowerCase() === "verified"
    ).length;


    const resolvedCount = issues.filter(
        (issue) =>
            String(issue.status || "")
                .toLowerCase() === "resolved"
    ).length;


    const civicCredits =
        Number(rewardSummary?.credits) || 0;


    const level =
        rewardSummary?.level ||
        "Civic Observer";


    const progress =
        Math.min(
            100,
            Math.max(
                0,
                Number(
                    rewardSummary?.progress
                ) || 0
            )
        );


    /* =====================================================
       LOGOUT
    ===================================================== */

    const handleLogout = () => {

        logoutCitizen();

        navigate("/signin", {
            replace: true,
        });

    };


    /* =====================================================
       LOADING
    ===================================================== */

    if (loading) {

        return (

            <main className="profile-page">

                <div className="profile-loading">

                    <div className="profile-loading-spinner" />

                    <p>
                        Loading your profile...
                    </p>

                </div>

            </main>
        );

    }


    /* =====================================================
       ERROR
    ===================================================== */

    if (error) {

        return (

            <main className="profile-page">

                <div className="profile-error">

                    <ShieldCheck size={30} />

                    <h2>
                        Unable to load profile
                    </h2>

                    <p>
                        {error}
                    </p>

                    <button
                        type="button"
                        onClick={() =>
                            window.location.reload()
                        }
                    >
                        Try Again
                    </button>

                </div>

            </main>
        );

    }


    /* =====================================================
       PROFILE PAGE
    ===================================================== */

    return (

        <main className="profile-page">

            <div className="profile-glow profile-glow-one" />

            <div className="profile-glow profile-glow-two" />


            <div className="profile-container">


                {/* =================================================
                    TOP BAR
                ================================================= */}

                <header className="profile-topbar">

                    <button
                        type="button"
                        className="profile-back"
                        onClick={() =>
                            navigate(
                                "/citizen-dashboard"
                            )
                        }
                    >

                        <ArrowLeft size={17} />

                        <span>
                            Dashboard
                        </span>

                    </button>


                    <div className="profile-top-actions">

                        <button
                            type="button"
                            className="profile-notification"
                            aria-label="Notifications"
                        >

                            <Bell size={18} />

                            <span />

                        </button>

                    </div>

                </header>


                {/* =================================================
                    PAGE TITLE
                ================================================= */}

                <section className="profile-title">

                    <span>
                        CITIZEN ACCOUNT
                    </span>

                    <h1>
                        My CIVICSOL Profile
                    </h1>

                    <p>
                        Manage your citizen identity,
                        personal information and civic
                        activity.
                    </p>

                </section>


                {/* =================================================
                    IDENTITY CARD
                ================================================= */}

                <section className="profile-identity-card">

                    <div className="identity-main">

                        <div className="identity-avatar">

                            <User size={38} />

                        </div>


                        <div className="identity-info">

                            <span className="identity-label">
                                CITIZEN IDENTITY
                            </span>

                            <h2>
                                {user?.name ||
                                    "Citizen"}
                            </h2>

                            <div className="identity-id">

                                <BadgeCheck size={15} />

                                {user?.citizen_id ||
                                    "CIVIC"}

                            </div>

                            <div className="identity-level">

                                <Award size={15} />

                                {level}

                            </div>

                        </div>

                    </div>


                    <button
                        type="button"
                        className="edit-profile-button"
                        onClick={() =>
                            setShowEdit(true)
                        }
                    >

                        <Edit3 size={16} />

                        Edit Profile

                    </button>

                </section>


                {/* =================================================
                    QUICK STATS
                ================================================= */}

                <section className="profile-stats">

                    <ProfileStat
                        icon={
                            <FileText size={20} />
                        }
                        label="My Reports"
                        value={issues.length}
                        className="blue"
                    />

                    <ProfileStat
                        icon={
                            <Award size={20} />
                        }
                        label="Civic Credits"
                        value={civicCredits}
                        className="gold"
                    />

                    <ProfileStat
                        icon={
                            <BadgeCheck size={20} />
                        }
                        label="Verified Issues"
                        value={verifiedCount}
                        className="cyan"
                    />

                    <ProfileStat
                        icon={
                            <CheckCircle2 size={20} />
                        }
                        label="Resolved Issues"
                        value={resolvedCount}
                        className="green"
                    />

                </section>


                {/* =================================================
                    CONTENT GRID
                ================================================= */}

                <section className="profile-content-grid">


                    {/* =================================================
                        MAIN CONTENT
                    ================================================= */}

                    <div className="profile-content-main">


                        {/* PERSONAL INFORMATION */}

                        <ProfileSection
                            eyebrow="PERSONAL INFORMATION"
                            title="Your personal details"
                            icon={
                                <User size={19} />
                            }
                        >

                            <InfoRow
                                icon={
                                    <User size={16} />
                                }
                                label="Full Name"
                                value={
                                    user?.name ||
                                    "Not provided"
                                }
                            />

                            <InfoRow
                                icon={
                                    <Phone size={16} />
                                }
                                label="Mobile"
                                value={maskMobile(
                                    user?.mobile
                                )}
                            />

                            <InfoRow
                                icon={
                                    <Mail size={16} />
                                }
                                label="Email"
                                value={
                                    user?.email ||
                                    "Not provided"
                                }
                            />

                            <InfoRow
                                icon={
                                    <Globe size={16} />
                                }
                                label="Language"
                                value={
                                    user?.preferred_language ||
                                    "English"
                                }
                            />

                        </ProfileSection>


                        {/* CIVIC IDENTITY */}

                        <ProfileSection
                            eyebrow="CIVIC IDENTITY"
                            title="Your civic information"
                            icon={
                                <MapPin size={19} />
                            }
                        >

                            <InfoRow
                                icon={
                                    <BadgeCheck
                                        size={16}
                                    />
                                }
                                label="Citizen ID"
                                value={
                                    user?.citizen_id ||
                                    "—"
                                }
                                highlight
                            />

                            <InfoRow
                                icon={
                                    <MapPin size={16} />
                                }
                                label="Ward"
                                value={
                                    user?.ward ||
                                    "Not assigned"
                                }
                            />

                            <InfoRow
                                icon={
                                    <MapPin size={16} />
                                }
                                label="Zone"
                                value={
                                    user?.zone ||
                                    "Not assigned"
                                }
                            />

                            <InfoRow
                                icon={
                                    <MapPin size={16} />
                                }
                                label="Locality"
                                value="Derived from report location"
                            />

                        </ProfileSection>


                        {/* ACHIEVEMENTS */}

                        <ProfileSection
                            eyebrow="ACHIEVEMENTS"
                            title="Civic badges"
                            icon={
                                <Award size={19} />
                            }
                        >

                            <div className="profile-badges">

                                {badges.length === 0 ? (

                                    <div className="no-badges">

                                        <Award size={24} />

                                        <span>
                                            Your civic
                                            achievements
                                            will appear here.
                                        </span>

                                    </div>

                                ) : (

                                    badges.map(
                                        (badge) => (

                                            <div
                                                key={
                                                    badge.id
                                                }
                                                className={
                                                    `profile-badge ${badge.earned
                                                        ? "earned"
                                                        : "locked"
                                                    }`
                                                }
                                            >

                                                <div className="badge-icon">

                                                    {badge.earned ? (
                                                        <Award
                                                            size={20}
                                                        />
                                                    ) : (
                                                        <Lock
                                                            size={17}
                                                        />
                                                    )}

                                                </div>

                                                <div>

                                                    <strong>
                                                        {
                                                            badge.name
                                                        }
                                                    </strong>

                                                    <span>
                                                        {
                                                            badge.description ||
                                                            "Civic contribution achievement"
                                                        }
                                                    </span>

                                                </div>

                                            </div>

                                        )
                                    )

                                )}

                            </div>

                        </ProfileSection>

                    </div>


                    {/* =================================================
                        SIDEBAR
                    ================================================= */}

                    <aside className="profile-sidebar">


                        {/* CIVIC LEVEL */}

                        <section className="profile-level-card">

                            <div className="level-card-icon">

                                <Award size={23} />

                            </div>

                            <span>
                                CURRENT LEVEL
                            </span>

                            <h2>
                                {level}
                            </h2>

                            <strong>

                                {civicCredits}

                                {" "}

                                <small>
                                    civic credits
                                </small>

                            </strong>

                            <div className="level-progress">

                                <div
                                    style={{
                                        width:
                                            `${progress}%`,
                                    }}
                                />

                            </div>

                            <button
                                type="button"
                                onClick={() =>
                                    navigate(
                                        "/rewards"
                                    )
                                }
                            >

                                View Rewards

                                <ChevronRight
                                    size={15}
                                />

                            </button>

                        </section>


                        {/* SECURITY */}

                        <section className="profile-menu-card">

                            <MenuHeading
                                icon={
                                    <ShieldCheck
                                        size={18}
                                    />
                                }
                                title="Security & Privacy"
                            />

                            <MenuItem
                                icon={
                                    <Lock size={17} />
                                }
                                title="Change Password"
                                onClick={() =>
                                    setShowPassword(true)
                                }
                            />

                            <MenuItem
                                icon={
                                    <Bell size={17} />
                                }
                                title="Notification Settings"
                            />

                            <MenuItem
                                icon={
                                    <ShieldCheck
                                        size={17}
                                    />
                                }
                                title="Privacy Settings"
                            />

                        </section>


                        {/* SUPPORT */}

                        <section className="profile-menu-card">

                            <MenuHeading
                                icon={
                                    <CircleHelp
                                        size={18}
                                    />
                                }
                                title="Support"
                            />

                            <MenuItem
                                icon={
                                    <CircleHelp
                                        size={17}
                                    />
                                }
                                title="Help & Support"
                            />

                            <MenuItem
                                icon={
                                    <FileText
                                        size={17}
                                    />
                                }
                                title="Terms & Conditions"
                            />

                            <MenuItem
                                icon={
                                    <ShieldCheck
                                        size={17}
                                    />
                                }
                                title="Privacy Policy"
                            />

                        </section>


                        {/* ACCOUNT ACTIONS */}

                        <section className="profile-account-actions">

                            <button
                                type="button"
                                className="logout-button"
                                onClick={
                                    handleLogout
                                }
                            >

                                <LogOut size={17} />

                                Logout

                            </button>

                            <button
                                type="button"
                                className="delete-account-button"
                                onClick={() =>
                                    setShowDelete(true)
                                }
                            >

                                <Trash2 size={16} />

                                Delete Account

                            </button>

                        </section>

                    </aside>

                </section>


                {/* =================================================
                    SECURITY NOTE
                ================================================= */}

                <div className="profile-security-note">

                    <ShieldCheck size={15} />

                    <span>
                        Your CIVICSOL account information
                        is protected and used for civic
                        service management.
                    </span>

                </div>

            </div>


            {/* =================================================
                EDIT PROFILE
            ================================================= */}

            {showEdit && (

                <EditProfileModal
                    user={user}
                    onClose={() =>
                        setShowEdit(false)
                    }
                    onSaved={(updatedUser) => {

                        setUser(updatedUser);

                        localStorage.setItem(
                            "civicsol_citizen",
                            JSON.stringify({
                                citizen_id:
                                    updatedUser.citizen_id,
                                name:
                                    updatedUser.name,
                            })
                        );

                        setShowEdit(false);

                    }}
                />

            )}


            {/* =================================================
                CHANGE PASSWORD
            ================================================= */}

            {showPassword && (

                <ChangePasswordModal
                    onClose={() =>
                        setShowPassword(false)
                    }
                />

            )}


            {/* =================================================
                DELETE ACCOUNT
            ================================================= */}

            {showDelete && (

                <div
                    className="profile-modal-backdrop"
                    onMouseDown={(event) => {

                        if (
                            event.target ===
                            event.currentTarget
                        ) {

                            setShowDelete(false);

                        }

                    }}
                >

                    <div className="profile-modal delete-modal">

                        <button
                            type="button"
                            className="modal-close"
                            onClick={() =>
                                setShowDelete(false)
                            }
                        >

                            <X size={18} />

                        </button>


                        <div className="delete-icon">

                            <Trash2 size={25} />

                        </div>


                        <h2>
                            Delete account?
                        </h2>


                        <p>
                            Account deletion is not
                            available yet. This feature
                            will be connected to the
                            secure backend account
                            deletion endpoint.
                        </p>


                        <div className="modal-actions">

                            <button
                                type="button"
                                className="modal-cancel"
                                onClick={() =>
                                    setShowDelete(false)
                                }
                            >
                                Cancel
                            </button>

                            <button
                                type="button"
                                className="modal-danger"
                                onClick={() =>
                                    setShowDelete(false)
                                }
                            >
                                Close
                            </button>

                        </div>

                    </div>

                </div>

            )}

        </main>
    );
};


/* =========================================================
   PROFILE STAT
========================================================= */

const ProfileStat = ({
    icon,
    label,
    value,
    className,
}) => {

    return (

        <div className="profile-stat">

            <div
                className={
                    `profile-stat-icon ${className}`
                }
            >
                {icon}
            </div>

            <div>

                <span>
                    {label}
                </span>

                <strong>
                    {value}
                </strong>

            </div>

        </div>
    );
};


/* =========================================================
   PROFILE SECTION
========================================================= */

const ProfileSection = ({
    eyebrow,
    title,
    icon,
    children,
}) => {

    return (

        <section className="profile-section">

            <div className="profile-section-heading">

                <div className="section-heading-icon">
                    {icon}
                </div>

                <div>

                    <span>
                        {eyebrow}
                    </span>

                    <h2>
                        {title}
                    </h2>

                </div>

            </div>

            <div className="profile-section-content">
                {children}
            </div>

        </section>
    );
};


/* =========================================================
   INFO ROW
========================================================= */

const InfoRow = ({
    icon,
    label,
    value,
    highlight = false,
}) => {

    return (

        <div className="profile-info-row">

            <div className="info-label">

                <div className="info-row-icon">
                    {icon}
                </div>

                <span>
                    {label}
                </span>

            </div>

            <strong
                className={
                    highlight
                        ? "highlight-value"
                        : ""
                }
            >
                {value}
            </strong>

        </div>
    );
};


/* =========================================================
   MENU HEADING
========================================================= */

const MenuHeading = ({
    icon,
    title,
}) => {

    return (

        <div className="menu-heading">

            <div>
                {icon}
            </div>

            <h3>
                {title}
            </h3>

        </div>
    );
};


/* =========================================================
   MENU ITEM
========================================================= */

const MenuItem = ({
    icon,
    title,
    onClick,
}) => {

    return (

        <button
            type="button"
            className="profile-menu-item"
            onClick={onClick}
        >

            <div className="menu-item-left">

                {icon}

                <span>
                    {title}
                </span>

            </div>

            <ChevronRight size={15} />

        </button>
    );
};


/* =========================================================
   EDIT PROFILE MODAL
========================================================= */

const EditProfileModal = ({
    user,
    onClose,
    onSaved,
}) => {

    const [name, setName] =
        useState(user?.name || "");

    const [email, setEmail] =
        useState(user?.email || "");

    const [language, setLanguage] =
        useState(
            user?.preferred_language ||
            "English"
        );

    const [saving, setSaving] =
        useState(false);

    const [error, setError] =
        useState("");


    const handleSave = async () => {

        if (!name.trim()) {

            setError(
                "Name cannot be empty."
            );

            return;
        }


        try {

            setSaving(true);
            setError("");


            const updatedUser =
                await updateCitizenProfile({
                    name: name.trim(),
                    email: email.trim(),
                    preferred_language: language,
                });


            onSaved(updatedUser);

        } catch (err) {

            console.error(
                "Profile update error:",
                err
            );


            if (
                err.response?.status === 401 ||
                err.response?.status === 403
            ) {

                logoutCitizen();

                onClose();

                window.location.replace(
                    "/signin"
                );

                return;
            }


            setError(
                err.response?.data?.detail ||
                "Unable to update profile."
            );

        } finally {

            setSaving(false);

        }
    };


    return (

        <div
            className="profile-modal-backdrop"
            onMouseDown={(event) => {

                if (
                    event.target ===
                    event.currentTarget &&
                    !saving
                ) {

                    onClose();

                }

            }}
        >

            <div className="profile-modal">

                <button
                    type="button"
                    className="modal-close"
                    onClick={onClose}
                    disabled={saving}
                >

                    <X size={18} />

                </button>


                <div className="modal-icon">

                    <Pencil size={20} />

                </div>


                <span className="modal-eyebrow">
                    ACCOUNT SETTINGS
                </span>


                <h2>
                    Edit Profile
                </h2>


                <p>
                    Update your personal
                    information.
                </p>


                {error && (

                    <div className="modal-error">
                        {error}
                    </div>

                )}


                {/* NAME */}

                <div className="modal-field">

                    <label>
                        Full Name
                    </label>

                    <input
                        type="text"
                        value={name}
                        onChange={(event) =>
                            setName(
                                event.target.value
                            )
                        }
                        disabled={saving}
                    />

                </div>


                {/* MOBILE */}

                <div className="modal-field">

                    <label>
                        Mobile Number
                    </label>

                    <input
                        type="text"
                        value={
                            user?.mobile ||
                            ""
                        }
                        disabled
                    />

                    <small>
                        Mobile number cannot be
                        changed here.
                    </small>

                </div>


                {/* EMAIL */}

                <div className="modal-field">

                    <label>
                        Email
                    </label>

                    <input
                        type="email"
                        value={email}
                        onChange={(event) =>
                            setEmail(
                                event.target.value
                            )
                        }
                        placeholder="example@email.com"
                        disabled={saving}
                    />

                </div>


                {/* LANGUAGE */}

                <div className="modal-field">

                    <label>
                        Preferred Language
                    </label>

                    <select
                        value={language}
                        onChange={(event) =>
                            setLanguage(
                                event.target.value
                            )
                        }
                        disabled={saving}
                    >

                        <option value="English">
                            English
                        </option>

                        <option value="Hindi">
                            Hindi
                        </option>

                        <option value="Gujarati">
                            Gujarati
                        </option>

                    </select>

                </div>


                {/* ACTIONS */}

                <div className="modal-actions">

                    <button
                        type="button"
                        className="modal-cancel"
                        onClick={onClose}
                        disabled={saving}
                    >
                        Cancel
                    </button>


                    <button
                        type="button"
                        className="modal-save"
                        onClick={handleSave}
                        disabled={saving}
                    >

                        {saving
                            ? "Saving..."
                            : "Save Changes"}

                    </button>

                </div>

            </div>

        </div>
    );
};


/* =========================================================
   CHANGE PASSWORD MODAL
========================================================= */

const ChangePasswordModal = ({
    onClose,
}) => {

    const [currentPassword, setCurrentPassword] =
        useState("");

    const [newPassword, setNewPassword] =
        useState("");

    const [confirmPassword, setConfirmPassword] =
        useState("");

    const [showCurrent, setShowCurrent] =
        useState(false);

    const [showNew, setShowNew] =
        useState(false);

    const [showConfirm, setShowConfirm] =
        useState(false);

    const [saving, setSaving] =
        useState(false);

    const [error, setError] =
        useState("");

    const [success, setSuccess] =
        useState("");


    const handleSubmit = async (event) => {

        event.preventDefault();

        setError("");
        setSuccess("");


        if (
            !currentPassword ||
            !newPassword ||
            !confirmPassword
        ) {

            setError(
                "Please fill in all password fields."
            );

            return;
        }


        if (newPassword.length < 8) {

            setError(
                "New password must contain at least 8 characters."
            );

            return;
        }


        if (
            newPassword !==
            confirmPassword
        ) {

            setError(
                "New password and confirmation do not match."
            );

            return;
        }


        if (
            currentPassword ===
            newPassword
        ) {

            setError(
                "New password must be different from your current password."
            );

            return;
        }


        try {

            setSaving(true);


            const response =
                await changeCitizenPassword({
                    current_password:
                        currentPassword,

                    new_password:
                        newPassword,
                });


            setSuccess(
                response?.message ||
                "Password changed successfully."
            );


            setCurrentPassword("");
            setNewPassword("");
            setConfirmPassword("");


            setTimeout(() => {

                onClose();

            }, 1200);

        } catch (err) {

            console.error(
                "Password change error:",
                err
            );


            if (
                err.response?.status === 401 ||
                err.response?.status === 403
            ) {

                logoutCitizen();

                window.location.replace(
                    "/signin"
                );

                return;
            }


            setError(
                err.response?.data?.detail ||
                "Unable to change password. Please try again."
            );

        } finally {

            setSaving(false);

        }
    };


    return (

        <div
            className="profile-modal-backdrop"
            onMouseDown={(event) => {

                if (
                    event.target ===
                    event.currentTarget &&
                    !saving
                ) {

                    onClose();

                }

            }}
        >

            <div className="profile-modal password-modal">

                <button
                    type="button"
                    className="modal-close"
                    onClick={onClose}
                    disabled={saving}
                >

                    <X size={18} />

                </button>


                <div className="modal-icon">

                    <Lock size={21} />

                </div>


                <span className="modal-eyebrow">
                    SECURITY
                </span>


                <h2>
                    Change Password
                </h2>


                <p className="modal-description">
                    Update your CIVICSOL account
                    password to keep your citizen
                    account secure.
                </p>


                {error && (

                    <div className="password-message password-error">
                        {error}
                    </div>

                )}


                {success && (

                    <div className="password-message password-success">
                        {success}
                    </div>

                )}


                <form onSubmit={handleSubmit}>


                    {/* CURRENT PASSWORD */}

                    <div className="password-field">

                        <label>
                            Current Password
                        </label>

                        <div className="password-input-wrapper">

                            <input
                                type={
                                    showCurrent
                                        ? "text"
                                        : "password"
                                }
                                value={currentPassword}
                                onChange={(event) =>
                                    setCurrentPassword(
                                        event.target.value
                                    )
                                }
                                placeholder="Enter current password"
                                disabled={saving}
                                autoComplete="current-password"
                            />

                            <button
                                type="button"
                                className="password-toggle"
                                onClick={() =>
                                    setShowCurrent(
                                        !showCurrent
                                    )
                                }
                                disabled={saving}
                                tabIndex={-1}
                            >

                                {showCurrent
                                    ? "Hide"
                                    : "Show"}

                            </button>

                        </div>

                    </div>


                    {/* NEW PASSWORD */}

                    <div className="password-field">

                        <label>
                            New Password
                        </label>

                        <div className="password-input-wrapper">

                            <input
                                type={
                                    showNew
                                        ? "text"
                                        : "password"
                                }
                                value={newPassword}
                                onChange={(event) =>
                                    setNewPassword(
                                        event.target.value
                                    )
                                }
                                placeholder="Enter new password"
                                disabled={saving}
                                autoComplete="new-password"
                            />

                            <button
                                type="button"
                                className="password-toggle"
                                onClick={() =>
                                    setShowNew(
                                        !showNew
                                    )
                                }
                                disabled={saving}
                                tabIndex={-1}
                            >

                                {showNew
                                    ? "Hide"
                                    : "Show"}

                            </button>

                        </div>

                    </div>


                    {/* CONFIRM PASSWORD */}

                    <div className="password-field">

                        <label>
                            Confirm New Password
                        </label>

                        <div className="password-input-wrapper">

                            <input
                                type={
                                    showConfirm
                                        ? "text"
                                        : "password"
                                }
                                value={confirmPassword}
                                onChange={(event) =>
                                    setConfirmPassword(
                                        event.target.value
                                    )
                                }
                                placeholder="Re-enter new password"
                                disabled={saving}
                                autoComplete="new-password"
                            />

                            <button
                                type="button"
                                className="password-toggle"
                                onClick={() =>
                                    setShowConfirm(
                                        !showConfirm
                                    )
                                }
                                disabled={saving}
                                tabIndex={-1}
                            >

                                {showConfirm
                                    ? "Hide"
                                    : "Show"}

                            </button>

                        </div>

                    </div>


                    {/* REQUIREMENTS */}

                    <div className="password-requirements">

                        <div>
                            Password requirements
                        </div>

                        <span
                            className={
                                newPassword.length >= 8
                                    ? "requirement-valid"
                                    : ""
                            }
                        >
                            ✓ At least 8 characters
                        </span>

                        <span
                            className={
                                newPassword &&
                                    newPassword ===
                                    confirmPassword
                                    ? "requirement-valid"
                                    : ""
                            }
                        >
                            ✓ Passwords match
                        </span>

                    </div>


                    {/* ACTIONS */}

                    <div className="modal-actions">

                        <button
                            type="button"
                            className="modal-cancel"
                            onClick={onClose}
                            disabled={saving}
                        >
                            Cancel
                        </button>


                        <button
                            type="submit"
                            className="modal-save"
                            disabled={saving}
                        >

                            {saving
                                ? "Updating..."
                                : "Update Password"}

                        </button>

                    </div>

                </form>

            </div>

        </div>
    );
};


/* =========================================================
   MOBILE MASK
========================================================= */

const maskMobile = (mobile) => {

    if (!mobile) {
        return "Not provided";
    }


    const value = String(mobile);


    if (value.length < 4) {
        return "********";
    }


    return (
        "*".repeat(
            Math.max(
                0,
                value.length - 2
            )
        ) +
        value.slice(-2)
    );
};


export default Profile;