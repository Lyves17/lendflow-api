from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List
from beanie.operators import In

from app.models.user import User, UserRole
from app.models.client import Client
from app.models.loan import Loan, LoanStatus, Repayment, RepaymentStatus
from app.models.audit import AuditLog, AuditAction
from app.schemas.loan import ReminderOut
from app.services.notifications import notify_reminder_due, notify_reminder_overdue
from app.core.security import get_current_user

router = APIRouter(prefix="/reminders", tags=["Reminders"])


@router.get("/upcoming")
async def upcoming_reminders(user: User = Depends(get_current_user)):
    if user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.AGENT]:
        raise HTTPException(status_code=403, detail="Accès refusé")

    now = datetime.now(timezone.utc)
    upcoming_limit = now + timedelta(days=3)

    active_loans = await Loan.find(
        In(Loan.status, [LoanStatus.ACTIVE, LoanStatus.EXTENDED])
    ).to_list()

    reminders = []
    for loan in active_loans:
        if loan.due_date and now < loan.due_date <= upcoming_limit:
            days_until = (loan.due_date - now).days
            client = await Client.get(loan.client_id)
            pending_repayments = await Repayment.find(
                Repayment.loan_id == str(loan.id),
                Repayment.status == RepaymentStatus.PENDING,
            ).sort([("due_date", 1)]).to_list()

            next_payment = pending_repayments[0] if pending_repayments else None
            amount_due = next_payment.amount_due if next_payment else loan.balance

            reminders.append({
                "loan_id": str(loan.id),
                "client_name": client.full_name if client else "N/A",
                "phone": client.phone if client else "N/A",
                "days_until_due": days_until,
                "amount_due": amount_due,
                "due_date": str(loan.due_date),
                "status": "upcoming",
            })

    return sorted(reminders, key=lambda x: x["days_until_due"])


@router.get("/overdue", response_model=List[ReminderOut])
async def overdue_reminders(user: User = Depends(get_current_user)):
    if user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.AGENT]:
        raise HTTPException(status_code=403, detail="Accès refusé")

    now = datetime.now(timezone.utc)
    active_loans = await Loan.find(
        In(Loan.status, [LoanStatus.ACTIVE, LoanStatus.EXTENDED])
    ).to_list()

    overdue = []
    for loan in active_loans:
        if loan.due_date and loan.due_date < now:
            days_overdue = (now - loan.due_date).days
            client = await Client.get(loan.client_id)

            pending_repayments = await Repayment.find(
                Repayment.loan_id == str(loan.id),
                Repayment.status == RepaymentStatus.PENDING,
            ).sort([("due_date", 1)]).to_list()

            amount_overdue = sum(r.amount_due - r.amount_paid for r in pending_repayments)
            reminder_count = await AuditLog.find(
                AuditLog.entity_type == "loan",
                AuditLog.entity_id == str(loan.id),
                AuditLog.action == AuditAction.REMINDER_SENT,
            ).count()

            overdue.append(ReminderOut(
                id=str(loan.id),
                loan_id=str(loan.id),
                client_name=client.full_name if client else "N/A",
                phone=client.phone if client else "N/A",
                days_overdue=days_overdue,
                amount_due=loan.balance,
                amount_overdue=round(amount_overdue, 2),
                reminder_count=reminder_count,
                last_reminder=str(reminder_count),
                status="overdue",
            ))

    return sorted(overdue, key=lambda x: x.days_overdue, reverse=True)


@router.post("/send-overdue")
async def send_overdue_reminders(user: User = Depends(get_current_user)):
    if user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Accès refusé")

    now = datetime.now(timezone.utc)
    active_loans = await Loan.find(
        In(Loan.status, [LoanStatus.ACTIVE, LoanStatus.EXTENDED])
    ).to_list()

    sent_count = 0
    for loan in active_loans:
        if loan.due_date and loan.due_date < now:
            days_overdue = (now - loan.due_date).days
            client = await Client.get(loan.client_id)
            if not client:
                continue

            await notify_reminder_overdue(
                client_id=str(client.id),
                loan_id=str(loan.id),
                days_overdue=days_overdue,
                amount=loan.balance,
                phone=client.phone,
            )

            await AuditLog(
                entity_type="loan",
                entity_id=str(loan.id),
                action=AuditAction.REMINDER_SENT,
                details={"days_overdue": days_overdue, "amount": loan.balance},
            ).insert()
            sent_count += 1

    return {"message": f"{sent_count} rappel(s) envoyé(s)", "count": sent_count}


@router.post("/send-upcoming")
async def send_upcoming_reminders(user: User = Depends(get_current_user)):
    if user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Accès refusé")

    now = datetime.now(timezone.utc)
    upcoming_limit = now + timedelta(days=2)

    active_loans = await Loan.find(
        In(Loan.status, [LoanStatus.ACTIVE, LoanStatus.EXTENDED])
    ).to_list()

    sent_count = 0
    for loan in active_loans:
        if loan.due_date and now < loan.due_date <= upcoming_limit:
            days_before = (loan.due_date - now).days
            client = await Client.get(loan.client_id)
            if not client:
                continue

            pending_repayments = await Repayment.find(
                Repayment.loan_id == str(loan.id),
                Repayment.status == RepaymentStatus.PENDING,
            ).sort([("due_date", 1)]).to_list()

            next_payment = pending_repayments[0] if pending_repayments else None
            amount = next_payment.amount_due if next_payment else loan.balance

            await notify_reminder_due(
                client_id=str(client.id),
                loan_id=str(loan.id),
                days_before=days_before,
                amount=amount,
                phone=client.phone,
            )

            await AuditLog(
                entity_type="loan",
                entity_id=str(loan.id),
                action=AuditAction.REMINDER_SENT,
                details={"days_before": days_before, "amount": amount, "type": "upcoming"},
            ).insert()
            sent_count += 1

    return {"message": f"{sent_count} rappel(s) à venir envoyé(s)", "count": sent_count}
