import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Lock, Loader2, ShieldCheck, UserCheck } from "lucide-react";
import { loginAuthority } from "../../services/authorityApi";
import "./AuthorityLogin.css";

export default function AuthorityLogin() {
    const navigate = useNavigate();

    const [identifier, setIdentifier] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");

        if (!identifier.trim() || !password) {
            setError("Please enter both your official identifier and password.");
            return;
        }

        try {
            setLoading(true);
            await loginAuthority({
                identifier: identifier.trim(),
                password,
            });
            navigate("/authority/dashboard", { replace: true });
        } catch (err) {
            const detail = err.response?.data?.detail;
            if (typeof detail === "string") {
                setError(detail);
            } else {
                setError("Authentication failed. Please verify your credentials and active authority status.");
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="authority-login-wrapper">
            <div className="authority-login-card">
                <div className="authority-login-header">
                    <div className="authority-login-badge">
                        <ShieldCheck size={14} />
                        <span>MUNICIPAL OPERATIONS</span>
                    </div>
                    <h1 className="authority-login-title">Authority Portal</h1>
                    <p className="authority-login-subtitle">
                        Sign in with your Employee ID, Official Email, or Mobile
                    </p>
                </div>

                {error && <div className="authority-error-banner">{error}</div>}

                <form onSubmit={handleSubmit} className="authority-login-form">
                    <div className="authority-input-group">
                        <label className="authority-input-label">Official Identifier</label>
                        <input
                            type="text"
                            className="authority-input-field"
                            placeholder="e.g. ADM-00001 or officer@civicsol.gov.in"
                            value={identifier}
                            onChange={(e) => setIdentifier(e.target.value)}
                            disabled={loading}
                            required
                        />
                    </div>

                    <div className="authority-input-group">
                        <label className="authority-input-label">Password</label>
                        <input
                            type="password"
                            className="authority-input-field"
                            placeholder="Enter your authority password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            disabled={loading}
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        className="authority-submit-btn"
                        disabled={loading}
                    >
                        {loading ? (
                            <>
                                <Loader2 size={16} className="animate-spin" />
                                <span>Verifying Credentials...</span>
                            </>
                        ) : (
                            <>
                                <span>Access Command Center</span>
                                <ArrowRight size={16} />
                            </>
                        )}
                    </button>
                </form>

                <div className="authority-login-footer">
                    <p>
                        Are you a citizen? <Link to="/signin">Go to Citizen Portal</Link>
                    </p>
                    <p style={{ marginTop: "8px", color: "#475569" }}>
                        CIVICSOL Municipal Authority System &bull; Secure Encrypted Session
                    </p>
                </div>
            </div>
        </div>
    );
}
