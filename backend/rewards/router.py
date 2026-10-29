from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user
from ..database import get_db
from ..models import (
    User,
    CivicCreditTransaction,
    Badge,
    UserBadge,
)

from .credit_engine import get_total_credits


router = APIRouter(
    prefix="/rewards",
    tags=["Civic Rewards"],
)


# =========================================================
# LEVEL CALCULATION
# =========================================================

def get_civic_level(credits: int):

    if credits >= 1000:
        return {
            "name": "Civic Ambassador",
            "start": 1000,
            "target": 1500,
        }

    if credits >= 500:
        return {
            "name": "Civic Leader",
            "start": 500,
            "target": 1000,
        }

    if credits >= 250:
        return {
            "name": "Civic Champion",
            "start": 250,
            "target": 500,
        }

    if credits >= 100:
        return {
            "name": "Civic Contributor",
            "start": 100,
            "target": 250,
        }

    return {
        "name": "Civic Observer",
        "start": 0,
        "target": 100,
    }


# =========================================================
# REWARD SUMMARY
# =========================================================

@router.get("/summary")
def get_reward_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    total_credits = get_total_credits(
        db,
        current_user.id,
    )

    level = get_civic_level(
        total_credits
    )

    progress = 0

    if level["target"] > level["start"]:

        progress = (
            (
                total_credits
                - level["start"]
            )
            /
            (
                level["target"]
                - level["start"]
            )
        ) * 100

    progress = min(
        100,
        max(0, progress)
    )

    return {
        "credits": total_credits,
        "level": level["name"],
        "level_start": level["start"],
        "level_target": level["target"],
        "progress": round(progress, 2),
        "citizen_id": current_user.citizen_id,
        "name": current_user.name,
    }


# =========================================================
# CREDIT HISTORY
# =========================================================

@router.get("/history")
def get_credit_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    transactions = (
        db.query(CivicCreditTransaction)
        .filter(
            CivicCreditTransaction.user_id
            == current_user.id
        )
        .order_by(
            CivicCreditTransaction.created_at.desc()
        )
        .all()
    )

    return [
        {
            "id": transaction.id,
            "action": transaction.action,
            "description": transaction.description,
            "credits": transaction.credits,
            "issue_id": transaction.issue_id,
            "created_at": transaction.created_at,
        }
        for transaction in transactions
    ]


# =========================================================
# BADGES
# =========================================================

@router.get("/badges")
def get_badges(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    badges = (
        db.query(
            Badge,
            UserBadge.earned_at,
        )
        .outerjoin(
            UserBadge,
            (
                UserBadge.badge_id == Badge.id
            )
            &
            (
                UserBadge.user_id
                == current_user.id
            )
        )
        .order_by(Badge.id)
        .all()
    )

    return [
        {
            "id": badge.id,
            "code": badge.code,
            "name": badge.name,
            "description": badge.description,
            "icon": badge.icon,
            "earned": earned_at is not None,
            "earned_at": earned_at,
        }
        for badge, earned_at in badges
    ]