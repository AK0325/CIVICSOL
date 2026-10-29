import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
    ArrowLeft,
    ArrowRight,
    Award,
    BadgeCheck,
    CalendarDays,
    CheckCircle2,
    Clock3,
    Flame,
    History,
    ShieldCheck,
    Sparkles,
    Star,
    Target,
    TrendingUp,
    Trophy,
    User,
    XCircle,
    Zap,
} from "lucide-react";

import {
    getCurrentUser,
    getRewardSummary,
    getCreditHistory,
    getCitizenBadges,
} from "../services/api";

import "./Rewards.css";


const Rewards = () => {

    const navigate = useNavigate();

    const [user, setUser] = useState(null);
    const [summary, setSummary] = useState(null);
    const [history, setHistory] = useState([]);
    const [badges, setBadges] = useState([]);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");


    // =====================================================
    // LOAD REWARDS
    // =====================================================

    useEffect(() => {

        const loadRewards = async () => {

            try {

                setLoading(true);
                setError("");


                const [
                    userData,
                    rewardData,
                    historyData,
                    badgeData,
                ] = await Promise.all([

                    getCurrentUser(),

                    getRewardSummary(),

                    getCreditHistory(),

                    getCitizenBadges(),

                ]);


                setUser(userData);

                setSummary(
                    rewardData || null
                );

                setHistory(
                    Array.isArray(historyData)
                        ? historyData
                        : []
                );

                setBadges(
                    Array.isArray(badgeData)
                        ? badgeData
                        : []
                );

            } catch (err) {

                console.error(
                    "Rewards loading error:",
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
                    "Unable to load your rewards."
                );

            } finally {

                setLoading(false);

            }

        };


        loadRewards();

    }, [navigate]);


    // =====================================================
    // VALUES
    // =====================================================

    const credits =
        Number(summary?.credits) || 0;


    const level =
        summary?.level ||
        "Civic Observer";


    const levelStart =
        Number(summary?.level_start) || 0;


    const levelTarget =
        Number(summary?.level_target) || 100;


    const progress =
        Number(summary?.progress) || 0;


    const earnedBadges =
        badges.filter(
            (badge) => badge.earned
        ).length;


    const totalBadgeCount =
        badges.length;


    // =====================================================
    // NEXT LEVEL
    // =====================================================

    const nextLevel =
        level === "Civic Observer"
            ? "Civic Contributor"
            : level === "Civic Contributor"
                ? "Civic Champion"
                : level === "Civic Champion"
                    ? "Civic Leader"
                    : level === "Civic Leader"
                        ? "Civic Ambassador"
                        : "Maximum Level";


    const creditsRemaining =
        Math.max(
            0,
            levelTarget - credits
        );


    // =====================================================
    // FORMAT DATE
    // =====================================================

    const formatDate = (dateValue) => {

        if (!dateValue) {
            return "Recently";
        }


        const date = new Date(dateValue);


        if (Number.isNaN(date.getTime())) {
            return "Recently";
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
    // LOADING
    // =====================================================

    if (loading) {

        return (

            <main className="rewards-page">

                <div className="rewards-loading">

                    <Sparkles size={28} />

                    <p>
                        Loading your civic rewards...
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

            <main className="rewards-page">

                <div className="rewards-error">

                    <ShieldCheck size={32} />

                    <h2>
                        Unable to load rewards
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
    // PAGE
    // =====================================================

    return (

        <main className="rewards-page">

            {/* =================================================
                PAGE HEADER
            ================================================= */}

            <section className="rewards-header">

                <div>

                    <Link
                        to="/citizen-dashboard"
                        className="back-link"
                    >

                        <ArrowLeft size={16} />

                        Dashboard

                    </Link>


                    <p className="rewards-eyebrow">

                        CIVIC REWARDS CENTER

                    </p>


                    <h1>
                        Your Civic Impact
                    </h1>


                    <p className="rewards-subtitle">

                        Every verified contribution helps
                        build a more responsive city.

                    </p>

                </div>


                <div className="rewards-user-chip">

                    <div className="rewards-user-avatar">

                        <User size={19} />

                    </div>


                    <div>

                        <strong>
                            {user?.name || "Citizen"}
                        </strong>

                        <span>
                            {user?.citizen_id || "CIVIC"}
                        </span>

                    </div>

                </div>

            </section>


            {/* =================================================
                HERO REWARD CARD
            ================================================= */}

            <section className="rewards-hero">

                <div className="rewards-hero-content">

                    <div className="credits-symbol">

                        <Award size={30} />

                    </div>


                    <p>
                        CIVIC CREDITS
                    </p>


                    <h2>
                        {credits}
                    </h2>


                    <span>
                        Contribution points earned
                    </span>

                </div>


                <div className="hero-divider" />


                <div className="rewards-level">

                    <div className="level-icon">

                        <Trophy size={25} />

                    </div>


                    <div>

                        <span>
                            CURRENT LEVEL
                        </span>

                        <strong>
                            {level}
                        </strong>

                    </div>

                </div>

            </section>


            {/* =================================================
                PROGRESS
            ================================================= */}

            <section className="reward-progress-card">

                <div className="reward-progress-header">

                    <div>

                        <span>
                            LEVEL PROGRESS
                        </span>

                        <h2>
                            {level}
                        </h2>

                    </div>


                    <div className="progress-number">

                        <strong>
                            {Math.round(progress)}%
                        </strong>

                        <span>
                            complete
                        </span>

                    </div>

                </div>


                <div className="reward-progress-track">

                    <div
                        className="reward-progress-value"
                        style={{
                            width: `${progress}%`,
                        }}
                    />

                </div>


                <div className="reward-progress-footer">

                    <span>

                        {credits} credits

                    </span>


                    <span>

                        {creditsRemaining > 0
                            ? `${creditsRemaining} credits to ${nextLevel}`
                            : "Level milestone reached"}

                    </span>

                </div>

            </section>


            {/* =================================================
                QUICK STATS
            ================================================= */}

            <section className="reward-stat-grid">


                <div className="reward-stat-card">

                    <div className="reward-stat-icon blue">

                        <Zap size={20} />

                    </div>


                    <div>

                        <span>
                            Total Credits
                        </span>

                        <strong>
                            {credits}
                        </strong>

                    </div>

                </div>


                <div className="reward-stat-card">

                    <div className="reward-stat-icon gold">

                        <BadgeCheck size={20} />

                    </div>


                    <div>

                        <span>
                            Badges Earned
                        </span>

                        <strong>
                            {earnedBadges}
                        </strong>

                    </div>

                </div>


                <div className="reward-stat-card">

                    <div className="reward-stat-icon green">

                        <TrendingUp size={20} />

                    </div>


                    <div>

                        <span>
                            Contributions
                        </span>

                        <strong>
                            {history.length}
                        </strong>

                    </div>

                </div>


                <div className="reward-stat-card">

                    <div className="reward-stat-icon purple">

                        <Flame size={20} />

                    </div>


                    <div>

                        <span>
                            Civic Level
                        </span>

                        <strong>
                            {level}
                        </strong>

                    </div>

                </div>

            </section>


            {/* =================================================
                MAIN GRID
            ================================================= */}

            <section className="rewards-content-grid">


                {/* =================================================
                    BADGES
                ================================================= */}

                <article className="badges-card">

                    <div className="rewards-section-header">

                        <div>

                            <p>
                                ACHIEVEMENTS
                            </p>

                            <h2>
                                Civic Badges
                            </h2>

                        </div>


                        <Award size={21} />

                    </div>


                    <div className="badge-grid">

                        {badges.length === 0 ? (

                            <div className="no-badges">

                                <Award size={30} />

                                <p>
                                    No badges available yet.
                                </p>

                            </div>

                        ) : (

                            badges.map(
                                (badge) => (

                                    <div
                                        className={
                                            `badge-item ${badge.earned
                                                ? "earned"
                                                : "locked"
                                            }`
                                        }
                                        key={badge.id}
                                    >

                                        <div className="badge-icon">

                                            <Award size={22} />

                                            {!badge.earned && (
                                                <span>
                                                    ?
                                                </span>
                                            )}

                                        </div>


                                        <div className="badge-info">

                                            <strong>
                                                {badge.name}
                                            </strong>

                                            <span>
                                                {badge.description}
                                            </span>


                                            {badge.earned ? (

                                                <small>
                                                    <CheckCircle2
                                                        size={12}
                                                    />

                                                    Earned
                                                </small>

                                            ) : (

                                                <small>
                                                    Locked
                                                </small>

                                            )}

                                        </div>

                                    </div>

                                )
                            )

                        )}

                    </div>


                    {totalBadgeCount > 0 && (

                        <div className="badge-summary">

                            <ShieldCheck size={15} />

                            {earnedBadges} of{" "}
                            {totalBadgeCount} badges earned

                        </div>

                    )}

                </article>


                {/* =================================================
                    CREDIT HISTORY
                ================================================= */}

                <article className="history-card">

                    <div className="rewards-section-header">

                        <div>

                            <p>
                                ACTIVITY
                            </p>

                            <h2>
                                Contribution History
                            </h2>

                        </div>


                        <History size={21} />

                    </div>


                    {history.length === 0 ? (

                        <div className="empty-history">

                            <Clock3 size={30} />

                            <h3>
                                No contributions yet
                            </h3>

                            <p>

                                Submit a verified civic
                                report to start earning
                                Civic Credits.

                            </p>


                            <Link to="/report">

                                Report an Issue

                                <ArrowRight size={15} />

                            </Link>

                        </div>

                    ) : (

                        <div className="history-list">

                            {history.map(
                                (transaction) => {

                                    const positive =
                                        Number(
                                            transaction.credits
                                        ) >= 0;


                                    return (

                                        <div
                                            className="history-row"
                                            key={
                                                transaction.id
                                            }
                                        >

                                            <div
                                                className={
                                                    `history-icon ${positive
                                                        ? "positive"
                                                        : "negative"
                                                    }`
                                                }
                                            >

                                                {positive ? (
                                                    <TrendingUp
                                                        size={17}
                                                    />
                                                ) : (
                                                    <XCircle
                                                        size={17}
                                                    />
                                                )}

                                            </div>


                                            <div className="history-details">

                                                <strong>

                                                    {transaction.description ||
                                                        transaction.action ||
                                                        "Civic contribution"}

                                                </strong>


                                                <span>

                                                    <CalendarDays
                                                        size={12}
                                                    />

                                                    {formatDate(
                                                        transaction.created_at
                                                    )}

                                                    {transaction.issue_id && (
                                                        <>
                                                            {" • "}
                                                            Issue #
                                                            {
                                                                transaction.issue_id
                                                            }
                                                        </>
                                                    )}

                                                </span>

                                            </div>


                                            <strong
                                                className={
                                                    `history-credits ${positive
                                                        ? "positive"
                                                        : "negative"
                                                    }`
                                                }
                                            >

                                                {positive
                                                    ? "+"
                                                    : ""}

                                                {
                                                    transaction.credits
                                                }

                                            </strong>

                                        </div>

                                    );

                                }
                            )}

                        </div>

                    )}

                </article>

            </section>


            {/* =================================================
                LEVEL GUIDE
            ================================================= */}

            <section className="level-guide">

                <div className="rewards-section-header">

                    <div>

                        <p>
                            CIVIC PROGRESSION
                        </p>

                        <h2>
                            Contribution Levels
                        </h2>

                    </div>


                    <Target size={21} />

                </div>


                <div className="level-guide-grid">


                    <div
                        className={
                            `level-guide-item ${level === "Civic Observer"
                                ? "active"
                                : ""
                            }`
                        }
                    >

                        <div>
                            <Star size={18} />
                        </div>

                        <strong>
                            Civic Observer
                        </strong>

                        <span>
                            0 – 99 credits
                        </span>

                    </div>


                    <div
                        className={
                            `level-guide-item ${level === "Civic Contributor"
                                ? "active"
                                : ""
                            }`
                        }
                    >

                        <div>
                            <BadgeCheck size={18} />
                        </div>

                        <strong>
                            Civic Contributor
                        </strong>

                        <span>
                            100 – 249 credits
                        </span>

                    </div>


                    <div
                        className={
                            `level-guide-item ${level === "Civic Champion"
                                ? "active"
                                : ""
                            }`
                        }
                    >

                        <div>
                            <Trophy size={18} />
                        </div>

                        <strong>
                            Civic Champion
                        </strong>

                        <span>
                            250 – 499 credits
                        </span>

                    </div>


                    <div
                        className={
                            `level-guide-item ${level === "Civic Leader"
                                ? "active"
                                : ""
                            }`
                        }
                    >

                        <div>
                            <TrendingUp size={18} />
                        </div>

                        <strong>
                            Civic Leader
                        </strong>

                        <span>
                            500 – 999 credits
                        </span>

                    </div>


                    <div
                        className={
                            `level-guide-item ${level === "Civic Ambassador"
                                ? "active"
                                : ""
                            }`
                        }
                    >

                        <div>
                            <Sparkles size={18} />
                        </div>

                        <strong>
                            Civic Ambassador
                        </strong>

                        <span>
                            1000+ credits
                        </span>

                    </div>

                </div>

            </section>


            {/* =================================================
                CTA
            ================================================= */}

            <section className="rewards-cta">

                <div>

                    <Sparkles size={25} />

                    <div>

                        <h2>
                            Keep contributing to your city.
                        </h2>

                        <p>

                            Every verified report,
                            accurate location and useful
                            civic contribution helps create
                            measurable impact.

                        </p>

                    </div>

                </div>


                <Link
                    to="/report"
                    className="rewards-cta-button"
                >

                    Report an Issue

                    <ArrowRight size={17} />

                </Link>

            </section>

        </main>

    );

};


export default Rewards;