import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
    ShieldCheck,
    Phone,
    Lock,
    ArrowRight,
    LogIn,
    CheckCircle2,
} from "lucide-react";

import api from "../services/api";
import "./Signin.css";

const Signin = () => {
    const navigate = useNavigate();

    const [form, setForm] = useState({
        mobile: "",
        password: "",
    });

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const handleChange = (event) => {
        const { name, value } = event.target;

        setForm((previous) => ({
            ...previous,
            [name]: value,
        }));
    };

    const handleSubmit = async (event) => {
        event.preventDefault();

        setError("");

        if (form.mobile.length !== 10) {
            setError("Please enter a valid 10-digit mobile number.");
            return;
        }

        if (!form.password) {
            setError("Please enter your password.");
            return;
        }

        setLoading(true);

        try {
            const response = await api.post("/auth/signin", {
                mobile: form.mobile.trim(),
                password: form.password,
            });

            const data = response.data;

            localStorage.setItem(
                "civicsol_access_token",
                data.access_token
            );

            localStorage.setItem(
                "civicsol_citizen",
                JSON.stringify({
                    citizen_id: data.citizen_id,
                    name: data.name,
                })
            );

            api.defaults.headers.common.Authorization =
                `Bearer ${data.access_token}`;

            navigate("/citizen-dashboard");

        } catch (err) {
            const message =
                err.response?.data?.detail ||
                "Unable to sign in. Please check your credentials.";

            setError(message);

        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="signin-page">

            <div className="signin-glow signin-glow-one" />
            <div className="signin-glow signin-glow-two" />

            <section className="signin-container">

                {/* LEFT SIDE */}

                <div className="signin-info">

                    <div className="signin-brand">

                        <div className="signin-brand-icon">
                            <ShieldCheck size={25} />
                        </div>

                        <div>
                            <strong>CIVICSOL</strong>
                            <span>Civic Intelligence Platform</span>
                        </div>

                    </div>

                    <div className="signin-hero">

                        <p className="signin-eyebrow">
                            CITIZEN PORTAL
                        </p>

                        <h1>
                            Welcome
                            <span> back.</span>
                        </h1>

                        <p>
                            Continue contributing to a smarter,
                            more responsive city.
                        </p>

                        <div className="signin-points">

                            <div>
                                <CheckCircle2 size={18} />
                                <span>Track your civic reports</span>
                            </div>

                            <div>
                                <CheckCircle2 size={18} />
                                <span>Monitor issue resolution</span>
                            </div>

                            <div>
                                <CheckCircle2 size={18} />
                                <span>Earn Civic Credits</span>
                            </div>

                            <div>
                                <CheckCircle2 size={18} />
                                <span>Build your civic contribution</span>
                            </div>

                        </div>

                    </div>

                    <div className="signin-security">

                        <ShieldCheck size={17} />

                        <span>
                            Secure citizen authentication
                        </span>

                    </div>

                </div>


                {/* LOGIN FORM */}

                <div className="signin-form-card">

                    <div className="signin-form-header">

                        <div className="signin-form-icon">
                            <LogIn size={23} />
                        </div>

                        <div>

                            <p>
                                CITIZEN SIGN IN
                            </p>

                            <h2>
                                Access your account
                            </h2>

                            <span>
                                Sign in to continue to your dashboard.
                            </span>

                        </div>

                    </div>


                    {error && (
                        <div className="signin-error">
                            {error}
                        </div>
                    )}


                    <form onSubmit={handleSubmit}>

                        {/* MOBILE */}

                        <div className="signin-input-group">

                            <label htmlFor="mobile">
                                Mobile Number
                            </label>

                            <div className="signin-input">

                                <Phone size={18} />

                                <input
                                    id="mobile"
                                    name="mobile"
                                    type="tel"
                                    inputMode="numeric"
                                    maxLength={10}
                                    placeholder="Enter your mobile number"
                                    value={form.mobile}
                                    onChange={handleChange}
                                    required
                                    autoComplete="tel"
                                />

                            </div>

                        </div>


                        {/* PASSWORD */}

                        <div className="signin-input-group">

                            <label htmlFor="password">
                                Password
                            </label>

                            <div className="signin-input">

                                <Lock size={18} />

                                <input
                                    id="password"
                                    name="password"
                                    type="password"
                                    placeholder="Enter your password"
                                    value={form.password}
                                    onChange={handleChange}
                                    required
                                    autoComplete="current-password"
                                />

                            </div>

                        </div>


                        {/* FORGOT PASSWORD */}

                        <div className="forgot-password-wrapper">

                            <button
                                type="button"
                                className="forgot-password-link"
                                onClick={() =>
                                    navigate("/forgot-password")
                                }
                            >
                                Forgot Password?
                            </button>

                        </div>


                        {/* SIGN IN BUTTON */}

                        <button
                            type="submit"
                            className="signin-button"
                            disabled={loading}
                        >

                            {loading ? (
                                "Signing In..."
                            ) : (
                                <>
                                    Sign In
                                    <ArrowRight size={18} />
                                </>
                            )}

                        </button>

                    </form>


                    {/* SIGN UP */}

                    <div className="signup-prompt">

                        Don't have a CIVICSOL account?

                        <Link to="/signup">
                            Create account
                        </Link>

                    </div>


                    <div className="signin-form-footer">

                        <span>
                            CIVICSOL Citizen Portal
                        </span>

                        <span>•</span>

                        <span>
                            Secure Access
                        </span>

                    </div>

                </div>

            </section>

        </main>
    );
};

export default Signin;