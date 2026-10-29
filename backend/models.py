from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


# =========================================================
# MUNICIPAL DEPARTMENT MODEL
# =========================================================

class Department(Base):
    __tablename__ = "departments"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    name = Column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    code = Column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    description = Column(
        Text,
        nullable=True,
    )

    contact_email = Column(
        String(255),
        nullable=True,
    )

    contact_phone = Column(
        String(20),
        nullable=True,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # -----------------------------------------------------
    # Relationships
    # -----------------------------------------------------

    officers = relationship(
        "User",
        back_populates="department",
        foreign_keys="[User.department_id]",
    )

    issues = relationship(
        "CivicIssue",
        back_populates="department_rel",
        foreign_keys="[CivicIssue.department_id]",
    )


# =========================================================
# USER / CITIZEN / OFFICER MODEL
# =========================================================

class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    name = Column(
        String(100),
        nullable=False,
    )

    email = Column(
        String(255),
        unique=True,
        index=True,
        nullable=True,
    )

    mobile = Column(
        String(15),
        unique=True,
        index=True,
        nullable=False,
    )

    password_hash = Column(
        String(255),
        nullable=False,
    )

    preferred_language = Column(
        String(20),
        nullable=False,
        default="English",
    )

    citizen_id = Column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    ward = Column(
        String(100),
        nullable=True,
    )

    zone = Column(
        String(100),
        nullable=True,
    )

    # -----------------------------------------------------
    # Authority & Administrative extensions
    # -----------------------------------------------------

    role = Column(
        String(30),
        nullable=False,
        default="CITIZEN",
        server_default="CITIZEN",
        index=True,
    )

    department_id = Column(
        Integer,
        ForeignKey(
            "departments.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    designation = Column(
        String(100),
        nullable=True,
    )

    employee_id = Column(
        String(50),
        unique=True,
        index=True,
        nullable=True,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # -----------------------------------------------------
    # Relationships
    # -----------------------------------------------------

    issues = relationship(
        "CivicIssue",
        back_populates="user",
        foreign_keys="[CivicIssue.user_id]",
    )

    assigned_issues = relationship(
        "CivicIssue",
        back_populates="assigned_officer",
        foreign_keys="[CivicIssue.assigned_officer_id]",
    )

    department = relationship(
        "Department",
        back_populates="officers",
        foreign_keys="[User.department_id]",
    )

    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="[Notification.user_id]",
    )


# =========================================================
# CIVIC ISSUE MODEL
# =========================================================

class CivicIssue(Base):
    __tablename__ = "civic_issues"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # -----------------------------------------------------
    # Citizen ownership
    # -----------------------------------------------------

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    user = relationship(
        "User",
        back_populates="issues",
        foreign_keys="[CivicIssue.user_id]",
    )

    # -----------------------------------------------------
    # Basic issue information
    # -----------------------------------------------------

    title = Column(
        String(200),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=True,
    )

    category = Column(
        String(100),
        nullable=False,
        index=True,
    )

    severity = Column(
        String(50),
        nullable=False,
        default="Medium",
    )

    # -----------------------------------------------------
    # Location
    # -----------------------------------------------------

    location = Column(
        String(500),
        nullable=False,
    )

    latitude = Column(
        Float,
        nullable=False,
    )

    longitude = Column(
        Float,
        nullable=False,
    )

    ward = Column(
        String(100),
        nullable=True,
    )

    # -----------------------------------------------------
    # Evidence
    # -----------------------------------------------------

    image_path = Column(
        String(500),
        nullable=False,
    )

    # -----------------------------------------------------
    # Issue status
    # -----------------------------------------------------

    status = Column(
        String(50),
        nullable=False,
        default="Reported",
        index=True,
    )

    priority = Column(
        String(50),
        nullable=False,
        default="Medium",
        index=True,
    )

    # -----------------------------------------------------
    # AI ANALYSIS
    # -----------------------------------------------------

    ai_label = Column(
        String(100),
        nullable=True,
    )

    ai_confidence = Column(
        Float,
        nullable=True,
    )

    # -----------------------------------------------------
    # CIVIC INTELLIGENCE & LEGACY DEPARTMENT STRING
    # -----------------------------------------------------

    priority_score = Column(
        Float,
        nullable=True,
    )

    department = Column(
        String(100),
        nullable=True,
    )

    cluster_id = Column(
        Integer,
        nullable=True,
    )

    report_count = Column(
        Integer,
        nullable=False,
        default=1,
    )

    # -----------------------------------------------------
    # AUTHORITY ASSIGNMENT & RESOLUTION EXTENSIONS
    # -----------------------------------------------------

    department_id = Column(
        Integer,
        ForeignKey(
            "departments.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    assigned_officer_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    assigned_by_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    assigned_at = Column(
        DateTime,
        nullable=True,
    )

    resolution_notes = Column(
        Text,
        nullable=True,
    )

    resolution_image_path = Column(
        String(500),
        nullable=True,
    )

    resolved_by_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    resolved_at = Column(
        DateTime,
        nullable=True,
    )

    rejection_reason = Column(
        Text,
        nullable=True,
    )

    # -----------------------------------------------------
    # TIMESTAMPS
    # -----------------------------------------------------

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    # -----------------------------------------------------
    # Authority Relationships
    # -----------------------------------------------------

    department_rel = relationship(
        "Department",
        back_populates="issues",
        foreign_keys="[CivicIssue.department_id]",
    )

    assigned_officer = relationship(
        "User",
        back_populates="assigned_issues",
        foreign_keys="[CivicIssue.assigned_officer_id]",
    )

    assigned_by = relationship(
        "User",
        foreign_keys="[CivicIssue.assigned_by_id]",
    )

    resolved_by = relationship(
        "User",
        foreign_keys="[CivicIssue.resolved_by_id]",
    )

    status_history = relationship(
        "IssueStatusHistory",
        back_populates="issue",
        cascade="all, delete-orphan",
        order_by="IssueStatusHistory.created_at.desc()",
    )


# =========================================================
# ISSUE STATUS HISTORY MODEL
# =========================================================

class IssueStatusHistory(Base):
    __tablename__ = "issue_status_history"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    issue_id = Column(
        Integer,
        ForeignKey(
            "civic_issues.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    from_status = Column(
        String(50),
        nullable=True,
    )

    to_status = Column(
        String(50),
        nullable=False,
        index=True,
    )

    changed_by_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    comment = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    # -----------------------------------------------------
    # Relationships
    # -----------------------------------------------------

    issue = relationship(
        "CivicIssue",
        back_populates="status_history",
        foreign_keys="[IssueStatusHistory.issue_id]",
    )

    changed_by = relationship(
        "User",
        foreign_keys="[IssueStatusHistory.changed_by_id]",
    )


# =========================================================
# AUDIT LOG MODEL
# =========================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    action = Column(
        String(100),
        nullable=False,
        index=True,
    )

    entity_type = Column(
        String(50),
        nullable=False,
        index=True,
    )

    entity_id = Column(
        Integer,
        nullable=True,
        index=True,
    )

    details = Column(
        Text,
        nullable=True,
    )

    ip_address = Column(
        String(50),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    # -----------------------------------------------------
    # Relationships
    # -----------------------------------------------------

    user = relationship(
        "User",
        foreign_keys="[AuditLog.user_id]",
    )


# =========================================================
# REWARD & REPUTATION MODELS (PRESERVED)
# =========================================================

class CivicCreditTransaction(Base):
    __tablename__ = "civic_credit_transactions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        nullable=False,
    )

    issue_id = Column(
        Integer,
        nullable=True,
    )

    action = Column(
        String(100),
        nullable=False,
    )

    description = Column(
        String(255),
        nullable=True,
    )

    credits = Column(
        Integer,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class Badge(Base):
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True)

    code = Column(
        String(50),
        unique=True,
        nullable=False,
    )

    name = Column(
        String(100),
        nullable=False,
    )

    description = Column(
        String(255),
        nullable=True,
    )

    icon = Column(
        String(100),
        nullable=True,
    )

    requirement_type = Column(
        String(50),
        nullable=True,
    )

    requirement_value = Column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class UserBadge(Base):
    __tablename__ = "user_badges"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        nullable=False,
    )

    badge_id = Column(
        Integer,
        nullable=False,
    )

    earned_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# =========================================================
# PASSWORD RESET OTP (PRESERVED)
# =========================================================

class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    channel = Column(
        String(20),
        nullable=False,
    )

    destination = Column(
        String(255),
        nullable=False,
    )

    otp_hash = Column(
        String(255),
        nullable=False,
    )

    expires_at = Column(
        DateTime,
        nullable=False,
    )

    attempts = Column(
        Integer,
        nullable=False,
        default=0,
    )

    verified = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    used_at = Column(
        DateTime,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# =========================================================
# CITIZEN & OFFICER IN-APP NOTIFICATION MODEL
# =========================================================

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    title = Column(
        String(150),
        nullable=False,
    )

    message = Column(
        Text,
        nullable=False,
    )

    notification_type = Column(
        String(50),
        nullable=False,
        index=True,
    )

    entity_type = Column(
        String(50),
        nullable=True,
        default="CIVIC_ISSUE",
        index=True,
    )

    entity_id = Column(
        Integer,
        nullable=True,
        index=True,
    )

    is_read = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    # -----------------------------------------------------
    # Relationships
    # -----------------------------------------------------

    user = relationship(
        "User",
        back_populates="notifications",
        foreign_keys="[Notification.user_id]",
    )