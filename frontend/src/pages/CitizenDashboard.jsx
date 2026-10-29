import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
    Activity,
    ArrowRight,
    Award,
    BadgeCheck,
    Bell,
    Camera,
    CheckCircle2,
    ChevronRight,
    FileText,
    Flame,
    MapPin,
    ShieldCheck,
    Target,
    Trophy,
    TrendingUp,
    User,
} from "lucide-react";

import {
    getCurrentUser,
    getMyIssues,
    getRewardSummary,
} from "../services/api";

import "./CitizenDashboard.css";


const CitizenDashboard = () => {

    const navigate = useNavigate();

    const [user, setUser] = useState(null);
    const [issues, setIssues] = useState([]);
    const [rewardSummary, setRewardSummary] = useState(null);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");


    // =====================================================
    // LOAD DASHBOARD
    // =====================================================

    useEffect(() => {

        const loadDashboard = async () => {

            try {

                setLoading(true);
                setError("");

                const [
                    userData,
                    issueData,
                    rewardData,
                ] = await Promise.all([
                    getCurrentUser(),
                    getMyIssues(),
                    getRewardSummary(),
                ]);

                setUser(userData);

                setIssues(
                    Array.isArray(issueData)
                        ? issueData
                        : []
                );

                setRewardSummary(
                    rewardData || null
                );

            } catch (err) {

                console.error(
                    "Citizen dashboard error:",
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
                    "Unable to load your citizen dashboard."
                );

            } finally {

                setLoading(false);

            }

        };

        loadDashboard();

    }, [navigate]);


    // =====================================================
    // ISSUE STATISTICS
    // =====================================================

    const verifiedCount = useMemo(() => {

        return issues.filter(
            (issue) =>
                String(issue.status || "")
                    .toLowerCase()
                === "verified"
        ).length;

    }, [issues]);


    const resolvedCount = useMemo(() => {

        return issues.filter(
            (issue) =>
                String(issue.status || "")
                    .toLowerCase()
                === "resolved"
        ).length;

    }, [issues]);


    // =====================================================
    // RECENT REPORTS
    // =====================================================

    const recentIssues = useMemo(() => {

        return issues.slice(0, 5);

    }, [issues]);


    // =====================================================
    // REAL REWARD DATA
    // =====================================================

    const civicCredits =
        Number(
            rewardSummary?.credits
        ) || 0;


    const level =
        rewardSummary?.level ||
        "Civic Observer";


    const levelStart =
        Number(
            rewardSummary?.level_start
        ) || 0;


    const levelTarget =
        Number(
            rewardSummary?.level_target
        ) || 100;


    const levelProgress =
        Number(
            rewardSummary?.progress
        ) || 0;


    // =====================================================
    // LOGOUT
    // =====================================================

    const handleLogout = () => {

        localStorage.removeItem(
            "civicsol_access_token"
        );

        localStorage.removeItem(
            "civicsol_citizen"
        );

        navigate("/signin");

    };


    // =====================================================
    // PROFILE
    // =====================================================

    const openProfile = () => {

        navigate("/profile");

    };


    // =====================================================
    // LOADING
    // =====================================================

    if (loading) {

        return (

            <main className="citizen-dashboard">

                <div className="dashboard-loading">

                    <Activity size={28} />

                    <p>
                        Loading your civic dashboard...
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

            <main className="citizen-dashboard">

                <div className="dashboard-error">

                    <ShieldCheck size={30} />

                    <h2>
                        Unable to load dashboard
                    </h2>

                    <p>
                        {error}
                    </p>

                    <button
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


    // =====================================================
    // DASHBOARD
    // =====================================================

    return (

        <main className="citizen-dashboard">

            {/* =================================================
                HEADER
            ================================================= */}

            <section className="dashboard-top">

                <div>

                    <p className="dashboard-eyebrow">
                        CITIZEN COMMAND CENTER
                    </p>

                    <h1>

                        Welcome back,

                        <span>
                            {" "}
                            {user?.name || "Citizen"}
                        </span>

                        {" "}👋

                    </h1>

                    <p className="dashboard-subtitle">

                        Your civic contribution is helping
                        make the city more responsive.

                    </p>

                </div>


                <div className="dashboard-actions">

                    {/* Notifications */}

                    <button
                        className="notification-button"
                        aria-label="Notifications"
                        onClick={() =>
                            navigate("/notifications")
                        }
                    >

                        <Bell size={19} />

                        <span />

                    </button>


                    {/* =================================================
                        CITIZEN PROFILE BUTTON
                        ================================================= */}

                    <button
                        type="button"
                        className="profile-chip"
                        onClick={openProfile}
                        aria-label="Open citizen profile"
                    >

                        <div className="profile-avatar">

                            <User size={18} />

                        </div>


                        <div>

                            <strong>
                                {user?.name || "Citizen"}
                            </strong>

                            <span>
                                {user?.citizen_id || "CIVIC"}
                            </span>

                        </div>


                        <ChevronRight size={16} />

                    </button>

                </div>

            </section>


            {/* =================================================
                STATISTICS
            ================================================= */}

            <section className="dashboard-stats">


                <div className="dashboard-stat-card">

                    <div className="stat-icon blue">

                        <FileText size={21} />

                    </div>


                    <div>

                        <span>
                            My Reports
                        </span>

                        <strong>
                            {issues.length}
                        </strong>

                    </div>

                </div>


                <div className="dashboard-stat-card">

                    <div className="stat-icon cyan">

                        <BadgeCheck size={21} />

                    </div>


                    <div>

                        <span>
                            Verified Issues
                        </span>

                        <strong>
                            {verifiedCount}
                        </strong>

                    </div>

                </div>


                <div className="dashboard-stat-card">

                    <div className="stat-icon green">

                        <CheckCircle2 size={21} />

                    </div>


                    <div>

                        <span>
                            Resolved Issues
                        </span>

                        <strong>
                            {resolvedCount}
                        </strong>

                    </div>

                </div>


                <div className="dashboard-stat-card">

                    <div className="stat-icon gold">

                        <Award size={21} />

                    </div>


                    <div>

                        <span>
                            Civic Credits
                        </span>

                        <strong>
                            {civicCredits}
                        </strong>

                    </div>

                </div>

            </section>


            {/* =================================================
                MAIN GRID
            ================================================= */}

            <section className="dashboard-grid">


                {/* =================================================
                    CIVIC LEVEL
                ================================================= */}

                <article className="civic-level-card">

                    <div className="card-heading">

                        <div>

                            <p>
                                CURRENT LEVEL
                            </p>

                            <h2>
                                {level}
                            </h2>

                        </div>


                        <div className="level-trophy">

                            <Trophy size={25} />

                        </div>

                    </div>


                    <div className="level-score">

                        <strong>
                            {civicCredits}
                        </strong>

                        <span>
                            / {levelTarget} credits
                        </span>

                    </div>


                    <div className="progress-track">

                        <div
                            className="progress-value"
                            style={{
                                width:
                                    `${levelProgress}%`,
                            }}
                        />

                    </div>


                    <div className="level-footer">

                        <span>
                            {Math.round(
                                levelProgress
                            )}% complete
                        </span>


                        <span>

                            Next:{" "}

                            {level ===
                                "Civic Observer"
                                ? "Civic Contributor"
                                : level ===
                                    "Civic Contributor"
                                    ? "Civic Champion"
                                    : level ===
                                        "Civic Champion"
                                        ? "Civic Leader"
                                        : level ===
                                            "Civic Leader"
                                            ? "Civic Ambassador"
                                            : "Maximum Level"}

                        </span>

                    </div>


                    <Link
                        to="/rewards"
                        className="level-link"
                    >

                        View Rewards

                        <ArrowRight size={16} />

                    </Link>

                </article>


                {/* =================================================
                    QUICK REPORT
                ================================================= */}

                <article className="quick-report-card">

                    <div className="quick-report-icon">

                        <Camera size={25} />

                    </div>


                    <p className="quick-report-label">
                        SEE SOMETHING?
                    </p>


                    <h2>
                        Report a civic issue
                    </h2>


                    <p>

                        Submit image and GPS evidence
                        so CIVICSOL can analyze and
                        prioritize the problem.

                    </p>


                    <Link
                        to="/report"
                        className="report-button"
                    >

                        Report Issue

                        <ArrowRight size={17} />

                    </Link>

                </article>


                {/* =================================================
                    RECENT REPORTS
                ================================================= */}

                <article className="recent-reports-card">


                    <div className="section-card-header">

                        <div>

                            <p>
                                MY ACTIVITY
                            </p>

                            <h2>
                                Recent Reports
                            </h2>

                        </div>


                        <Link to="/my-reports">

                            View All

                            <ArrowRight size={15} />

                        </Link>

                    </div>


                    {recentIssues.length === 0 ? (

                        <div className="empty-reports">

                            <FileText size={28} />

                            <h3>
                                No civic reports yet
                            </h3>

                            <p>
                                Your submitted issues
                                will appear here.
                            </p>


                            <Link to="/report">
                                Submit your first report
                            </Link>

                        </div>

                    ) : (

                        <div className="issue-list">

                            {recentIssues.map(
                                (issue) => (

                                    <div
                                        className="issue-row"
                                        key={issue.id}
                                    >

                                        <div className="issue-row-icon">

                                            <MapPin size={17} />

                                        </div>


                                        <div className="issue-row-content">

                                            <strong>

                                                {issue.title ||
                                                    "Civic Issue"}

                                            </strong>


                                            <span>

                                                {issue.category ||
                                                    "General"}

                                                {" • "}

                                                {issue.location ||
                                                    "Location unavailable"}

                                            </span>

                                        </div>


                                        <div className="issue-row-status">

                                            <span
                                                className={
                                                    `status-dot ${String(
                                                        issue.status ||
                                                        "Reported"
                                                    )
                                                        .toLowerCase()
                                                        .replace(
                                                            /\s+/g,
                                                            "-"
                                                        )
                                                    }`
                                                }
                                            />

                                            {issue.status ||
                                                "Reported"}

                                        </div>

                                    </div>

                                )
                            )}

                        </div>

                    )}

                </article>


                {/* =================================================
                    CONTRIBUTION
                ================================================= */}

                <article className="contribution-card">


                    <div className="section-card-header">

                        <div>

                            <p>
                                YOUR IMPACT
                            </p>

                            <h2>
                                Civic Contribution
                            </h2>

                        </div>


                        <TrendingUp size={20} />

                    </div>


                    <div className="impact-items">


                        <div className="impact-item">

                            <div>

                                <Target size={17} />

                                <span>
                                    Reports Submitted
                                </span>

                            </div>


                            <strong>
                                {issues.length}
                            </strong>

                        </div>


                        <div className="impact-item">

                            <div>

                                <BadgeCheck size={17} />

                                <span>
                                    Verified Contribution
                                </span>

                            </div>


                            <strong>
                                {verifiedCount}
                            </strong>

                        </div>


                        <div className="impact-item">

                            <div>

                                <CheckCircle2 size={17} />

                                <span>
                                    Issues Resolved
                                </span>

                            </div>


                            <strong>
                                {resolvedCount}
                            </strong>

                        </div>


                        <div className="impact-item">

                            <div>

                                <Flame size={17} />

                                <span>
                                    Civic Credits
                                </span>

                            </div>


                            <strong>
                                {civicCredits}
                            </strong>

                        </div>

                    </div>


                    <Link
                        to="/rewards"
                        className="contribution-link"
                    >

                        View Contribution Profile

                        <ArrowRight size={15} />

                    </Link>

                </article>


            </section>

        </main>

    );

};


export default CitizenDashboard;