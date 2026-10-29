import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import Navbar from "./components/Navbar";
import Footer from "./components/Footer";

import Signup from "./pages/Signup";
import Signin from "./pages/Signin";
import ForgotPassword from "./pages/ForgotPassword";

import Home from "./pages/Home";
import CitizenDashboard from "./pages/CitizenDashboard";
import ReportIssue from "./pages/ReportIssue";
import Map from "./pages/Map";
import Dashboard from "./pages/Dashboard";
import Rewards from "./pages/Rewards";
import MyReports from "./pages/MyReports";
import Profile from "./pages/Profile";

// Authority Components & Pages
import AuthorityRoute from "./components/AuthorityRoute";
import AuthorityLogin from "./pages/authority/AuthorityLogin";
import AuthorityDashboard from "./pages/authority/AuthorityDashboard";
import IssueManagement from "./pages/authority/IssueManagement";
import IssueDetails from "./pages/authority/IssueDetails";
import DepartmentManagement from "./pages/authority/DepartmentManagement";
import OfficerManagement from "./pages/authority/OfficerManagement";
import AuthorityMap from "./pages/authority/AuthorityMap";
import AnalyticsDashboard from "./pages/authority/AnalyticsDashboard";
import AuditLogViewer from "./pages/authority/AuditLogViewer";

const getAuthToken = () => {
  return localStorage.getItem("civicsol_access_token");
};

function ProtectedRoute({ children }) {
  const token = getAuthToken();

  if (!token) {
    return <Navigate to="/signin" replace />;
  }

  return children;
}

function PublicAuthRoute({ children }) {
  const token = getAuthToken();

  if (token) {
    return <Navigate to="/citizen-dashboard" replace />;
  }

  return children;
}

function App() {
  const location = useLocation();
  const isAuthorityRoute = location.pathname.startsWith("/authority");

  if (isAuthorityRoute) {
    return (
      <div className="authority-app-root">
        <Routes>
          <Route path="/authority/login" element={<AuthorityLogin />} />

          <Route
            path="/authority"
            element={<Navigate to="/authority/dashboard" replace />}
          />

          <Route
            path="/authority/dashboard"
            element={
              <AuthorityRoute>
                <AuthorityDashboard />
              </AuthorityRoute>
            }
          />

          <Route
            path="/authority/issues"
            element={
              <AuthorityRoute>
                <IssueManagement />
              </AuthorityRoute>
            }
          />

          <Route
            path="/authority/issues/:id"
            element={
              <AuthorityRoute>
                <IssueDetails />
              </AuthorityRoute>
            }
          />

          <Route
            path="/authority/map"
            element={
              <AuthorityRoute>
                <AuthorityMap />
              </AuthorityRoute>
            }
          />

          <Route
            path="/authority/departments"
            element={
              <AuthorityRoute allowedRoles={["SUPER_ADMIN"]}>
                <DepartmentManagement />
              </AuthorityRoute>
            }
          />

          <Route
            path="/authority/officers"
            element={
              <AuthorityRoute allowedRoles={["SUPER_ADMIN", "DEPARTMENT_OFFICER"]}>
                <OfficerManagement />
              </AuthorityRoute>
            }
          />

          <Route
            path="/authority/analytics"
            element={
              <AuthorityRoute>
                <AnalyticsDashboard />
              </AuthorityRoute>
            }
          />

          <Route
            path="/authority/audit-logs"
            element={
              <AuthorityRoute allowedRoles={["SUPER_ADMIN"]}>
                <AuditLogViewer />
              </AuthorityRoute>
            }
          />

          <Route
            path="/authority/*"
            element={<Navigate to="/authority/dashboard" replace />}
          />
        </Routes>
      </div>
    );
  }

  return (
    <div className="app">
      <Navbar />

      <main className="app-content">
        <Routes>
          {/* PUBLIC CITIZEN PAGES */}
          <Route path="/" element={<Home />} />

          <Route
            path="/signin"
            element={
              <PublicAuthRoute>
                <Signin />
              </PublicAuthRoute>
            }
          />

          <Route
            path="/signup"
            element={
              <PublicAuthRoute>
                <Signup />
              </PublicAuthRoute>
            }
          />

          <Route path="/forgot-password" element={<ForgotPassword />} />

          {/* PROTECTED CITIZEN PAGES */}
          <Route
            path="/citizen-dashboard"
            element={
              <ProtectedRoute>
                <CitizenDashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/report"
            element={
              <ProtectedRoute>
                <ReportIssue />
              </ProtectedRoute>
            }
          />

          <Route
            path="/map"
            element={
              <ProtectedRoute>
                <Map />
              </ProtectedRoute>
            }
          />

          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/rewards"
            element={
              <ProtectedRoute>
                <Rewards />
              </ProtectedRoute>
            }
          />

          <Route
            path="/my-reports"
            element={
              <ProtectedRoute>
                <MyReports />
              </ProtectedRoute>
            }
          />

          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            }
          />

          {/* UNKNOWN ROUTES */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      <Footer />
    </div>
  );
}

export default App;
