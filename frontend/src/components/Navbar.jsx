import { Link, NavLink, useNavigate } from "react-router-dom";

import {
    ShieldCheck,
    LayoutDashboard,
    Map,
    FileWarning,
    ChevronRight,
    UserCircle,
    LogOut,
} from "lucide-react";

import api from "../services/api";
import NotificationCenter from "./NotificationCenter";

import "./Navbar.css";


function Navbar() {
    const navigate = useNavigate();

    // ===============================
    // AUTHENTICATION
    // ===============================

    const token = localStorage.getItem(
        "civicsol_access_token"
    );

    const citizenData = localStorage.getItem(
        "civicsol_citizen"
    );

    let userName = "Citizen";

    if (citizenData) {
        try {
            const citizen = JSON.parse(citizenData);

            userName = citizen.name || "Citizen";
        } catch {
            userName = "Citizen";
        }
    }

    const isAuthenticated = Boolean(token);


    // ===============================
    // LOGOUT
    // ===============================

    const handleLogout = () => {

        localStorage.removeItem(
            "civicsol_access_token"
        );

        localStorage.removeItem(
            "civicsol_citizen"
        );

        delete api.defaults.headers.common.Authorization;

        navigate("/signin", {
            replace: true,
        });
    };


    return (
        <header className="navbar">

            <div className="navbar-container">


                {/* =================================================
                    LOGO
                ================================================= */}

                <Link
                    to="/"
                    className="navbar-brand"
                >

                    <div className="brand-icon">

                        <ShieldCheck
                            size={23}
                            strokeWidth={2.2}
                        />

                    </div>


                    <div className="brand-text">

                        <span className="brand-name">
                            CIVICSOL
                        </span>

                        <span className="brand-tagline">
                            CIVIC INTELLIGENCE
                        </span>

                    </div>

                </Link>



                {/* =================================================
                    NAVIGATION
                ================================================= */}

                <nav className="navbar-links">


                    {/* HOME
                        Visible for everyone
                    */}

                    <NavLink
                        to="/"
                        end
                        className={({ isActive }) =>
                            `nav-link ${isActive ? "active" : ""
                            }`
                        }
                    >
                        Home
                    </NavLink>



                    {/* =================================================
                        AUTHENTICATED NAVIGATION
                    ================================================= */}

                    {isAuthenticated && (
                        <>


                            {/* LIVE MAP */}

                            <NavLink
                                to="/map"
                                className={({ isActive }) =>
                                    `nav-link ${isActive ? "active" : ""
                                    }`
                                }
                            >

                                <Map size={16} />

                                <span>
                                    Live Map
                                </span>

                            </NavLink>



                            {/* COMMAND CENTER */}

                            <NavLink
                                to="/dashboard"
                                className={({ isActive }) =>
                                    `nav-link ${isActive ? "active" : ""
                                    }`
                                }
                            >

                                <LayoutDashboard size={16} />

                                <span>
                                    Command Center
                                </span>

                            </NavLink>

                        </>
                    )}

                </nav>



                {/* =================================================
                    RIGHT SIDE
                ================================================= */}

                <div className="navbar-actions">


                    {/* =================================================
                        LOGGED-IN CITIZEN
                    ================================================= */}

                    {isAuthenticated ? (
                        <>


                            {/* REPORT ISSUE */}

                            <Link
                                to="/report"
                                className="report-button"
                            >

                                <FileWarning size={17} />

                                <span>
                                    Report Issue
                                </span>

                                <ChevronRight size={16} />

                            </Link>



                            {/* NOTIFICATION CENTER */}
                            <NotificationCenter isAuthority={false} />

                            {/* =================================================
                                CITIZEN PROFILE
                            ================================================= */}

                            <button
                                type="button"
                                className="navbar-profile"
                                onClick={() =>
                                    navigate("/profile")
                                }
                                title="Open profile"
                            >

                                <UserCircle size={21} />

                                <span className="navbar-profile-name">
                                    {userName}
                                </span>

                            </button>



                            {/* =================================================
                                LOGOUT
                            ================================================= */}

                            <button
                                type="button"
                                className="navbar-logout"
                                onClick={handleLogout}
                                title="Logout"
                                aria-label="Logout"
                            >

                                <LogOut size={18} />

                            </button>

                        </>

                    ) : (


                        /* =================================================
                            LOGGED-OUT USER
                        ================================================= */

                        <div className="navbar-auth-buttons">


                            {/* SIGN IN */}

                            <Link
                                to="/signin"
                                className="navbar-signin"
                            >
                                Sign In
                            </Link>



                            {/* SIGN UP */}

                            <Link
                                to="/signup"
                                className="navbar-signup"
                            >
                                Sign Up
                            </Link>


                        </div>

                    )}

                </div>

            </div>

        </header>
    );
}


export default Navbar;