import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
    UserPlus,
    User,
    Phone,
    Mail,
    Lock,
    Languages,
    ShieldCheck,
    ArrowRight,
    CheckCircle2,
} from "lucide-react";

import api from "../services/api";
import "./Signup.css";


const Signup = () => {
    const navigate = useNavigate();

    const [form, setForm] = useState({
        name: "",
        mobile: "",
        email: "",
        password: "",
        preferred_language: "English",
    });

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState(null);


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

        if (form.password.length < 8) {
            setError("Password must contain at least 8 characters.");
            return;
        }

        setLoading(true);

        try {
            const response = await api.post("/auth/signup", {
                name: form.name.trim(),
                mobile: form.mobile.trim(),
                email: form.email.trim() || null,
                password: form.password,
                preferred_language: form.preferred_language,
            });

            setSuccess(response.data);

        } catch (err) {
            const message =
                err.response?.data?.detail ||
                "Unable to create your account. Please try again.";

            setError(message);

        } finally {
            setLoading(false);
        }
    };


    if (success) {
        return (
            <main className="signup-page">
                <section className="signup-success-card">

                    <div className="success-icon">
                        <CheckCircle2 size={48} />
                    </div>

                    <p className="success-label">
                        ACCOUNT CREATED
                    </p>

                    <h1>
                        Welcome to <span>CIVICSOL</span>
                    </h1>

                    <p className="success-message">
                        Your citizen account has been successfully created.
                    </p>

                    <div className="citizen-id-card">
                        <span>Your Citizen ID</span>
                        <strong>{success.citizen_id}</strong>
                    </div>

                    <p className="save-id-text">
                        Keep your Citizen ID safe. You can use it to identify
                        your CIVICSOL citizen account.
                    </p>

                    <button
                        className="primary-button"
                        onClick={() => navigate("/signin")}
                    >
                        Continue to Sign In
                        <ArrowRight size={18} />
                    </button>

                </section>
            </main>
        );
    }


    return (
        <main className="signup-page">

            <div className="signup-background-glow glow-one" />
            <div className="signup-background-glow glow-two" />

            <section className="signup-container">

                {/* LEFT PANEL */}

                <div className="signup-info">

                    <div className="brand-mark">
                        <div className="brand-icon">
                            <ShieldCheck size={25} />
                        </div>

                        <div>
                            <strong>CIVICSOL</strong>
                            <span>Civic Intelligence Platform</span>
                        </div>
                    </div>

                    <div className="signup-info-content">

                        <p className="eyebrow">
                            JOIN THE CIVIC NETWORK
                        </p>

                        <h1>
                            Make your city
                            <span> better.</span>
                        </h1>

                        <p className="signup-description">
                            Create your citizen account and help transform
                            everyday civic observations into actionable
                            intelligence for the city.
                        </p>

                        <div className="signup-benefits">

                            <div className="benefit">
                                <CheckCircle2 size={19} />
                                <span>Report civic issues with image & GPS evidence</span>
                            </div>

                            <div className="benefit">
                                <CheckCircle2 size={19} />
                                <span>Track your reported issues</span>
                            </div>

                            <div className="benefit">
                                <CheckCircle2 size={19} />
                                <span>Earn Civic Credits for meaningful contributions</span>
                            </div>

                            <div className="benefit">
                                <CheckCircle2 size={19} />
                                <span>Build your civic contribution profile</span>
                            </div>

                        </div>

                    </div>

                    <div className="signup-security">
                        <ShieldCheck size={17} />

                        <span>
                            Your account credentials are securely protected.
                        </span>
                    </div>

                </div>


                {/* FORM PANEL */}

                <div className="signup-form-card">

                    <div className="form-header">

                        <div className="form-icon">
                            <UserPlus size={24} />
                        </div>

                        <div>
                            <p className="form-eyebrow">
                                CITIZEN REGISTRATION
                            </p>

                            <h2>
                                Create your account
                            </h2>

                            <p>
                                Join CIVICSOL as a citizen contributor.
                            </p>
                        </div>

                    </div>


                    {error && (
                        <div className="form-error">
                            {error}
                        </div>
                    )}


                    <form onSubmit={handleSubmit}>

                        {/* NAME */}

                        <div className="input-group">

                            <label htmlFor="name">
                                Full Name
                            </label>

                            <div className="input-wrapper">
                                <User size={18} />

                                <input
                                    id="name"
                                    name="name"
                                    type="text"
                                    placeholder="Enter your full name"
                                    value={form.name}
                                    onChange={handleChange}
                                    required
                                    autoComplete="name"
                                />
                            </div>

                        </div>


                        {/* MOBILE */}

                        <div className="input-group">

                            <label htmlFor="mobile">
                                Mobile Number
                            </label>

                            <div className="input-wrapper">
                                <Phone size={18} />

                                <input
                                    id="mobile"
                                    name="mobile"
                                    type="tel"
                                    inputMode="numeric"
                                    maxLength={10}
                                    placeholder="10-digit mobile number"
                                    value={form.mobile}
                                    onChange={handleChange}
                                    required
                                    autoComplete="tel"
                                />
                            </div>

                        </div>


                        {/* EMAIL */}

                        <div className="input-group">

                            <label htmlFor="email">
                                Email
                                <span className="optional">
                                    Optional
                                </span>
                            </label>

                            <div className="input-wrapper">
                                <Mail size={18} />

                                <input
                                    id="email"
                                    name="email"
                                    type="email"
                                    placeholder="you@example.com"
                                    value={form.email}
                                    onChange={handleChange}
                                    autoComplete="email"
                                />
                            </div>

                        </div>


                        {/* PASSWORD */}

                        <div className="input-group">

                            <label htmlFor="password">
                                Password
                            </label>

                            <div className="input-wrapper">
                                <Lock size={18} />

                                <input
                                    id="password"
                                    name="password"
                                    type="password"
                                    placeholder="Minimum 8 characters"
                                    value={form.password}
                                    onChange={handleChange}
                                    required
                                    autoComplete="new-password"
                                />
                            </div>

                        </div>


                        {/* LANGUAGE */}

                        <div className="input-group">

                            <label htmlFor="preferred_language">
                                Preferred Language
                            </label>

                            <div className="input-wrapper">
                                <Languages size={18} />

                                <select
                                    id="preferred_language"
                                    name="preferred_language"
                                    value={form.preferred_language}
                                    onChange={handleChange}
                                >
                                    <option value="English">English</option>
                                    <option value="Gujarati">Gujarati</option>
                                    <option value="Hindi">Hindi</option>
                                </select>
                            </div>

                        </div>


                        <button
                            type="submit"
                            className="signup-button"
                            disabled={loading}
                        >
                            {loading ? (
                                "Creating Account..."
                            ) : (
                                <>
                                    Create Citizen Account
                                    <ArrowRight size={18} />
                                </>
                            )}
                        </button>

                    </form>


                    <div className="signin-link">

                        Already have an account?

                        <Link to="/signin">
                            Sign in
                        </Link>

                    </div>


                    <div className="form-footer">

                        <ShieldCheck size={16} />

                        <span>
                            Secure citizen authentication
                        </span>

                    </div>

                </div>

            </section>

        </main>
    );
};


export default Signup;