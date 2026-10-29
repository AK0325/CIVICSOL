import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
    ArrowLeft,
    CheckCircle2,
    ChevronLeft,
    Mail,
    MessageSquare,
    RefreshCw,
    ShieldCheck,
    Smartphone,
    Lock,
    Eye,
    EyeOff,
} from "lucide-react";

import {
    requestPasswordReset,
    verifyPasswordResetOTP,
    resetForgottenPassword,
} from "../services/api";

import "./ForgotPassword.css";


const ForgotPassword = () => {

    const navigate = useNavigate();

    const [step, setStep] = useState(1);

    const [channel, setChannel] =
        useState("mobile");

    const [destination, setDestination] =
        useState("");

    const [maskedDestination, setMaskedDestination] =
        useState("");

    const [otp, setOtp] =
        useState([
            "",
            "",
            "",
            "",
            "",
            "",
        ]);

    const [resetToken, setResetToken] =
        useState("");

    const [newPassword, setNewPassword] =
        useState("");

    const [confirmPassword, setConfirmPassword] =
        useState("");

    const [showNewPassword, setShowNewPassword] =
        useState(false);

    const [showConfirmPassword, setShowConfirmPassword] =
        useState(false);

    const [loading, setLoading] =
        useState(false);

    const [error, setError] =
        useState("");

    const [success, setSuccess] =
        useState("");

    const [resendSeconds, setResendSeconds] =
        useState(0);

    const otpRefs = useRef([]);


    /* =====================================================
       OTP COUNTDOWN
    ===================================================== */

    useEffect(() => {

        if (resendSeconds <= 0) {
            return;
        }

        const timer = setInterval(() => {

            setResendSeconds(
                (seconds) =>
                    Math.max(0, seconds - 1)
            );

        }, 1000);

        return () => clearInterval(timer);

    }, [resendSeconds]);


    /* =====================================================
       CLEAR MESSAGES
    ===================================================== */

    const clearMessages = () => {

        setError("");
        setSuccess("");

    };


    /* =====================================================
       SEND OTP
    ===================================================== */

    const handleSendOTP = async (event) => {

        event.preventDefault();

        clearMessages();

        const value =
            destination.trim();


        if (!value) {

            setError(
                channel === "mobile"
                    ? "Please enter your mobile number."
                    : "Please enter your email address."
            );

            return;
        }


        if (
            channel === "mobile" &&
            !/^\d{10}$/.test(value)
        ) {

            setError(
                "Please enter a valid 10-digit mobile number."
            );

            return;
        }


        if (
            channel === "email" &&
            !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
        ) {

            setError(
                "Please enter a valid email address."
            );

            return;
        }


        try {

            setLoading(true);

            const response =
                await requestPasswordReset({
                    channel,
                    destination: value,
                });


            setMaskedDestination(
                response.destination || value
            );

            setStep(2);

            setOtp([
                "",
                "",
                "",
                "",
                "",
                "",
            ]);

            setResendSeconds(45);

            setSuccess(
                "Verification code sent successfully."
            );


            setTimeout(() => {

                otpRefs.current[0]?.focus();

            }, 100);

        } catch (err) {

            console.error(
                "Forgot password error:",
                err
            );

            setError(
                err.response?.data?.detail ||
                "Unable to send verification code. Please try again."
            );

        } finally {

            setLoading(false);
        }
    };


    /* =====================================================
       OTP INPUT
    ===================================================== */

    const handleOTPChange = (
        index,
        value
    ) => {

        if (!/^\d?$/.test(value)) {
            return;
        }

        const nextOtp = [
            ...otp,
        ];

        nextOtp[index] = value;

        setOtp(nextOtp);

        if (
            value &&
            index < 5
        ) {

            otpRefs
                .current[index + 1]
                ?.focus();

        }
    };


    /* =====================================================
       OTP KEYBOARD
    ===================================================== */

    const handleOTPKeyDown = (
        index,
        event
    ) => {

        if (
            event.key === "Backspace" &&
            !otp[index] &&
            index > 0
        ) {

            otpRefs
                .current[index - 1]
                ?.focus();

        }
    };


    /* =====================================================
       VERIFY OTP
    ===================================================== */

    const handleVerifyOTP = async (
        event
    ) => {

        event.preventDefault();

        clearMessages();

        const otpValue =
            otp.join("");


        if (otpValue.length !== 6) {

            setError(
                "Please enter the complete 6-digit verification code."
            );

            return;
        }


        try {

            setLoading(true);

            const response =
                await verifyPasswordResetOTP({
                    destination,
                    otp: otpValue,
                });


            setResetToken(
                response.reset_token
            );

            setStep(3);

            setSuccess(
                "Identity verified successfully."
            );

        } catch (err) {

            console.error(
                "OTP verification error:",
                err
            );

            setError(
                err.response?.data?.detail ||
                "Invalid or expired verification code."
            );

        } finally {

            setLoading(false);
        }
    };


    /* =====================================================
       RESEND OTP
    ===================================================== */

    const handleResendOTP = async () => {

        if (resendSeconds > 0) {
            return;
        }

        clearMessages();

        try {

            setLoading(true);

            await requestPasswordReset({
                channel,
                destination,
            });


            setOtp([
                "",
                "",
                "",
                "",
                "",
                "",
            ]);

            setResendSeconds(45);

            setSuccess(
                "A new verification code has been sent."
            );


            setTimeout(() => {

                otpRefs.current[0]?.focus();

            }, 100);

        } catch (err) {

            console.error(
                "OTP resend error:",
                err
            );

            setError(
                err.response?.data?.detail ||
                "Unable to resend verification code."
            );

        } finally {

            setLoading(false);
        }
    };


    /* =====================================================
       RESET PASSWORD
    ===================================================== */

    const handleResetPassword = async (
        event
    ) => {

        event.preventDefault();

        clearMessages();


        if (
            newPassword.length < 8
        ) {

            setError(
                "Password must contain at least 8 characters."
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


        try {

            setLoading(true);

            const response =
                await resetForgottenPassword({
                    destination,
                    reset_token:
                        resetToken,
                    new_password:
                        newPassword,
                });


            setSuccess(
                response?.message ||
                "Password reset successfully."
            );

            setStep(4);

        } catch (err) {

            console.error(
                "Password reset error:",
                err
            );

            setError(
                err.response?.data?.detail ||
                "Unable to reset password. Please try again."
            );

        } finally {

            setLoading(false);
        }
    };


    /* =====================================================
       BACK
    ===================================================== */

    const handleBack = () => {

        clearMessages();

        if (step === 1) {

            navigate("/signin");

            return;
        }


        if (step === 2) {

            setStep(1);

            return;
        }


        if (step === 3) {

            setStep(2);

            return;
        }

    };


    /* =====================================================
       RENDER
    ===================================================== */

    return (

        <main className="forgot-page">

            <div className="forgot-background-glow forgot-glow-one" />
            <div className="forgot-background-glow forgot-glow-two" />


            <div className="forgot-container">


                {/* =================================================
                    HEADER
                ================================================= */}

                <header className="forgot-header">

                    <button
                        className="forgot-back"
                        onClick={handleBack}
                    >

                        <ChevronLeft size={18} />

                        <span>
                            {step === 1
                                ? "Back to Sign In"
                                : "Back"}
                        </span>

                    </button>


                    <div className="forgot-security">

                        <ShieldCheck size={16} />

                        <span>
                            Secure Recovery
                        </span>

                    </div>

                </header>


                {/* =================================================
                    CARD
                ================================================= */}

                <section className="forgot-card">


                    {/* =================================================
                        PROGRESS
                    ================================================= */}

                    {step < 4 && (

                        <div className="forgot-progress">

                            <div
                                className={
                                    step >= 1
                                        ? "active"
                                        : ""
                                }
                            />

                            <div
                                className={
                                    step >= 2
                                        ? "active"
                                        : ""
                                }
                            />

                            <div
                                className={
                                    step >= 3
                                        ? "active"
                                        : ""
                                }
                            />

                        </div>

                    )}


                    {/* =================================================
                        STEP 1
                    ================================================= */}

                    {step === 1 && (

                        <div className="forgot-step">

                            <div className="forgot-icon">

                                <Lock size={25} />

                            </div>

                            <span className="forgot-eyebrow">
                                ACCOUNT RECOVERY
                            </span>

                            <h1>
                                Recover Your Account
                            </h1>

                            <p className="forgot-subtitle">
                                Choose how you want to
                                receive your verification
                                code.
                            </p>


                            <div className="recovery-methods">


                                {/* MOBILE */}

                                <button
                                    type="button"
                                    className={
                                        `recovery-method ${channel === "mobile"
                                            ? "selected"
                                            : ""
                                        }`
                                    }
                                    onClick={() => {

                                        setChannel(
                                            "mobile"
                                        );

                                        setDestination(
                                            ""
                                        );

                                        clearMessages();

                                    }}
                                >

                                    <div className="method-icon">

                                        <Smartphone
                                            size={20}
                                        />

                                    </div>

                                    <div className="method-content">

                                        <strong>
                                            Mobile Number
                                        </strong>

                                        <span>
                                            Receive OTP by SMS
                                        </span>

                                    </div>

                                    <div className="method-radio">

                                        {channel === "mobile" && (
                                            <span />
                                        )}

                                    </div>

                                </button>


                                {/* EMAIL */}

                                <button
                                    type="button"
                                    className={
                                        `recovery-method ${channel === "email"
                                            ? "selected"
                                            : ""
                                        }`
                                    }
                                    onClick={() => {

                                        setChannel(
                                            "email"
                                        );

                                        setDestination(
                                            ""
                                        );

                                        clearMessages();

                                    }}
                                >

                                    <div className="method-icon">

                                        <Mail
                                            size={20}
                                        />

                                    </div>

                                    <div className="method-content">

                                        <strong>
                                            Email Address
                                        </strong>

                                        <span>
                                            Receive OTP by email
                                        </span>

                                    </div>

                                    <div className="method-radio">

                                        {channel === "email" && (
                                            <span />
                                        )}

                                    </div>

                                </button>

                            </div>


                            <form
                                onSubmit={
                                    handleSendOTP
                                }
                            >

                                <div className="forgot-field">

                                    <label>
                                        {channel === "mobile"
                                            ? "Mobile Number"
                                            : "Email Address"}
                                    </label>

                                    <div className="forgot-input-wrap">

                                        {channel === "mobile" && (
                                            <span className="input-prefix">
                                                +91
                                            </span>
                                        )}

                                        {channel === "mobile" ? (
                                            <input
                                                type="tel"
                                                value={destination}
                                                onChange={(event) =>
                                                    setDestination(
                                                        event.target.value
                                                            .replace(
                                                                /\D/g,
                                                                ""
                                                            )
                                                            .slice(
                                                                0,
                                                                10
                                                            )
                                                    )
                                                }
                                                placeholder="Enter 10-digit mobile number"
                                                autoComplete="tel"
                                            />
                                        ) : (
                                            <input
                                                type="email"
                                                value={destination}
                                                onChange={(event) =>
                                                    setDestination(
                                                        event.target.value
                                                    )
                                                }
                                                placeholder="Enter your email address"
                                                autoComplete="email"
                                            />
                                        )}

                                    </div>

                                </div>


                                {error && (

                                    <div className="forgot-error">
                                        {error}
                                    </div>

                                )}


                                <button
                                    type="submit"
                                    className="forgot-primary-button"
                                    disabled={loading}
                                >

                                    {loading
                                        ? "Sending OTP..."
                                        : "Send OTP"}

                                </button>

                            </form>


                            <div className="forgot-info">

                                <ShieldCheck size={15} />

                                <span>
                                    Your account information
                                    remains protected during
                                    recovery.
                                </span>

                            </div>

                        </div>
                    )}


                    {/* =================================================
                        STEP 2
                    ================================================= */}

                    {step === 2 && (

                        <div className="forgot-step">

                            <div className="forgot-icon">

                                <MessageSquare size={25} />

                            </div>

                            <span className="forgot-eyebrow">
                                VERIFY IDENTITY
                            </span>

                            <h1>
                                Enter Verification Code
                            </h1>

                            <p className="forgot-subtitle">

                                Enter the 6-digit code sent
                                to

                                <strong>
                                    {" "}
                                    {maskedDestination}
                                </strong>

                            </p>


                            <form
                                onSubmit={
                                    handleVerifyOTP
                                }
                            >

                                <div className="otp-container">

                                    {otp.map(
                                        (
                                            value,
                                            index
                                        ) => (

                                            <input
                                                key={
                                                    index
                                                }
                                                ref={(element) => {

                                                    otpRefs.current[
                                                        index
                                                    ] = element;

                                                }}
                                                className="otp-input"
                                                type="text"
                                                inputMode="numeric"
                                                maxLength={1}
                                                value={value}
                                                onChange={(event) =>
                                                    handleOTPChange(
                                                        index,
                                                        event.target.value
                                                    )
                                                }
                                                onKeyDown={(event) =>
                                                    handleOTPKeyDown(
                                                        index,
                                                        event
                                                    )
                                                }
                                                autoComplete={
                                                    index === 0
                                                        ? "one-time-code"
                                                        : "off"
                                                }
                                            />

                                        )
                                    )}

                                </div>


                                {error && (

                                    <div className="forgot-error">
                                        {error}
                                    </div>

                                )}


                                {success && (

                                    <div className="forgot-success">
                                        {success}
                                    </div>

                                )}


                                <button
                                    type="submit"
                                    className="forgot-primary-button"
                                    disabled={loading}
                                >

                                    {loading
                                        ? "Verifying..."
                                        : "Verify OTP"}

                                </button>

                            </form>


                            <div className="resend-area">

                                <span>
                                    Didn't receive the code?
                                </span>

                                <button
                                    type="button"
                                    onClick={
                                        handleResendOTP
                                    }
                                    disabled={
                                        resendSeconds > 0 ||
                                        loading
                                    }
                                >

                                    <RefreshCw size={13} />

                                    {resendSeconds > 0
                                        ? `Resend in ${resendSeconds}s`
                                        : "Resend OTP"}

                                </button>

                            </div>

                        </div>
                    )}


                    {/* =================================================
                        STEP 3
                    ================================================= */}

                    {step === 3 && (

                        <div className="forgot-step">

                            <div className="forgot-icon">

                                <Lock size={25} />

                            </div>

                            <span className="forgot-eyebrow">
                                SECURE PASSWORD RESET
                            </span>

                            <h1>
                                Create New Password
                            </h1>

                            <p className="forgot-subtitle">
                                Choose a strong password
                                for your CIVICSOL account.
                            </p>


                            <form
                                onSubmit={
                                    handleResetPassword
                                }
                            >


                                {/* NEW PASSWORD */}

                                <div className="forgot-field">

                                    <label>
                                        New Password
                                    </label>

                                    <div className="forgot-password-wrap">

                                        <input
                                            type={
                                                showNewPassword
                                                    ? "text"
                                                    : "password"
                                            }
                                            value={
                                                newPassword
                                            }
                                            onChange={(event) =>
                                                setNewPassword(
                                                    event.target.value
                                                )
                                            }
                                            placeholder="Enter new password"
                                            autoComplete="new-password"
                                        />

                                        <button
                                            type="button"
                                            onClick={() =>
                                                setShowNewPassword(
                                                    !showNewPassword
                                                )
                                            }
                                            aria-label={
                                                showNewPassword
                                                    ? "Hide password"
                                                    : "Show password"
                                            }
                                        >

                                            {showNewPassword ? (
                                                <EyeOff
                                                    size={17}
                                                />
                                            ) : (
                                                <Eye
                                                    size={17}
                                                />
                                            )}

                                        </button>

                                    </div>

                                </div>


                                {/* CONFIRM PASSWORD */}

                                <div className="forgot-field">

                                    <label>
                                        Confirm New Password
                                    </label>

                                    <div className="forgot-password-wrap">

                                        <input
                                            type={
                                                showConfirmPassword
                                                    ? "text"
                                                    : "password"
                                            }
                                            value={
                                                confirmPassword
                                            }
                                            onChange={(event) =>
                                                setConfirmPassword(
                                                    event.target.value
                                                )
                                            }
                                            placeholder="Re-enter new password"
                                            autoComplete="new-password"
                                        />

                                        <button
                                            type="button"
                                            onClick={() =>
                                                setShowConfirmPassword(
                                                    !showConfirmPassword
                                                )
                                            }
                                            aria-label={
                                                showConfirmPassword
                                                    ? "Hide password"
                                                    : "Show password"
                                            }
                                        >

                                            {showConfirmPassword ? (
                                                <EyeOff
                                                    size={17}
                                                />
                                            ) : (
                                                <Eye
                                                    size={17}
                                                />
                                            )}

                                        </button>

                                    </div>

                                </div>


                                <div className="forgot-password-requirements">

                                    <span
                                        className={
                                            newPassword.length >= 8
                                                ? "valid"
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
                                                ? "valid"
                                                : ""
                                        }
                                    >
                                        ✓ Passwords match
                                    </span>

                                </div>


                                {error && (

                                    <div className="forgot-error">
                                        {error}
                                    </div>

                                )}


                                <button
                                    type="submit"
                                    className="forgot-primary-button"
                                    disabled={loading}
                                >

                                    {loading
                                        ? "Resetting Password..."
                                        : "Reset Password"}

                                </button>

                            </form>

                        </div>
                    )}


                    {/* =================================================
                        STEP 4
                    ================================================= */}

                    {step === 4 && (

                        <div className="forgot-step forgot-success-step">

                            <div className="forgot-success-icon">

                                <CheckCircle2
                                    size={38}
                                />

                            </div>

                            <span className="forgot-eyebrow">
                                RECOVERY COMPLETE
                            </span>

                            <h1>
                                Password Reset Successfully
                            </h1>

                            <p className="forgot-subtitle">
                                Your CIVICSOL account password
                                has been updated successfully.
                            </p>


                            <div className="success-security-box">

                                <ShieldCheck
                                    size={18}
                                />

                                <span>
                                    Your account is now
                                    protected with your
                                    new password.
                                </span>

                            </div>


                            <button
                                className="forgot-primary-button"
                                onClick={() =>
                                    navigate(
                                        "/signin"
                                    )
                                }
                            >

                                <ArrowLeft
                                    size={16}
                                />

                                Back to Sign In

                            </button>

                        </div>

                    )}

                </section>


                {/* =================================================
                    FOOTER
                ================================================= */}

                <footer className="forgot-footer">

                    <ShieldCheck size={14} />

                    <span>
                        CIVICSOL Secure Citizen
                        Authentication
                    </span>

                </footer>

            </div>

        </main>
    );
};


export default ForgotPassword;