import {
    ArrowRight,
    CheckCircle2,
    Map,
    MapPin,
    ShieldCheck,
    Sparkles,
    TrendingUp,
} from "lucide-react";

import { Link } from "react-router-dom";

import "./Home.css";


function Home() {
    return (
        <main className="home-page">

            {/* =====================================================
          HERO SECTION
      ===================================================== */}

            <section className="hero-section">

                <div className="hero-container">

                    {/* LEFT SIDE */}

                    <div className="hero-content">

                        <div className="hero-badge">
                            <Sparkles size={17} />
                            <span>AI-POWERED CIVIC INTELLIGENCE</span>
                        </div>


                        <h1 className="hero-title">

                            <span className="hero-title-line">
                                Turning Citizen
                            </span>

                            <span className="hero-title-line">
                                Reports
                            </span>

                            <span className="hero-title-line hero-title-accent">
                                Into Civic
                            </span>

                            <span className="hero-title-line hero-title-accent">
                                Intelligence.
                            </span>

                        </h1>


                        <p className="hero-description">

                            CIVICSOL transforms real-world civic problems
                            into structured, location-aware and AI-assisted
                            intelligence for faster and smarter city response.

                        </p>


                        <div className="hero-actions">

                            <Link
                                to="/report"
                                className="hero-primary-button"
                            >
                                <span>Report a Civic Issue</span>
                                <ArrowRight size={20} />
                            </Link>


                            <Link
                                to="/map"
                                className="hero-secondary-button"
                            >
                                <span>Explore Civic Map</span>
                                <MapPin size={19} />
                            </Link>

                        </div>


                        <div className="hero-features">

                            <div className="hero-feature">

                                <CheckCircle2 size={17} />

                                <span>
                                    AI-Assisted Analysis
                                </span>

                            </div>


                            <div className="hero-feature">

                                <MapPin size={17} />

                                <span>
                                    GPS Location Evidence
                                </span>

                            </div>


                            <div className="hero-feature">

                                <ShieldCheck size={17} />

                                <span>
                                    Secure Reporting
                                </span>

                            </div>


                            <div className="hero-feature">

                                <TrendingUp size={17} />

                                <span>
                                    24/7 Civic Monitoring
                                </span>

                            </div>

                        </div>

                    </div>


                    {/* RIGHT SIDE — CIVIC INTELLIGENCE CARD */}

                    <div className="hero-monitor">

                        <div className="monitor-header">

                            <div>

                                <span className="monitor-label">
                                    CIVICSOL INTELLIGENCE
                                </span>

                                <h2>
                                    City Issue Monitor
                                </h2>

                            </div>


                            <div className="live-indicator">

                                <span className="live-dot"></span>

                                LIVE

                            </div>

                        </div>


                        <div className="monitor-divider"></div>


                        {/* SCORE */}

                        <div className="monitor-score-row">

                            <div className="score-circle">

                                <div className="score-inner">

                                    <strong>
                                        87
                                    </strong>

                                    <span>
                                        AI SCORE
                                    </span>

                                </div>

                            </div>


                            <div className="score-information">

                                <span>
                                    CURRENT PRIORITY
                                </span>

                                <h3>
                                    High Impact Area
                                </h3>

                                <p>
                                    Multiple reports detected within
                                    the same location.
                                </p>

                            </div>

                        </div>


                        {/* ISSUE LIST */}

                        <div className="monitor-issues">


                            <div className="monitor-issue">

                                <div className="issue-number">
                                    01
                                </div>

                                <div className="issue-content">

                                    <strong>
                                        Road Damage
                                    </strong>

                                    <span>
                                        12 citizen reports
                                    </span>

                                </div>

                                <span className="issue-priority high">
                                    HIGH
                                </span>

                            </div>


                            <div className="monitor-issue">

                                <div className="issue-number">
                                    02
                                </div>

                                <div className="issue-content">

                                    <strong>
                                        Garbage Accumulation
                                    </strong>

                                    <span>
                                        8 citizen reports
                                    </span>

                                </div>

                                <span className="issue-priority medium">
                                    MED
                                </span>

                            </div>


                            <div className="monitor-issue">

                                <div className="issue-number">
                                    03
                                </div>

                                <div className="issue-content">

                                    <strong>
                                        Street Light
                                    </strong>

                                    <span>
                                        5 citizen reports
                                    </span>

                                </div>

                                <span className="issue-priority low">
                                    LOW
                                </span>

                            </div>


                        </div>


                        <div className="monitor-footer">

                            <div>

                                <span className="status-dot"></span>

                                <span>
                                    Spatial analysis active
                                </span>

                            </div>


                            <span>
                                Priority engine ready
                            </span>

                        </div>

                    </div>

                </div>

            </section>



            {/* =====================================================
          CTA SECTION
      ===================================================== */}

            <section className="home-cta">

                <div className="cta-glow"></div>


                <div className="cta-content">

                    <span className="cta-label">
                        BUILDING SMARTER CITIES
                    </span>


                    <h2>

                        See a civic problem?

                        <br />

                        <span>
                            Report it.
                        </span>

                    </h2>


                    <p>

                        One verified citizen report can become part
                        of a larger intelligence network helping cities
                        understand what needs attention.

                    </p>


                    <Link
                        to="/report"
                        className="cta-button"
                    >

                        <span>
                            Report an Issue
                        </span>

                        <ArrowRight size={20} />

                    </Link>

                </div>


                <div className="cta-visual">

                    <div className="cta-ring ring-one"></div>

                    <div className="cta-ring ring-two"></div>

                    <div className="cta-ring ring-three"></div>


                    <div className="cta-icon">

                        <ShieldCheck size={34} />

                    </div>

                </div>

            </section>

        </main>
    );
}


export default Home;