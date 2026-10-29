/* =========================================================
   CIVICSOL API SERVICE
========================================================= */

import axios from "axios";


/* =========================================================
   API CONFIGURATION
========================================================= */

const API_BASE_URL = "http://127.0.0.1:8000";


const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
});


/* =========================================================
   REQUEST INTERCEPTOR
   Automatically attaches JWT to protected requests.
========================================================= */

api.interceptors.request.use(
    (config) => {

        const token =
            localStorage.getItem("civicsol_access_token") ||
            localStorage.getItem("civicsol_authority_token");


        if (token) {

            config.headers = config.headers || {};

            config.headers.Authorization =
                `Bearer ${token}`;

        }


        return config;

    },

    (error) => {

        return Promise.reject(error);

    }
);


/* =========================================================
   RESPONSE INTERCEPTOR
   Handles expired / invalid authentication tokens.
========================================================= */

api.interceptors.response.use(

    (response) => {

        return response;

    },

    (error) => {

        const status = error.response?.status;

        const requestUrl =
            error.config?.url || "";


        /*
         * Do not automatically logout for authentication
         * endpoints such as signin/signup.
         *
         * Their errors should be displayed by the page itself.
         */

        const isAuthEndpoint =
            requestUrl.includes("/auth/signin") ||
            requestUrl.includes("/auth/signup") ||
            requestUrl.includes("/auth/forgot-password") ||
            requestUrl.includes("/auth/verify-reset-otp") ||
            requestUrl.includes("/auth/reset-password");


        /*
         * If a protected request returns 401/403,
         * clear the local authentication state.
         */

        if (
            (status === 401 || status === 403) &&
            !isAuthEndpoint
        ) {

            localStorage.removeItem(
                "civicsol_access_token"
            );

            localStorage.removeItem(
                "civicsol_citizen"
            );


            delete api.defaults.headers.common.Authorization;


            /*
             * Redirect only in the browser.
             */

            if (
                typeof window !== "undefined" &&
                window.location.pathname !== "/signin"
            ) {

                window.location.replace("/signin");

            }

        }


        return Promise.reject(error);

    }
);


/* =========================================================
   CREATE CIVIC ISSUE
========================================================= */

export const createIssue = async ({
    title,
    description,
    category,
    severity,
    location,
    latitude,
    longitude,
    image,
}) => {

    const formData = new FormData();


    formData.append(
        "title",
        title
    );


    formData.append(
        "description",
        description
    );


    formData.append(
        "category",
        category
    );


    formData.append(
        "severity",
        severity
    );


    formData.append(
        "location",
        location
    );


    formData.append(
        "latitude",
        String(latitude)
    );


    formData.append(
        "longitude",
        String(longitude)
    );


    formData.append(
        "image",
        image
    );


    const response = await api.post(
        "/issues/",
        formData
    );


    return response.data;
};


/* =========================================================
   GET ALL CIVIC ISSUES
========================================================= */

export const getIssues = async () => {

    const response = await api.get(
        "/issues/"
    );


    return response.data;
};


/* =========================================================
   GET LOGGED-IN CITIZEN'S ISSUES
========================================================= */

export const getMyIssues = async () => {

    const response = await api.get(
        "/issues/mine"
    );


    return response.data;
};


/* =========================================================
   GET CURRENT CITIZEN PROFILE
========================================================= */

export const getCurrentUser = async () => {

    const response = await api.get(
        "/auth/me"
    );


    return response.data;
};


/* =========================================================
   UPDATE CITIZEN PROFILE
========================================================= */

export const updateCitizenProfile = async ({
    name,
    email,
    preferred_language,
}) => {

    const response = await api.put(
        "/auth/profile",
        {
            name,
            email: email || null,
            preferred_language,
        }
    );


    return response.data;
};


/* =========================================================
   CHANGE CITIZEN PASSWORD
========================================================= */

export const changeCitizenPassword = async ({
    current_password,
    new_password,
}) => {

    const response = await api.put(
        "/auth/change-password",
        {
            current_password,
            new_password,
        }
    );


    return response.data;
};


/* =========================================================
   GET CIVIC REWARD SUMMARY
========================================================= */

export const getRewardSummary = async () => {

    const response = await api.get(
        "/rewards/summary"
    );


    return response.data;
};


/* =========================================================
   GET CIVIC CREDIT HISTORY
========================================================= */

export const getCreditHistory = async () => {

    const response = await api.get(
        "/rewards/history"
    );


    return response.data;
};


/* =========================================================
   GET CITIZEN BADGES
========================================================= */

export const getCitizenBadges = async () => {

    const response = await api.get(
        "/rewards/badges"
    );


    return response.data;
};


/* =========================================================
   CHECK BACKEND HEALTH
========================================================= */

export const checkBackendHealth = async () => {

    const response = await api.get(
        "/health"
    );


    return response.data;
};


/* =========================================================
   SIGN UP
========================================================= */

export const signupCitizen = async (data) => {

    const response = await api.post(
        "/auth/signup",
        data
    );


    return response.data;
};


/* =========================================================
   SIGN IN
========================================================= */

export const signinCitizen = async (data) => {

    const response = await api.post(
        "/auth/signin",
        data
    );


    return response.data;
};


/* =========================================================
   LOGOUT
========================================================= */

export const logoutCitizen = () => {

    localStorage.removeItem(
        "civicsol_access_token"
    );


    localStorage.removeItem(
        "civicsol_citizen"
    );


    delete api.defaults.headers.common.Authorization;

};


/* =========================================================
   PASSWORD RECOVERY
========================================================= */


/* REQUEST PASSWORD RESET */

export const requestPasswordReset = async ({
    channel,
    destination,
}) => {

    const response = await api.post(
        "/auth/forgot-password",
        {
            channel,
            destination,
        }
    );


    return response.data;
};


/* VERIFY RESET OTP */

export const verifyPasswordResetOTP = async ({
    destination,
    otp,
}) => {

    const response = await api.post(
        "/auth/verify-reset-otp",
        {
            destination,
            otp,
        }
    );


    return response.data;
};


/* RESET PASSWORD */

export const resetForgottenPassword = async ({
    destination,
    reset_token,
    new_password,
}) => {

    const response = await api.post(
        "/auth/reset-password",
        {
            destination,
            reset_token,
            new_password,
        }
    );


    return response.data;
};


/* =========================================================
   NOTIFICATIONS API
========================================================= */

export const getUserNotifications = async (params = {}) => {
    const response = await api.get("/notifications/", { params });
    return response.data;
};

export const getUnreadNotificationCount = async () => {
    const response = await api.get("/notifications/unread-count");
    return response.data;
};

export const markNotificationRead = async (notificationId) => {
    const response = await api.put(`/notifications/${notificationId}/read`);
    return response.data;
};

export const markAllNotificationsRead = async () => {
    const response = await api.put("/notifications/read-all");
    return response.data;
};

/* =========================================================
   ISSUE TIMELINE & REOPEN REQUEST
========================================================= */

export const getIssueTimeline = async (issueId) => {
    const response = await api.get(`/issues/${issueId}`);
    return response.data;
};

export const requestIssueReopen = async (issueId, reason) => {
    const response = await api.post(`/issues/${issueId}/reopen-request`, { reason });
    return response.data;
};

/* =========================================================
   EXPORT AXIOS INSTANCE
========================================================= */

export default api;