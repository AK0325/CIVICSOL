/* =========================================================
   CIVICSOL - Authority API Service
   Handles all Authority Command Center network requests.
========================================================= */

import axios from "axios";

const API_BASE_URL = import.meta.env?.VITE_API_URL || "http://127.0.0.1:8000";

const authorityApi = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
});

// Attach Authority Bearer token
authorityApi.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem("civicsol_authority_token");
        if (token) {
            config.headers = config.headers || {};
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Handle 401 / 403 on Authority endpoints
authorityApi.interceptors.response.use(
    (response) => response,
    (error) => {
        const status = error.response?.status;
        const requestUrl = error.config?.url || "";

        if (status === 401 && !requestUrl.includes("/authority/auth/login")) {
            localStorage.removeItem("civicsol_authority_token");
            localStorage.removeItem("civicsol_authority_user");
            delete authorityApi.defaults.headers.common.Authorization;

            if (typeof window !== "undefined" && window.location.pathname !== "/authority/login") {
                window.location.replace("/authority/login");
            }
        }
        return Promise.reject(error);
    }
);

/* =========================================================
   AUTH
========================================================= */

export const loginAuthority = async ({ identifier, password }) => {
    const res = await authorityApi.post("/authority/auth/login", {
        identifier,
        password,
    });
    if (res.data?.access_token) {
        localStorage.setItem("civicsol_authority_token", res.data.access_token);
        localStorage.setItem("civicsol_authority_user", JSON.stringify(res.data));
    }
    return res.data;
};

export const getAuthorityProfile = async () => {
    const res = await authorityApi.get("/authority/auth/me");
    return res.data;
};

export const logoutAuthority = () => {
    localStorage.removeItem("civicsol_authority_token");
    localStorage.removeItem("civicsol_authority_user");
    delete authorityApi.defaults.headers.common.Authorization;
};

/* =========================================================
   STATISTICS & ANALYTICS
========================================================= */

export const getAuthorityStatsOverview = async () => {
    const res = await authorityApi.get("/authority/stats/overview");
    return res.data;
};

export const getAuthorityDepartmentStats = async () => {
    const res = await authorityApi.get("/authority/stats/departments");
    return res.data;
};

export const getAuthorityTrends = async (days = 30) => {
    const res = await authorityApi.get(`/authority/stats/trends?days=${days}`);
    return res.data;
};

/* =========================================================
   ISSUES
========================================================= */

export const getAuthorityIssues = async (params = {}) => {
    const res = await authorityApi.get("/authority/issues/", { params });
    return res.data;
};

export const getAuthorityIssueDetail = async (issueId) => {
    const res = await authorityApi.get(`/authority/issues/${issueId}`);
    return res.data;
};

export const assignAuthorityIssue = async (issueId, { department_id, assigned_officer_id, comment }) => {
    const res = await authorityApi.put(`/authority/issues/${issueId}/assign`, {
        department_id,
        assigned_officer_id,
        comment,
    });
    return res.data;
};

export const updateAuthorityIssueStatus = async (issueId, { status, comment, rejection_reason }) => {
    const res = await authorityApi.put(`/authority/issues/${issueId}/status`, {
        status,
        comment,
        rejection_reason,
    });
    return res.data;
};

export const resolveAuthorityIssue = async (issueId, formData) => {
    const res = await authorityApi.post(`/authority/issues/${issueId}/resolve`, formData);
    return res.data;
};

/* =========================================================
   DEPARTMENTS
========================================================= */

export const getAuthorityDepartments = async (params = {}) => {
    const res = await authorityApi.get("/authority/departments/", { params });
    return res.data;
};

export const createAuthorityDepartment = async (data) => {
    const res = await authorityApi.post("/authority/departments/", data);
    return res.data;
};

export const updateAuthorityDepartment = async (deptId, data) => {
    const res = await authorityApi.put(`/authority/departments/${deptId}`, data);
    return res.data;
};

/* =========================================================
   OFFICERS
========================================================= */

export const getAuthorityOfficers = async (params = {}) => {
    const res = await authorityApi.get("/authority/officers/", { params });
    return res.data;
};

export const createAuthorityOfficer = async (data) => {
    const res = await authorityApi.post("/authority/officers/", data);
    return res.data;
};

export const updateAuthorityOfficer = async (officerId, data) => {
    const res = await authorityApi.put(`/authority/officers/${officerId}`, data);
    return res.data;
};

/* =========================================================
   GIS MAP
========================================================= */

export const getAuthorityMapIssues = async (params = {}) => {
    const res = await authorityApi.get("/authority/map/issues", { params });
    return res.data;
};

/* =========================================================
   AUDIT LOGS
========================================================= */

export const getAuthorityAuditLogs = async (params = {}) => {
    const res = await authorityApi.get("/authority/audit-logs/", { params });
    return res.data;
};

/* =========================================================
   EXTENSIONS: CSV EXPORT, LIVE ACTIVITY & WORKLOADS
========================================================= */

export const exportAuthorityIssuesCsv = async (params = {}) => {
    const res = await authorityApi.get("/authority/issues/export", {
        params,
        responseType: "blob",
    });
    return res.data;
};

export const getRecentAuthorityActivity = async (limit = 20) => {
    const res = await authorityApi.get(`/authority/issues/activity/recent?limit=${limit}`);
    return res.data;
};

export const getOfficerWorkloads = async (departmentId = null) => {
    const params = departmentId ? { department_id: departmentId } : {};
    const res = await authorityApi.get("/authority/stats/officer-workloads", { params });
    return res.data;
};

/* =========================================================
   AI CIVIC INTELLIGENCE
========================================================= */

export const runIssueAiAnalysis = async (issueId) => {
    const res = await authorityApi.post(`/ai/analyze/${issueId}`);
    return res.data;
};

export const getIssueAiAnalysis = async (issueId) => {
    const res = await authorityApi.get(`/ai/analysis/${issueId}`);
    return res.data;
};

export const getIssueAiHistory = async (issueId) => {
    const res = await authorityApi.get(`/ai/analysis/${issueId}/history`);
    return res.data;
};

export const reanalyzeIssueAi = async (issueId) => {
    const res = await authorityApi.post(`/ai/reanalyze/${issueId}`);
    return res.data;
};

export const approveIssueAiRecommendation = async (issueId, payload = {}) => {
    const res = await authorityApi.post(`/ai/analysis/${issueId}/approve`, payload);
    return res.data;
};

export const rejectIssueAiRecommendation = async (issueId, payload = {}) => {
    const res = await authorityApi.post(`/ai/analysis/${issueId}/reject`, payload);
    return res.data;
};

export const flagAiFalsePositive = async (issueId, payload) => {
    const res = await authorityApi.post(`/ai/analysis/${issueId}/false_positive`, payload);
    return res.data;
};

export const linkDuplicateIssue = async (issueId, payload) => {
    const res = await authorityApi.post(`/ai/analysis/${issueId}/link_duplicate`, payload);
    return res.data;
};

export default authorityApi;

