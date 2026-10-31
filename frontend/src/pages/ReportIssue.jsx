import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
    ArrowLeft,
    ArrowRight,
    Camera,
    Check,
    CheckCircle2,
    FileImage,
    Lightbulb,
    Loader2,
    MapPin,
    Navigation,
    ShieldCheck,
    Sparkles,
    Upload,
    X,
} from "lucide-react";

import { createIssue } from "../services/api";

import "./ReportIssue.css";


const CATEGORIES = [
    "Road Damage",
    "Garbage",
    "Street Light",
    "Water Leakage",
    "Tree / Greenery",
    "Traffic",
    "Drainage",
    "Public Infrastructure",
];


const SEVERITIES = [
    "Low",
    "Medium",
    "High",
    "Critical",
];


const ReportIssue = () => {

    const navigate = useNavigate();

    const fileInputRef = useRef(null);
    const cameraInputRef = useRef(null);

    const [image, setImage] = useState(null);
    const [preview, setPreview] = useState("");

    const [location, setLocation] = useState(null);
    const [locationLoading, setLocationLoading] =
        useState(false);

    const [category, setCategory] = useState("");
    const [severity, setSeverity] = useState("Medium");
    const [description, setDescription] = useState("");

    const [submitting, setSubmitting] =
        useState(false);

    const [error, setError] = useState("");
    const [success, setSuccess] = useState(null);


    /* =====================================================
       IMAGE
    ===================================================== */

    const handleImageChange = (event) => {

        const selectedFile =
            event.target.files?.[0];

        if (!selectedFile) {
            return;
        }

        if (
            !selectedFile.type.startsWith("image/")
        ) {

            setError(
                "Please select a valid image file."
            );

            return;
        }

        setError("");

        setImage(selectedFile);

        const objectUrl =
            URL.createObjectURL(selectedFile);

        setPreview(objectUrl);
    };


    const removeImage = () => {

        setImage(null);
        setPreview("");

        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }

        if (cameraInputRef.current) {
            cameraInputRef.current.value = "";
        }
    };


    /* =====================================================
       GPS
    ===================================================== */

    const detectLocation = () => {

        setError("");

        if (!navigator.geolocation) {

            setError(
                "Geolocation is not supported by this browser."
            );

            return;
        }

        setLocationLoading(true);

        navigator.geolocation.getCurrentPosition(

            (position) => {

                setLocation({

                    latitude:
                        position.coords.latitude,

                    longitude:
                        position.coords.longitude,

                    accuracy:
                        position.coords.accuracy,

                });

                setLocationLoading(false);
            },

            (geoError) => {

                console.error(
                    "Location error:",
                    geoError
                );

                setLocationLoading(false);

                if (
                    geoError.code ===
                    geoError.PERMISSION_DENIED
                ) {

                    setError(
                        "Location permission was denied. Please allow location access and try again."
                    );

                } else {

                    setError(
                        "Unable to detect your current location. Please try again."
                    );
                }
            },

            {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 0,
            }
        );
    };


    /* =====================================================
       SUBMIT
    ===================================================== */

    const handleSubmit = async (event) => {

        event.preventDefault();

        setError("");

        if (!image) {

            setError(
                "Please upload a photo of the civic issue."
            );

            return;
        }

        if (!location) {

            setError(
                "Please detect your current GPS location."
            );

            return;
        }

        if (!category) {

            setError(
                "Please select an issue category."
            );

            return;
        }

        if (!description.trim()) {

            setError(
                "Please describe the civic issue."
            );

            return;
        }

        try {

            setSubmitting(true);

            const response = await createIssue({

                title: category,

                description:
                    description.trim(),

                category,

                severity,

                location:
                    `GPS: ${location.latitude.toFixed(6)}, ${location.longitude.toFixed(6)}`,

                latitude:
                    location.latitude,

                longitude:
                    location.longitude,

                image,
            });

            setSuccess(response);

        } catch (err) {

            console.error(
                "Report submission error:",
                err
            );

            if (
                err.response?.status === 401 ||
                err.response?.status === 403
            ) {

                navigate("/signin");

                return;
            }

            setError(
                err.response?.data?.detail ||
                "Unable to submit your civic report. Please try again."
            );

        } finally {

            setSubmitting(false);
        }
    };


    /* =====================================================
       RESET
    ===================================================== */

    const submitAnotherReport = () => {

        setImage(null);
        setPreview("");
        setLocation(null);
        setCategory("");
        setSeverity("Medium");
        setDescription("");
        setError("");
        setSuccess(null);

        window.scrollTo({
            top: 0,
            behavior: "smooth",
        });
    };


    /* =====================================================
       SUCCESS
    ===================================================== */

    if (success) {

        return (

            <main className="report-page">

                <div className="report-background-glow glow-one" />
                <div className="report-background-glow glow-two" />

                <div className="report-container">

                    <button
                        className="report-back-button"
                        onClick={() =>
                            navigate(
                                "/citizen-dashboard"
                            )
                        }
                    >
                        <ArrowLeft size={17} />
                        Back to Dashboard
                    </button>

                    <section className="report-success">

                        <div className="success-icon">
                            <CheckCircle2 size={42} />
                        </div>

                        <span className="report-eyebrow">
                            REPORT SUBMITTED
                        </span>

                        <h1>
                            Civic report submitted
                            successfully
                        </h1>

                        <p>
                            Your report has been securely
                            submitted to CIVICSOL for
                            analysis and civic processing.
                        </p>

                        <div className="success-details">

                            <div>
                                <span>REPORT ID</span>

                                <strong>
                                    #
                                    {success.issue?.id ||
                                        "PENDING"}
                                </strong>
                            </div>

                            <div>
                                <span>CATEGORY</span>

                                <strong>
                                    {success.issue?.category ||
                                        category}
                                </strong>
                            </div>

                            <div>
                                <span>CREDITS EARNED</span>

                                <strong className="success-credit">
                                    +
                                    {success.credits_earned ||
                                        0}
                                </strong>
                            </div>

                            <div>
                                <span>AI TRIAGE STATUS</span>

                                <strong>
                                    {success.issue?.ai_analysis?.processing_status ||
                                        "QUEUED"}
                                </strong>
                            </div>

                        </div>

                        {success.issue?.ai_analysis && (
                            <div
                                style={{
                                    marginTop: "14px",
                                    padding: "12px 16px",
                                    borderRadius: "10px",
                                    background: "rgba(14, 165, 233, 0.08)",
                                    border: "1px solid rgba(56, 189, 248, 0.22)",
                                    fontSize: "13px",
                                    color: "#cbd5e1",
                                    textAlign: "left",
                                }}
                            >
                                <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "#38bdf8", fontWeight: 700, marginBottom: "4px" }}>
                                    <Sparkles size={15} />
                                    <span>Civic AI Intelligence Triage</span>
                                </div>
                                <div>
                                    <strong>Predicted Category:</strong>{" "}
                                    {success.issue.ai_analysis.predicted_category || "Pending Authority Review"}
                                    {success.issue.ai_analysis.suggested_department_name && (
                                        <>
                                            {" • "}
                                            <strong>Recommended Dept:</strong>{" "}
                                            {success.issue.ai_analysis.suggested_department_name}
                                        </>
                                    )}
                                </div>
                            </div>
                        )}

                        <div className="success-actions">

                            <button
                                className="primary-report-button"
                                onClick={() =>
                                    navigate(
                                        "/my-reports"
                                    )
                                }
                            >
                                View My Reports
                                <ArrowRight size={17} />
                            </button>

                            <button
                                className="secondary-report-button"
                                onClick={
                                    submitAnotherReport
                                }
                            >
                                Submit Another Report
                            </button>

                        </div>

                    </section>

                </div>

            </main>
        );
    }


    /* =====================================================
       MAIN
    ===================================================== */

    return (

        <main className="report-page">

            <div className="report-background-glow glow-one" />
            <div className="report-background-glow glow-two" />


            <div className="report-container">


                {/* =================================================
                    HEADER
                ================================================= */}

                <header className="report-header">

                    <button
                        className="report-back-button"
                        onClick={() =>
                            navigate(
                                "/citizen-dashboard"
                            )
                        }
                    >
                        <ArrowLeft size={17} />
                        Back to Dashboard
                    </button>

                    <div className="secure-label">
                        <ShieldCheck size={16} />
                        Secure & Trusted
                    </div>

                </header>


                {/* =================================================
                    TITLE
                ================================================= */}

                <section className="report-title">

                    <span className="report-eyebrow">
                        CIVIC REPORTING
                    </span>

                    <h1>
                        Report
                        <span> a civic issue</span>
                    </h1>

                    <p>
                        Help make your city better.
                        Capture evidence, share your
                        location, and let CIVICSOL
                        analyze and route the issue
                        to the right authorities.
                    </p>

                </section>


                {/* =================================================
                    ERROR
                ================================================= */}

                {error && (

                    <div className="report-error">

                        <div>
                            <X size={16} />
                        </div>

                        <span>
                            {error}
                        </span>

                        <button
                            type="button"
                            onClick={() =>
                                setError("")
                            }
                        >
                            <X size={15} />
                        </button>

                    </div>
                )}


                {/* =================================================
                    REPORT GRID
                ================================================= */}

                <form
                    className="report-layout"
                    onSubmit={handleSubmit}
                >


                    {/* =================================================
                        MAIN COLUMN
                    ================================================= */}

                    <div className="report-main-column">


                        {/* =================================================
                            STEP 01
                        ================================================= */}

                        <section className="report-card">

                            <div className="step-header">

                                <div className="step-number">
                                    01
                                </div>

                                <div className="step-heading">

                                    <span>
                                        EVIDENCE
                                    </span>

                                    <h2>
                                        Capture the issue
                                    </h2>

                                    <p>
                                        Upload a clear photo
                                        showing the civic problem.
                                    </p>

                                </div>

                            </div>


                            {!preview ? (

                                <div className="upload-zone">

                                    <div className="upload-icon">
                                        <Camera size={30} />
                                    </div>

                                    <h3>
                                        Take a photo or
                                        upload one
                                    </h3>

                                    <p>
                                        Clear images help
                                        CIVICSOL analyze
                                        the issue accurately.
                                    </p>

                                    <div className="upload-actions">

                                        <button
                                            type="button"
                                            className="camera-button"
                                            onClick={() =>
                                                cameraInputRef.current?.click()
                                            }
                                        >
                                            <Camera size={18} />
                                            Open Camera
                                        </button>

                                        <button
                                            type="button"
                                            className="upload-button"
                                            onClick={() =>
                                                fileInputRef.current?.click()
                                            }
                                        >
                                            <Upload size={18} />
                                            Choose Image
                                        </button>

                                    </div>

                                    <small>
                                        JPG, PNG or WEBP
                                        {" "}
                                        (Max 10MB)
                                    </small>

                                </div>

                            ) : (

                                <div className="image-preview-wrapper">

                                    <img
                                        src={preview}
                                        alt="Civic issue evidence"
                                        className="image-preview"
                                    />

                                    <div className="image-preview-overlay">

                                        <div className="image-name">
                                            <FileImage size={17} />

                                            <span>
                                                {image?.name}
                                            </span>
                                        </div>

                                        <button
                                            type="button"
                                            className="remove-image"
                                            onClick={
                                                removeImage
                                            }
                                        >
                                            <X size={16} />
                                            Remove
                                        </button>

                                    </div>

                                </div>

                            )}


                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="image/*"
                                onChange={
                                    handleImageChange
                                }
                                hidden
                            />

                            <input
                                ref={cameraInputRef}
                                type="file"
                                accept="image/*"
                                capture="environment"
                                onChange={
                                    handleImageChange
                                }
                                hidden
                            />

                        </section>


                        {/* =================================================
                            STEP 02
                        ================================================= */}

                        <section className="report-card">

                            <div className="step-header">

                                <div className="step-number">
                                    02
                                </div>

                                <div className="step-heading">

                                    <span>
                                        LOCATION
                                    </span>

                                    <h2>
                                        Confirm your location
                                    </h2>

                                    <p>
                                        GPS evidence helps route
                                        your report to the correct area.
                                    </p>

                                </div>

                            </div>


                            <div
                                className={`location-box ${location
                                        ? "location-success"
                                        : ""
                                    }`}
                            >

                                <div className="location-icon">

                                    {location ? (
                                        <CheckCircle2
                                            size={25}
                                        />
                                    ) : (
                                        <Navigation
                                            size={25}
                                        />
                                    )}

                                </div>


                                <div className="location-content">

                                    {location ? (

                                        <>
                                            <strong>
                                                Location captured
                                            </strong>

                                            <span>
                                                GPS accuracy:
                                                {" "}
                                                {Math.round(
                                                    location.accuracy
                                                )}
                                                {" "}metres
                                            </span>

                                            <small>
                                                {location.latitude.toFixed(6)}
                                                {" , "}
                                                {location.longitude.toFixed(6)}
                                            </small>
                                        </>

                                    ) : (

                                        <>
                                            <strong>
                                                Location required
                                            </strong>

                                            <span>
                                                CIVICSOL needs your
                                                current GPS coordinates
                                                before the report can
                                                be submitted.
                                            </span>
                                        </>

                                    )}

                                </div>


                                <button
                                    type="button"
                                    className="location-button"
                                    onClick={
                                        detectLocation
                                    }
                                    disabled={
                                        locationLoading
                                    }
                                >

                                    {locationLoading ? (

                                        <>
                                            <Loader2
                                                size={17}
                                                className="spin"
                                            />
                                            Detecting...
                                        </>

                                    ) : (

                                        <>
                                            <MapPin size={17} />

                                            {location
                                                ? "Refresh Location"
                                                : "Detect Location"}
                                        </>

                                    )}

                                </button>

                            </div>

                        </section>


                        {/* =================================================
                            STEP 03
                        ================================================= */}

                        <section className="report-card">

                            <div className="step-header">

                                <div className="step-number">
                                    03
                                </div>

                                <div className="step-heading">

                                    <span>
                                        CLASSIFICATION
                                    </span>

                                    <h2>
                                        Issue details
                                    </h2>

                                    <p>
                                        Categorize and describe
                                        what you observed.
                                    </p>

                                </div>

                            </div>


                            <div className="form-grid">

                                <div className="form-field">

                                    <label>
                                        Issue Category
                                    </label>

                                    <select
                                        value={category}
                                        onChange={(event) =>
                                            setCategory(
                                                event.target.value
                                            )
                                        }
                                    >

                                        <option value="">
                                            Select issue type
                                        </option>

                                        {CATEGORIES.map(
                                            (item) => (
                                                <option
                                                    key={item}
                                                    value={item}
                                                >
                                                    {item}
                                                </option>
                                            )
                                        )}

                                    </select>

                                </div>


                                <div className="form-field">

                                    <label>
                                        Severity
                                    </label>

                                    <select
                                        value={severity}
                                        onChange={(event) =>
                                            setSeverity(
                                                event.target.value
                                            )
                                        }
                                    >

                                        {SEVERITIES.map(
                                            (item) => (
                                                <option
                                                    key={item}
                                                    value={item}
                                                >
                                                    {item}
                                                </option>
                                            )
                                        )}

                                    </select>

                                </div>

                            </div>


                            <div className="form-field description-field">

                                <label>
                                    Description
                                </label>

                                <textarea
                                    value={description}
                                    onChange={(event) =>
                                        setDescription(
                                            event.target.value
                                        )
                                    }
                                    placeholder="Describe what you observed, where it is located, and any details that may help authorities understand the issue..."
                                    rows={6}
                                    maxLength={1000}
                                />

                                <div className="character-count">
                                    {description.length}
                                    {" / 1000"}
                                </div>

                            </div>

                        </section>


                        {/* =================================================
                            SUBMIT
                        ================================================= */}

                        <button
                            type="submit"
                            className="submit-report-button"
                            disabled={submitting}
                        >

                            {submitting ? (

                                <>
                                    <Loader2
                                        size={19}
                                        className="spin"
                                    />

                                    Submitting Report...
                                </>

                            ) : (

                                <>
                                    <Navigation size={18} />

                                    Submit Civic Report

                                    <ArrowRight size={18} />
                                </>

                            )}

                        </button>


                        <p className="submit-note">
                            <ShieldCheck size={13} />

                            Your evidence is securely
                            submitted for civic issue
                            management and service improvement.
                        </p>

                    </div>


                    {/* =================================================
                        SIDEBAR
                    ================================================= */}

                    <aside className="report-sidebar">


                        {/* =================================================
                            SECURE CARD
                        ================================================= */}

                        <section className="secure-card">

                            <div className="secure-card-icon">
                                <ShieldCheck size={23} />
                            </div>

                            <div>

                                <h3>
                                    Secure & Trusted
                                </h3>

                                <p>
                                    Your data is safe and
                                    used only for civic
                                    improvement.
                                </p>

                            </div>

                        </section>


                        {/* =================================================
                            AI
                        ================================================= */}

                        <section className="ai-card">

                            <div className="ai-card-icon">
                                <Sparkles size={22} />
                            </div>

                            <span className="sidebar-eyebrow">
                                AI-READY REPORT
                            </span>

                            <h2>
                                Smart civic analysis
                            </h2>

                            <p>
                                Your evidence can be processed
                                by the CIVICSOL intelligence
                                pipeline for automated issue
                                analysis and prioritization.
                            </p>


                            <div className="ai-pipeline">

                                <PipelineItem
                                    number="01"
                                    text="Image Detection"
                                />

                                <PipelineItem
                                    number="02"
                                    text="Issue Classification"
                                />

                                <PipelineItem
                                    number="03"
                                    text="Confidence Analysis"
                                />

                                <PipelineItem
                                    number="04"
                                    text="Priority Routing"
                                />

                            </div>

                        </section>


                        {/* =================================================
                            CHECKLIST
                        ================================================= */}

                        <section className="checklist-card">

                            <span className="sidebar-eyebrow">
                                BEFORE SUBMITTING
                            </span>

                            <h2>
                                Report checklist
                            </h2>


                            <ChecklistItem
                                complete={
                                    Boolean(image)
                                }
                                text="Civic issue image"
                            />

                            <ChecklistItem
                                complete={
                                    Boolean(location)
                                }
                                text="Current GPS location"
                            />

                            <ChecklistItem
                                complete={
                                    Boolean(category)
                                }
                                text="Issue category"
                            />

                            <ChecklistItem
                                complete={
                                    Boolean(
                                        description.trim()
                                    )
                                }
                                text="Issue description"
                            />

                        </section>


                        {/* =================================================
                            TIPS
                        ================================================= */}

                        <section className="tips-card">

                            <div className="tips-heading">

                                <div className="tips-icon">
                                    <Lightbulb size={20} />
                                </div>

                                <h2>
                                    Tips for a better report
                                </h2>

                            </div>


                            <TipItem text="Take clear, well-lit photos" />

                            <TipItem text="Include the surrounding area" />

                            <TipItem text="Ensure accurate GPS location" />

                            <TipItem text="Provide enough detail" />

                            <TipItem text="Help authorities understand the issue" />

                        </section>

                    </aside>

                </form>

            </div>

        </main>
    );
};


/* =========================================================
   AI PIPELINE ITEM
========================================================= */

const PipelineItem = ({
    number,
    text,
}) => {

    return (

        <div className="pipeline-item">

            <strong>
                {number}
            </strong>

            <span>
                {text}
            </span>

        </div>
    );
};


/* =========================================================
   CHECKLIST
========================================================= */

const ChecklistItem = ({
    complete,
    text,
}) => {

    return (

        <div
            className={`checklist-item ${complete
                    ? "complete"
                    : ""
                }`}
        >

            <div className="check-circle">

                {complete && (
                    <Check size={12} />
                )}

            </div>

            <span>
                {text}
            </span>

        </div>
    );
};


/* =========================================================
   TIPS
========================================================= */

const TipItem = ({
    text,
}) => {

    return (

        <div className="tip-item">

            <div className="tip-check">
                <Check size={12} />
            </div>

            <span>
                {text}
            </span>

        </div>
    );
};


export default ReportIssue;