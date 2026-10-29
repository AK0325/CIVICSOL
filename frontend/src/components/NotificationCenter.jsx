import { useEffect, useRef, useState } from "react";
import { Bell, CheckCheck, Clock, ExternalLink, ShieldAlert } from "lucide-react";
import { useNavigate } from "react-router-dom";
import {
    getUserNotifications,
    getUnreadNotificationCount,
    markNotificationRead,
    markAllNotificationsRead,
} from "../services/api";
import "./NotificationCenter.css";

export default function NotificationCenter({ isAuthority = false }) {
    const [open, setOpen] = useState(false);
    const [notifications, setNotifications] = useState([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [loading, setLoading] = useState(false);
    const dropdownRef = useRef(null);
    const navigate = useNavigate();

    const fetchUnreadCount = async () => {
        try {
            const data = await getUnreadNotificationCount();
            setUnreadCount(data.unread_count || 0);
        } catch {
            // silent catch if unauthenticated
        }
    };

    const fetchNotifications = async () => {
        try {
            setLoading(true);
            const data = await getUserNotifications({ limit: 15 });
            setNotifications(data.notifications || []);
            setUnreadCount(data.unread_count || 0);
        } catch (err) {
            console.error("Failed to fetch notifications:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchUnreadCount();
        const interval = setInterval(fetchUnreadCount, 30000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        if (open) {
            fetchNotifications();
        }
    }, [open]);

    // Close on click outside
    useEffect(() => {
        function handleClickOutside(event) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const handleToggle = () => {
        setOpen(!open);
    };

    const handleMarkAllRead = async (e) => {
        e.stopPropagation();
        try {
            await markAllNotificationsRead();
            setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
            setUnreadCount(0);
        } catch (err) {
            console.error("Failed to mark all as read:", err);
        }
    };

    const handleItemClick = async (notif) => {
        if (!notif.is_read) {
            try {
                await markNotificationRead(notif.id);
                setNotifications((prev) =>
                    prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n))
                );
                setUnreadCount((prev) => Math.max(0, prev - 1));
            } catch {
                // ignore
            }
        }

        setOpen(false);
        if (notif.issue_id) {
            if (isAuthority) {
                navigate(`/authority/issues/${notif.issue_id}`);
            } else {
                navigate("/my-reports");
            }
        }
    };

    const formatTime = (isoString) => {
        if (!isoString) return "";
        const date = new Date(isoString);
        return date.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    };

    return (
        <div className="notif-center" ref={dropdownRef}>
            <button
                type="button"
                className={`notif-bell-btn ${unreadCount > 0 ? "has-unread" : ""}`}
                onClick={handleToggle}
                aria-label="View notifications"
                title="Notifications"
            >
                <Bell size={18} />
                {unreadCount > 0 && (
                    <span className="notif-badge">{unreadCount > 99 ? "99+" : unreadCount}</span>
                )}
            </button>

            {open && (
                <div className="notif-dropdown">
                    <div className="notif-header">
                        <div className="notif-title-row">
                            <h4 className="notif-header-title">Notifications</h4>
                            {unreadCount > 0 && (
                                <span className="notif-unread-tag">{unreadCount} unread</span>
                            )}
                        </div>

                        {unreadCount > 0 && (
                            <button
                                type="button"
                                className="notif-mark-all-btn"
                                onClick={handleMarkAllRead}
                                title="Mark all notifications as read"
                            >
                                <CheckCheck size={14} />
                                <span>Mark all read</span>
                            </button>
                        )}
                    </div>

                    <div className="notif-list">
                        {loading && notifications.length === 0 ? (
                            <div className="notif-loading">
                                <span>Loading notifications...</span>
                            </div>
                        ) : notifications.length === 0 ? (
                            <div className="notif-empty">
                                <ShieldAlert size={28} className="notif-empty-icon" />
                                <p>No notifications yet</p>
                                <span>You will be notified when your civic issues are updated or assigned.</span>
                            </div>
                        ) : (
                            notifications.map((notif) => (
                                <div
                                    key={notif.id}
                                    className={`notif-item ${!notif.is_read ? "unread" : ""}`}
                                    onClick={() => handleItemClick(notif)}
                                    role="button"
                                    tabIndex={0}
                                >
                                    <div className="notif-item-top">
                                        <span className="notif-item-title">{notif.title}</span>
                                        {!notif.is_read && <span className="notif-unread-dot" />}
                                    </div>

                                    <p className="notif-item-msg">{notif.message}</p>

                                    <div className="notif-item-footer">
                                        <span className="notif-item-time">
                                            <Clock size={11} />
                                            {formatTime(notif.created_at)}
                                        </span>
                                        {notif.issue_id && (
                                            <span className="notif-item-link">
                                                <span>View Issue</span>
                                                <ExternalLink size={11} />
                                            </span>
                                        )}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
