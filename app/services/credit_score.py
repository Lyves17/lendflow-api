from datetime import datetime, timezone

from app.core.config import settings
from app.models.client import Client
from app.models.loan import Loan, LoanStatus
from app.models.audit import AuditLog, AuditAction


def calculate_credit_score(client: Client, loans: list[Loan]) -> dict:
    score = 500
    factors = {}

    total_loans = len(loans)
    completed = [l for l in loans if l.status == LoanStatus.COMPLETED]
    defaulted = [l for l in loans if l.status == LoanStatus.DEFAULTED]
    active = [l for l in loans if l.status in (LoanStatus.ACTIVE, LoanStatus.EXTENDED)]

    if total_loans == 0:
        factors["history"] = "Aucun historique de prêt"
    else:
        completion_rate = len(completed) / total_loans
        score += int(completion_rate * 150)
        factors["completion_rate"] = f"{completion_rate * 100:.0f}%"

    if total_loans >= 3:
        score += 50
        factors["experience"] = "Client expérimenté (3+ prêts)"

    if total_loans >= 5:
        score += 30
        factors["loyalty"] = "Client fidèle (5+ prêts)"

    default_penalty = len(defaulted) * 100
    score -= default_penalty
    if defaulted:
        factors["defaults"] = f"{len(defaulted)} défaut(s) (-{default_penalty} pts)"

    if client.total_repaid > 0 and client.total_borrowed > 0:
        repay_ratio = client.total_repaid / client.total_borrowed
        if repay_ratio >= 1.0:
            score += 50
            factors["repayment"] = "Remboursement complet"
        elif repay_ratio >= 0.5:
            score += 20
            factors["repayment"] = f"Remboursement à {repay_ratio * 100:.0f}%"

    if not defaulted and total_loans >= 2:
        score += 50
        factors["no_default"] = "Aucun défaut récent"

    active_overdue = 0
    now = datetime.now(timezone.utc)
    for l in active:
        if l.due_date and l.due_date < now:
            active_overdue += 1
    if active_overdue > 0:
        penalty = active_overdue * 75
        score -= penalty
        factors["overdue"] = f"{active_overdue} prêt(s) en retard (-{penalty} pts)"

    score = max(300, min(850, score))

    if score >= 700:
        risk = "low"
    elif score >= 600:
        risk = "medium"
    elif score >= 500:
        risk = "high"
    else:
        risk = "very_high"

    max_loan = 0
    if risk == "low":
        max_loan = 50000
    elif risk == "medium":
        max_loan = 20000
    elif risk == "high":
        max_loan = 5000
    else:
        max_loan = 1000

    recommended = []
    if risk in ("low", "medium"):
        recommended.append("standard_loan")
    if risk == "low":
        recommended.append("premium_loan")
    if risk in ("high", "very_high"):
        recommended.append("micro_loan")

    return {
        "current_score": score,
        "factors": factors,
        "max_loan_amount": max_loan,
        "recommended_products": recommended,
        "risk_level": risk,
    }


async def update_client_credit_score(client_id: str) -> dict:
    client = await Client.get(client_id)
    if not client:
        raise ValueError("Client introuvable")

    loans = await Loan.find(Loan.client_id == client_id).to_list()
    result = calculate_credit_score(client, loans)

    old_score = client.credit_score
    client.credit_score = result["current_score"]
    client.updated_at = datetime.now(timezone.utc)
    await client.save()

    await AuditLog(
        entity_type="client",
        entity_id=client_id,
        action=AuditAction.CREDIT_SCORE_UPDATED,
        details={"old_score": old_score, "new_score": result["current_score"], "factors": result["factors"]},
    ).insert()

    return result
