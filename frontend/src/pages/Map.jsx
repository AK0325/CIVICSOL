import { useEffect, useMemo, useState } from "react";

import {
    AlertTriangle,
    BrainCircuit,
    Layers3,
    MapPin,
    RefreshCw,
    Radio,
    Target,
} from "lucide-react";

import {
    CircleMarker,
    MapContainer,
    Popup,
    TileLayer,
    useMap,
} from "react-leaflet";

import L from "leaflet";

import "leaflet/dist/leaflet.css";

import { getIssues } from "../services/api";

import "./Map.css";


/* =========================================================
   DEFAULT MAP LOCATION

   Ahmedabad is used as the initial map center only.
   Once civic reports exist, the map automatically fits
   itself to the reported coordinates.
   ========================================================= */

const DEFAULT_CENTER = [
    23.0225,
    72.5714,
];

const DEFAULT_ZOOM = 12;


/* =========================================================
   MAP VIEW CONTROLLER
   ========================================================= */

function MapViewController({ issues }) {

    const map = useMap();


    useEffect(() => {

        if (!issues.length) {

            map.setView(
                DEFAULT_CENTER,
                DEFAULT_ZOOM
            );

            return;

        }


        const validIssues = issues.filter(
            (issue) =>
                Number.isFinite(Number(issue.latitude)) &&
                Number.isFinite(Number(issue.longitude))
        );


        if (!validIssues.length) {

            map.setView(
                DEFAULT_CENTER,
                DEFAULT_ZOOM
            );

            return;

        }


        const bounds = L.latLngBounds(
            validIssues.map((issue) => [
                Number(issue.latitude),
                Number(issue.longitude),
            ])
        );


        map.fitBounds(
            bounds,
            {
                padding: [50, 50],
                maxZoom: 16,
            }
        );

    }, [issues, map]);


    return null;
}


/* =========================================================
   PRIORITY HELPERS
   ========================================================= */

function normalizePriority(priority) {

    const value =
        String(priority || "Medium")
            .toLowerCase();


    if (value === "high") {
        return "high";
    }


    if (value === "low") {
        return "low";
    }


    return "medium";
}


function getPriorityLabel(priority) {

    const normalized =
        normalizePriority(priority);


    if (normalized === "high") {
        return "High";
    }


    if (normalized === "low") {
        return "Low";
    }


    return "Medium";
}


/* =========================================================
   MAP PAGE
   ========================================================= */

function Map() {

    const [issues, setIssues] = useState([]);

    const [loading, setLoading] = useState(true);

    const [error, setError] = useState("");


    /* =======================================================
       FETCH ISSUES
       ======================================================= */

    const loadIssues = async () => {

        try {

            setLoading(true);

            setError("");


            const data =
                await getIssues();


            if (Array.isArray(data)) {

                setIssues(data);

            } else if (Array.isArray(data?.issues)) {

                setIssues(data.issues);

            } else {

                setIssues([]);

            }

        } catch (err) {

            console.error(
                "CIVICSOL MAP ERROR:",
                err
            );


            setError(
                "Unable to load civic issues from the CIVICSOL server."
            );

        } finally {

            setLoading(false);

        }
    };


    /* =======================================================
       INITIAL LOAD
       ======================================================= */

    useEffect(() => {

        loadIssues();

    }, []);


    /* =======================================================
       VALID MAP ISSUES
       ======================================================= */

    const mapIssues = useMemo(() => {

        return issues.filter(
            (issue) =>
                Number.isFinite(
                    Number(issue.latitude)
                ) &&
                Number.isFinite(
                    Number(issue.longitude)
                )
        );

    }, [issues]);


    /* =======================================================
       STATS
       ======================================================= */

    const stats = useMemo(() => {

        let high = 0;
        let medium = 0;
        let low = 0;


        issues.forEach((issue) => {

            const priority =
                normalizePriority(
                    issue.priority
                );


            if (priority === "high") {
                high++;
            } else if (priority === "low") {
                low++;
            } else {
                medium++;
            }

        });


        return {
            total: issues.length,
            high,
            medium,
            low,
        };

    }, [issues]);


    /* =======================================================
       RENDER
       ======================================================= */

    return (

        <main className="map-page">

            <div className="map-container">


                {/* =================================================
            HEADER
            ================================================= */}

                <header className="map-header">

                    <div>

                        <div className="map-eyebrow">

                            <Radio size={13} />

                            CIVIC INTELLIGENCE MAP

                        </div>


                        <h1>
                            Civic Issue Map
                        </h1>


                        <p>
                            Explore reported civic issues and their
                            geographic distribution in real time.
                        </p>

                    </div>


                    <div className="map-actions">

                        <button
                            type="button"
                            className="map-refresh-button"
                            onClick={loadIssues}
                            disabled={loading}
                        >

                            {loading ? (

                                <span className="map-spinner" />

                            ) : (

                                <RefreshCw size={15} />

                            )}

                            {loading
                                ? "Loading..."
                                : "Refresh Data"}

                        </button>

                    </div>

                </header>


                {/* =================================================
            ERROR
            ================================================= */}

                {error && (

                    <div className="map-error">

                        <AlertTriangle size={17} />

                        {error}

                    </div>

                )}


                {/* =================================================
            STATS
            ================================================= */}

                <section className="map-stats">


                    <div className="map-stat">

                        <span className="map-stat-label">
                            Reported Issues
                        </span>

                        <strong className="map-stat-value">
                            {stats.total}
                        </strong>

                    </div>


                    <div className="map-stat">

                        <span className="map-stat-label">
                            High Priority
                        </span>

                        <strong className="map-stat-value high">
                            {stats.high}
                        </strong>

                    </div>


                    <div className="map-stat">

                        <span className="map-stat-label">
                            Medium Priority
                        </span>

                        <strong className="map-stat-value medium">
                            {stats.medium}
                        </strong>

                    </div>


                    <div className="map-stat">

                        <span className="map-stat-label">
                            Low Priority
                        </span>

                        <strong className="map-stat-value low">
                            {stats.low}
                        </strong>

                    </div>


                </section>


                {/* =================================================
            MAP
            ================================================= */}

                <section className="map-card">


                    <div className="map-overlay">

                        <span className="live-dot"></span>

                        LIVE CIVIC DATA

                    </div>


                    <MapContainer
                        center={DEFAULT_CENTER}
                        zoom={DEFAULT_ZOOM}
                        scrollWheelZoom={true}
                        className="civic-map"
                    >

                        <TileLayer
                            attribution='&copy; OpenStreetMap contributors'
                            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        />


                        <MapViewController
                            issues={mapIssues}
                        />


                        {/* =============================================
                ISSUE MARKERS
                ============================================= */}

                        {mapIssues.map((issue) => {

                            const priority =
                                normalizePriority(
                                    issue.priority
                                );


                            return (

                                <CircleMarker
                                    key={issue.id}
                                    center={[
                                        Number(issue.latitude),
                                        Number(issue.longitude),
                                    ]}
                                    radius={9}
                                    className={`civic-marker ${priority}`}
                                    pathOptions={{
                                        className:
                                            `civic-marker ${priority}`,
                                    }}
                                >

                                    <Popup>

                                        <div className="civic-popup">

                                            <h3>
                                                {issue.title ||
                                                    issue.category ||
                                                    "Civic Issue"}
                                            </h3>


                                            <div className="civic-popup-row">

                                                <span>
                                                    Category
                                                </span>

                                                <strong>
                                                    {issue.category ||
                                                        "Unknown"}
                                                </strong>

                                            </div>


                                            <div className="civic-popup-row">

                                                <span>
                                                    Priority
                                                </span>

                                                <strong>
                                                    {getPriorityLabel(
                                                        issue.priority
                                                    )}
                                                </strong>

                                            </div>


                                            <div className="civic-popup-row">

                                                <span>
                                                    Severity
                                                </span>

                                                <strong>
                                                    {issue.severity ||
                                                        "Medium"}
                                                </strong>

                                            </div>


                                            <div className="civic-popup-row">

                                                <span>
                                                    Status
                                                </span>

                                                <strong>
                                                    {issue.status ||
                                                        "Reported"}
                                                </strong>

                                            </div>


                                        </div>

                                    </Popup>

                                </CircleMarker>

                            );

                        })}

                    </MapContainer>


                    {/* =============================================
              EMPTY STATE
              ============================================= */}

                    {!loading &&
                        mapIssues.length === 0 && (

                            <div className="map-empty">

                                <div className="map-empty-card">

                                    <div className="map-empty-icon">

                                        <MapPin size={25} />

                                    </div>


                                    <h3>
                                        No civic issues yet
                                    </h3>


                                    <p>
                                        Report the first civic issue to
                                        populate the CIVICSOL intelligence map.
                                    </p>

                                </div>

                            </div>

                        )}


                    {/* =============================================
              LEGEND
              ============================================= */}

                    <div className="map-legend">

                        <div className="legend-title">
                            Priority
                        </div>


                        <div className="legend-item">

                            <span className="legend-dot high"></span>

                            High Priority

                        </div>


                        <div className="legend-item">

                            <span className="legend-dot medium"></span>

                            Medium Priority

                        </div>


                        <div className="legend-item">

                            <span className="legend-dot low"></span>

                            Low Priority

                        </div>

                    </div>


                </section>


                {/* =================================================
            INTELLIGENCE SECTION
            ================================================= */}

                <section className="map-intelligence">


                    <div className="intelligence-card">

                        <span className="intelligence-label">

                            SPATIAL INTELLIGENCE

                        </span>


                        <h2>
                            Location-aware civic analysis.
                        </h2>


                        <p>
                            Every civic report contains geographic
                            coordinates. This allows CIVICSOL to
                            analyze where problems are occurring,
                            identify recurring locations, and
                            eventually detect civic hotspots.
                        </p>

                    </div>


                    <div className="intelligence-card">

                        <span className="intelligence-label">

                            NEXT INTELLIGENCE LAYER

                        </span>


                        <h2>
                            From individual reports to civic hotspots.
                        </h2>


                        <p>
                            As more reports are collected, CIVICSOL
                            can group geographically related issues,
                            detect recurring problems, and surface
                            areas that require greater civic attention.
                        </p>

                    </div>


                </section>


                {/* =================================================
            INTELLIGENCE FEATURES
            ================================================= */}

                <section className="intelligence-features">


                    <div className="intelligence-feature">

                        <span className="intelligence-feature-number">
                            01
                        </span>


                        <strong>
                            Spatial Clustering
                        </strong>


                        <span>
                            Group multiple reports occurring within
                            the same geographic area.
                        </span>

                    </div>


                    <div className="intelligence-feature">

                        <span className="intelligence-feature-number">
                            02
                        </span>


                        <strong>
                            Hotspot Detection
                        </strong>


                        <span>
                            Identify locations where civic problems
                            are repeatedly reported.
                        </span>

                    </div>


                    <div className="intelligence-feature">

                        <span className="intelligence-feature-number">
                            03
                        </span>


                        <strong>
                            Priority Mapping
                        </strong>


                        <span>
                            Combine location and issue priority to
                            highlight areas requiring attention.
                        </span>

                    </div>


                    <div className="intelligence-feature">

                        <span className="intelligence-feature-number">
                            04
                        </span>


                        <strong>
                            AI Civic Analysis
                        </strong>


                        <span>
                            Connect geographic evidence with the
                            CIVICSOL intelligence pipeline.
                        </span>

                    </div>


                </section>


            </div>

        </main>

    );
}


export default Map;