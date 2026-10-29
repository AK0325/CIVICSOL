import {
    Activity,
    AlertTriangle,
    CheckCircle2,
    Clock3,
    MapPin,
    TrendingUp,
} from "lucide-react";

function Dashboard() {
    return (
        <main
            style={{
                minHeight: "calc(100vh - 76px)",
                padding: "60px 24px",
                background: "#07111f",
                color: "#f8fafc",
            }}
        >
            <div
                style={{
                    width: "min(1200px, 100%)",
                    margin: "0 auto",
                }}
            >
                {/* HEADER */}
                <div style={{ marginBottom: "40px" }}>
                    <p
                        style={{
                            margin: 0,
                            color: "#38bdf8",
                            fontSize: "12px",
                            fontWeight: 700,
                            letterSpacing: "0.15em",
                        }}
                    >
                        CIVIC INTELLIGENCE
                    </p>

                    <h1
                        style={{
                            margin: "10px 0 8px",
                            fontSize: "42px",
                            lineHeight: 1.1,
                        }}
                    >
                        Command Center
                    </h1>

                    <p
                        style={{
                            margin: 0,
                            color: "#94a3b8",
                            fontSize: "16px",
                        }}
                    >
                        Monitor, prioritize, and analyze reported civic
                        issues.
                    </p>
                </div>

                {/* STATS */}
                <section
                    style={{
                        display: "grid",
                        gridTemplateColumns:
                            "repeat(auto-fit, minmax(200px, 1fr))",
                        gap: "18px",
                        marginBottom: "28px",
                    }}
                >
                    <StatCard
                        icon={<Activity size={21} />}
                        label="Total Reports"
                        value="0"
                    />

                    <StatCard
                        icon={<AlertTriangle size={21} />}
                        label="High Priority"
                        value="0"
                    />

                    <StatCard
                        icon={<Clock3 size={21} />}
                        label="Pending"
                        value="0"
                    />

                    <StatCard
                        icon={<CheckCircle2 size={21} />}
                        label="Resolved"
                        value="0"
                    />
                </section>

                {/* MAIN PANEL */}
                <section
                    style={{
                        display: "grid",
                        gridTemplateColumns:
                            "minmax(0, 1.5fr) minmax(280px, 1fr)",
                        gap: "20px",
                    }}
                >
                    {/* ISSUE MONITOR */}
                    <div
                        style={{
                            padding: "28px",
                            borderRadius: "18px",
                            border:
                                "1px solid rgba(148,163,184,0.12)",
                            background:
                                "rgba(15, 23, 42, 0.72)",
                        }}
                    >
                        <div
                            style={{
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "center",
                                marginBottom: "24px",
                            }}
                        >
                            <div>
                                <h2
                                    style={{
                                        margin: 0,
                                        fontSize: "20px",
                                    }}
                                >
                                    Live Issue Monitor
                                </h2>

                                <p
                                    style={{
                                        margin: "6px 0 0",
                                        color: "#64748b",
                                        fontSize: "13px",
                                    }}
                                >
                                    Latest citizen reports
                                </p>
                            </div>

                            <TrendingUp
                                size={21}
                                color="#38bdf8"
                            />
                        </div>

                        <div
                            style={{
                                padding: "42px 20px",
                                textAlign: "center",
                                borderRadius: "14px",
                                border:
                                    "1px dashed rgba(148,163,184,0.2)",
                            }}
                        >
                            <Activity
                                size={34}
                                style={{
                                    marginBottom: "12px",
                                    opacity: 0.6,
                                }}
                            />

                            <h3
                                style={{
                                    margin: "0 0 8px",
                                }}
                            >
                                No civic reports yet
                            </h3>

                            <p
                                style={{
                                    margin: 0,
                                    color: "#64748b",
                                    fontSize: "14px",
                                }}
                            >
                                Submitted issues will appear here
                                automatically.
                            </p>
                        </div>
                    </div>

                    {/* INTELLIGENCE */}
                    <div
                        style={{
                            padding: "28px",
                            borderRadius: "18px",
                            border:
                                "1px solid rgba(148,163,184,0.12)",
                            background:
                                "rgba(15, 23, 42, 0.72)",
                        }}
                    >
                        <h2
                            style={{
                                margin: "0 0 22px",
                                fontSize: "20px",
                            }}
                        >
                            Civic Intelligence
                        </h2>

                        <DashboardItem
                            icon={<MapPin size={18} />}
                            title="Hotspot Detection"
                            text="Awaiting sufficient reports"
                        />

                        <DashboardItem
                            icon={<TrendingUp size={18} />}
                            title="Issue Trends"
                            text="No trend data available"
                        />

                        <DashboardItem
                            icon={<AlertTriangle size={18} />}
                            title="Priority Analysis"
                            text="Awaiting civic reports"
                        />
                    </div>
                </section>
            </div>
        </main>
    );
}


/* =====================================================
   STAT CARD
   ===================================================== */

function StatCard({ icon, label, value }) {
    return (
        <div
            style={{
                padding: "22px",
                borderRadius: "16px",
                border:
                    "1px solid rgba(148,163,184,0.12)",
                background:
                    "rgba(15, 23, 42, 0.72)",
            }}
        >
            <div
                style={{
                    width: "38px",
                    height: "38px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    borderRadius: "10px",
                    background:
                        "rgba(14,165,233,0.1)",
                    color: "#38bdf8",
                    marginBottom: "16px",
                }}
            >
                {icon}
            </div>

            <p
                style={{
                    margin: 0,
                    color: "#64748b",
                    fontSize: "12px",
                    fontWeight: 600,
                }}
            >
                {label}
            </p>

            <strong
                style={{
                    display: "block",
                    marginTop: "5px",
                    fontSize: "28px",
                }}
            >
                {value}
            </strong>
        </div>
    );
}


/* =====================================================
   DASHBOARD ITEM
   ===================================================== */

function DashboardItem({ icon, title, text }) {
    return (
        <div
            style={{
                display: "flex",
                gap: "14px",
                padding: "16px 0",
                borderBottom:
                    "1px solid rgba(148,163,184,0.08)",
            }}
        >
            <div
                style={{
                    width: "36px",
                    height: "36px",
                    flexShrink: 0,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    borderRadius: "9px",
                    background:
                        "rgba(14,165,233,0.08)",
                    color: "#38bdf8",
                }}
            >
                {icon}
            </div>

            <div>
                <strong
                    style={{
                        display: "block",
                        fontSize: "14px",
                        marginBottom: "4px",
                    }}
                >
                    {title}
                </strong>

                <span
                    style={{
                        color: "#64748b",
                        fontSize: "12px",
                    }}
                >
                    {text}
                </span>
            </div>
        </div>
    );
}


/* =====================================================
   DEFAULT EXPORT
   ===================================================== */

export default Dashboard;