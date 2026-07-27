from fastapi import APIRouter, Depends
from beanie.operators import In

from app.models.user import User, UserRole
from app.models.client import Client
from app.models.loan import Loan, LoanStatus, LoanProduct
from app.models.payment import Payment, PaymentStatus
from app.core.security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_stats(user: User = Depends(get_current_user)):
    if user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Accès refusé")

    total_clients = await Client.find_all().count()
    total_loans = await Loan.find_all().count()
    active_loans = await Loan.find(Loan.status == LoanStatus.ACTIVE).count()
    total_disbursed = sum([l.amount for l in await Loan.find(In(Loan.status, [LoanStatus.ACTIVE, LoanStatus.COMPLETED, LoanStatus.DISBURSED])).to_list()])
    total_collected = sum([l.amount_paid for l in await Loan.find(In(Loan.status, [LoanStatus.ACTIVE, LoanStatus.COMPLETED])).to_list()])
    total_payments = await Payment.find_all().count()
    successful_payments = await Payment.find(Payment.status == PaymentStatus.SUCCESS).count()
    pending_loans = await Loan.find(Loan.status == LoanStatus.PENDING).count()
    defaulted = await Loan.find(Loan.status == LoanStatus.DEFAULTED).count()

    return {
        "total_clients": total_clients,
        "total_loans": total_loans,
        "active_loans": active_loans,
        "pending_loans": pending_loans,
        "defaulted_loans": defaulted,
        "total_disbursed": round(total_disbursed, 2),
        "total_collected": round(total_collected, 2),
        "collection_rate": round((total_collected / total_disbursed * 100), 1) if total_disbursed > 0 else 0,
        "total_payments": total_payments,
        "successful_payments": successful_payments,
    }


@router.get("/loans")
async def list_all_loans(user: User = Depends(get_current_user)):
    if user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.AGENT]:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Accès refusé")
    loans = await Loan.find_all().to_list()
    return [{"id": str(l.id), "client_id": l.client_id, "amount": l.amount,
             "currency": l.currency, "status": l.status.value,
             "balance": l.balance, "created_at": str(l.created_at)} for l in loans]
