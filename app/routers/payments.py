from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from typing import List

from app.models.user import User
from app.models.client import Client
from app.models.loan import Loan, LoanStatus, Repayment, RepaymentStatus
from app.models.payment import Payment, PaymentStatus
from app.schemas.payment import PaymentCreate, PaymentOut
from app.core.security import get_current_user
from app.services.notifications import notify_payment_received

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/", response_model=PaymentOut)
async def create_payment(data: PaymentCreate, user: User = Depends(get_current_user)):
    client = await Client.find_one(Client.user_id == str(user.id))
    if not client:
        raise HTTPException(status_code=404, detail="Profil client introuvable")

    loan = await Loan.get(data.loan_id)
    if not loan or loan.client_id != str(client.id):
        raise HTTPException(status_code=404, detail="Prêt introuvable")
    if loan.status not in [LoanStatus.ACTIVE, LoanStatus.DISBURSED]:
        raise HTTPException(status_code=400, detail="Prêt non actif")

    payment = Payment(
        loan_id=str(loan.id),
        client_id=str(client.id),
        amount=data.amount,
        currency=loan.currency,
        provider=data.provider,
        status=PaymentStatus.PENDING,
    )
    await payment.insert()

    payment.status = PaymentStatus.SUCCESS
    payment.completed_at = datetime.now(timezone.utc)
    await payment.save()

    loan.amount_paid += data.amount
    loan.balance = loan.total_amount - loan.amount_paid

    if loan.balance <= 0:
        loan.status = LoanStatus.COMPLETED
        loan.completed_at = datetime.now(timezone.utc)
    await loan.save()

    repayments = await Repayment.find(
        Repayment.loan_id == str(loan.id),
        Repayment.status == RepaymentStatus.PENDING,
    ).sort([("due_date", 1)]).to_list()

    remaining = data.amount
    for r in repayments:
        if remaining <= 0:
            break
        to_pay = min(remaining, r.amount_due - r.amount_paid)
        r.amount_paid += to_pay
        remaining -= to_pay
        if r.amount_paid >= r.amount_due:
            r.status = RepaymentStatus.PAID
            r.paid_date = datetime.now(timezone.utc)
        await r.save()

    client.total_repaid += data.amount
    await client.save()

    try:
        await notify_payment_received(
            client_id=str(client.id),
            loan_id=str(loan.id),
            amount=data.amount,
            currency=loan.currency,
            phone=client.phone,
        )
    except Exception:
        pass

    return PaymentOut(
        id=str(payment.id), loan_id=payment.loan_id,
        client_id=payment.client_id, amount=payment.amount,
        currency=payment.currency, provider=payment.provider.value,
        status=payment.status.value, provider_tx_id=payment.provider_tx_id,
        created_at=str(payment.created_at),
    )


@router.get("/me", response_model=List[PaymentOut])
async def get_my_payments(user: User = Depends(get_current_user)):
    client = await Client.find_one(Client.user_id == str(user.id))
    if not client:
        raise HTTPException(status_code=404, detail="Profil client introuvable")

    payments = await Payment.find(Payment.client_id == str(client.id)).to_list()
    return [PaymentOut(
        id=str(p.id), loan_id=p.loan_id, client_id=p.client_id,
        amount=p.amount, currency=p.currency, provider=p.provider.value,
        status=p.status.value, provider_tx_id=p.provider_tx_id,
        created_at=str(p.created_at),
    ) for p in payments]
