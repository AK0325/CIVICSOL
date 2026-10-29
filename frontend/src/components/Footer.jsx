import {
    ShieldCheck,
    Mail,
    ArrowUpRight,
    GitBranch,
    BriefcaseBusiness,
} from "lucide-react";

import "./Footer.css";

function Footer() {
    return (
        <footer className="site-footer">

            {/* =========================================
          FOOTER MAIN
      ========================================== */}

            <div className="footer-container">

                {/* BRAND */}

                <div className="footer-brand">

                    <div className="footer-logo-row">

                        <div className="footer-logo-icon">
                            <ShieldCheck size={22} />
                        </div>

                        <div>
                            <div className="footer-logo-text">
                                CIVICSOL
                            </div>

                            <div className="footer-logo-subtitle">
                                CIVIC INTELLIGENCE
                            </div>
                        </div>

                    </div>


                    <p className="footer-description">
                        AI-powered civic intelligence for smarter,
                        faster, and more responsive cities.
                    </p>


                    <div className="footer-status">

                        <span className="status-dot"></span>

                        CIVIC INTELLIGENCE NETWORK ONLINE

                    </div>

                </div>


                {/* PLATFORM */}

                <div className="footer-column">

                    <h3>Platform</h3>

                    <a href="/">
                        Home
                    </a>

                    <a href="/report">
                        Report an Issue
                    </a>

                    <a href="/map">
                        Civic Map
                    </a>

                    <a href="/dashboard">
                        Command Center
                    </a>

                </div>


                {/* INTELLIGENCE */}

                <div className="footer-column">

                    <h3>Intelligence</h3>

                    <a href="/dashboard">
                        AI Issue Detection
                    </a>

                    <a href="/dashboard">
                        Issue Classification
                    </a>

                    <a href="/dashboard">
                        Priority Analysis
                    </a>

                    <a href="/map">
                        Civic Hotspot Detection
                    </a>

                </div>


                {/* CONNECT */}

                <div className="footer-column">

                    <h3>Connect</h3>

                    <a
                        href="https://github.com"
                        target="_blank"
                        rel="noreferrer"
                    >
                        <GitBranch size={15} />
                        GitHub
                        <ArrowUpRight size={13} />
                    </a>


                    <a
                        href="https://linkedin.com"
                        target="_blank"
                        rel="noreferrer"
                    >
                        <BriefcaseBusiness size={15} />
                        LinkedIn
                        <ArrowUpRight size={13} />
                    </a>


                    <a href="mailto:contact@civicsol.ai">
                        <Mail size={15} />
                        Contact
                        <ArrowUpRight size={13} />
                    </a>

                </div>

            </div>


            {/* =========================================
          FOOTER BOTTOM
      ========================================== */}

            <div className="footer-bottom">

                <div className="footer-bottom-container">

                    <div className="footer-copyright">
                        © 2026 CIVICSOL. All rights reserved.
                    </div>


                    <div className="footer-credit">
                        Designed &amp; Developed by{" "}
                        <strong>
                            Ankit Kumar &amp; Team CIVICSOL
                        </strong>
                    </div>


                    <div className="footer-tech">
                        Built with
                        <span>AI</span>
                        <b>•</b>
                        FastAPI
                        <b>•</b>
                        React
                        <b>•</b>
                        PostgreSQL
                    </div>

                </div>

            </div>

        </footer>
    );
}

export default Footer;