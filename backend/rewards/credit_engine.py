from sqlalchemy.orm import Session

from ..models import CivicCreditTransaction


# =========================================================
# CIVIC CREDIT VALUES
# =========================================================

CREDIT_VALUES = {
    "valid_report": 10,
    "clear_evidence": 5,
    "gps_evidence": 5,
    "ai_confirmation": 10,
    "authority_verification": 20,
    "issue_resolved": 25,
    "resolution_confirmation": 15,
    "helpful_duplicate": 5,
    "false_report": -20,
    "fraudulent_report": -50,
}


# =========================================================
# ADD CREDIT TRANSACTION
# =========================================================

def add_credit_transaction(
    db: Session,
    user_id: int,
    action: str,
    description: str,
    issue_id: int | None = None,
):
    """
    Add a civic credit transaction for a citizen.
    """

    credits = CREDIT_VALUES.get(action)

    if credits is None:
        raise ValueError(
            f"Unknown civic credit action: {action}"
        )

    transaction = CivicCreditTransaction(
        user_id=user_id,
        issue_id=issue_id,
        action=action,
        description=description,
        credits=credits,
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return transaction


# =========================================================
# GET TOTAL CREDITS
# =========================================================

def get_total_credits(
    db: Session,
    user_id: int,
) -> int:

    transactions = (
        db.query(CivicCreditTransaction)
        .filter(
            CivicCreditTransaction.user_id == user_id
        )
        .all()
    )

    return sum(
        transaction.credits
        for transaction in transactions
    )