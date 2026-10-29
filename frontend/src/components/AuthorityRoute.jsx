import { Navigate } from "react-router-dom";

export default function AuthorityRoute({ children, allowedRoles }) {
    const token = localStorage.getItem("civicsol_authority_token");

    if (!token) {
        return <Navigate to="/authority/login" replace />;
    }

    if (allowedRoles && Array.isArray(allowedRoles) && allowedRoles.length > 0) {
        try {
            const rawUser = localStorage.getItem("civicsol_authority_user");
            const user = rawUser ? JSON.parse(rawUser) : null;
            if (user && !allowedRoles.includes(user.role)) {
                return <Navigate to="/authority/dashboard" replace />;
            }
        } catch {
            return <Navigate to="/authority/dashboard" replace />;
        }
    }

    return children;
}
