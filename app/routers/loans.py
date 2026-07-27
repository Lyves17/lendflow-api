import math
import csv
import io
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from typing import List
from beanie.operators import In

from app.models.user import User, UserRole
from app.models.client import Client
from app.models.loan import Loan, LoanStatus, LoanProduct, Repayment, RepaymentStatus
from app.models.audit import AuditLog, AuditAction
from app.schemas.loan import (
    LoanProductCreate, LoanProductOut, LoanCreate, LoanOut,
    LoanApprove, RepaymentOut, EarlyRepaymentCreate, EarlyRepaymentOut,
    ExtensionCreate, ExtensionOut, CalculatorRequest, CalculatorResponse,
)
from app.core.security import get_current_user
from app.services.notifications import notify_loan_approved, notify_loan_rejected, notify_extension_approved

router = APIRouter(prefix="/loans", tags=["Loans"])


async def log_audit(entity_type: str, entity_id: str, action: AuditAction, user: User, details: dict = None):
    audit = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_id=str(user.id),
        actor_name=user.full_name,
        details=details or {},
    )
    await audit.insert()


def calc_loan(amount, interest_rate, term_days, interest_type, processing_fee_pct):
    if interest_type == "flat":
        interest_amount = amount * (interest_rate / 100)
    elif interest_type == "reducing":
        monthly_rate = interest_rate / 100 / 12
        months = max(1, term_days / 30)
        interest_amount = amount * monthly_rate * months
    else:
        interest_amount = amount * (interest_rate / 100)

    processing_fee = amount * (processing_fee_pct / 100)
    total = amount + interest_amount + processing_fee
    daily = total / max(1, term_days)
    monthly = total / max(1, term_days / 30)
    return {
        "principal": round(amount, 2),
        "interest_amount": round(interest_amount, 2),
        "processing_fee": round(processing_fee, 2),
        "total_amount": round(total, 2),
        "daily_payment": round(daily, 2),
        "monthly_payment": round(monthly, 2),
        "term_days": term_days,
    }


@router.get("/calculator", response_model=CalculatorResponse)
async def loan_calculator(
    amount: float = Query(..., gt=0),
    interest_rate: float = Query(..., gt=0),
    term_days: int = Query(..., gt=0),
    interest_type: str = Query("flat"),
    processing_fee_percent: float = Query(0, ge=0),
):
    return CalculatorResponse(**calc_loan(amount, interest_rate, term_days, interest_type, processing_fee_percent))


@router.get("/products", response_model=List[LoanProductOut])
async def list_products(country_code: str = None):
    query = {}
    if country_code:
        query["country_code"] = country_code
    products = await LoanProduct.find(query).to_list()
    return [LoanProductOut(
        id=str(p.id), name=p.name, description=p.description,
        country_code=p.country_code, currency=p.currency,
        min_amount=p.min_amount, max_amount=p.max_amount,
        min_term_days=p.min_term_days, max_term_days=p.max_term_days,
        interest_rate=p.interest_rate, interest_type=p.interest_type,
        processing_fee=p.processing_fee, late_fee=p.late_fee,
    ) for p in products]


@router.post("/products", response_model=LoanProductOut)
async def create_product(data: LoanProductCreate, user: User = Depends(get_current_user)):
    if user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Accès refusé")
    product = LoanProduct(**data.model_dump())
    await product.insert()
    return LoanProductOut(
        id=str(product.id), name=product.name, description=product.description,
        country_code=product.country_code, currency=product.currency,
        min_amount=product.min_amount, max_amount=product.max_amount,
        min_term_days=product.min_term_days, max_term_days=product.max_term_days,
        interest_rate=product.interest_rate, interest_type=product.interest_type,
        processing_fee=product.processing_fee, late_fee=product.late_fee,
    )


@router.post("/", response_model=LoanOut)
async def create_loan(data: LoanCreate, user: User = Depends(get_current_user)):
    client = await Client.find_one(Client.user_id == str(user.id))
    if not client:
        raise HTTPException(status_code=404, detail="Profil client introuvable")

    product = await LoanProduct.get(data.product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Produit de prêt introuvable")

    if data.amount < product.min_amount or data.amount > product.max_amount:
        raise HTTPException(status_code=400, detail=f"Montant entre {product.min_amount} et {product.max_amount}")
    if data.term_days < product.min_term_days or data.term_days > product.max_term_days:
        raise HTTPException(status_code=400, detail=f"Durée entre {product.min_term_days} et {product.max_term_days} jours")

    calc = calc_loan(data.amount, product.interest_rate, data.term_days, product.interest_type, product.processing_fee)

    loan = Loan(
        client_id=str(client.id),
        product_id=str(product.id),
        amount=data.amount,
        currency=product.currency,
        term_days=data.term_days,
        interest_rate=product.interest_rate,
        interest_amount=calc["interest_amount"],
        processing_fee=calc["processing_fee"],
        total_amount=calc["total_amount"],
        balance=calc["total_amount"],
        purpose=data.purpose,
        status=LoanStatus.PENDING,
        credit_score_at_request=client.credit_score,
    )
    await loan.insert()
    await log_audit("loan", str(loan.id), AuditAction.LOAN_CREATED, user, {"amount": data.amount, "currency": product.currency})

    return LoanOut(
        id=str(loan.id), client_id=loan.client_id, product_id=loan.product_id,
        amount=loan.amount, currency=loan.currency, term_days=loan.term_days,
        interest_rate=loan.interest_rate, interest_amount=loan.interest_amount,
        processing_fee=loan.processing_fee, total_amount=loan.total_amount,
        amount_paid=loan.amount_paid, balance=loan.balance,
        status=loan.status.value, purpose=loan.purpose,
        due_date=str(loan.due_date) if loan.due_date else None,
        created_at=str(loan.created_at),
    )


@router.post("/{loan_id}/approve", response_model=LoanOut)
async def approve_loan(loan_id: str, data: LoanApprove, user: User = Depends(get_current_user)):
    if user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Accès refusé")

    loan = await Loan.get(loan_id)
    if not loan or loan.status != LoanStatus.PENDING:
        raise HTTPException(status_code=404, detail="Prêt introuvable ou déjà traité")

    client = await Client.get(loan.client_id)

    if data.approved:
        loan.status = LoanStatus.APPROVED
        loan.approved_by = str(user.id)
        loan.approved_at = datetime.now(timezone.utc)
        loan.due_date = datetime.now(timezone.utc) + timedelta(days=loan.term_days)

        nb_installments = max(1, loan.term_days // 30)
        installment_amount = loan.total_amount / nb_installments
        for i in range(1, nb_installments + 1):
            repayment = Repayment(
                loan_id=str(loan.id),
                installment_number=i,
                amount_due=round(installment_amount, 2),
                due_date=datetime.now(timezone.utc) + timedelta(days=30 * i),
            )
            await repayment.insert()
        await log_audit("loan", str(loan.id), AuditAction.LOAN_APPROVED, user, {"term_days": loan.term_days})
        try:
            await notify_loan_approved(str(client.id), str(loan.id), loan.amount, loan.currency, phone=client.phone)
        except Exception:
            pass
    else:
        loan.status = LoanStatus.REJECTED
        await log_audit("loan", str(loan.id), AuditAction.LOAN_REJECTED, user, {"reason": data.notes})
        try:
            await notify_loan_rejected(str(client.id), str(loan.id), data.notes, phone=client.phone)
        except Exception:
            pass

    loan.updated_at = datetime.now(timezone.utc)
    await loan.save()

    return LoanOut(
        id=str(loan.id), client_id=loan.client_id, product_id=loan.product_id,
        amount=loan.amount, currency=loan.currency, term_days=loan.term_days,
        interest_rate=loan.interest_rate, interest_amount=loan.interest_amount,
        processing_fee=loan.processing_fee, total_amount=loan.total_amount,
        amount_paid=loan.amount_paid, balance=loan.balance,
        status=loan.status.value, purpose=loan.purpose,
        due_date=str(loan.due_date) if loan.due_date else None,
        created_at=str(loan.created_at),
    )


@router.post("/{loan_id}/disburse")
async def disburse_loan(loan_id: str, user: User = Depends(get_current_user)):
    if user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Accès refusé")

    loan = await Loan.get(loan_id)
    if not loan or loan.status != LoanStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Prêt non approuvé")

    loan.status = LoanStatus.ACTIVE
    loan.disbursed_at = datetime.now(timezone.utc)
    await loan.save()

    client = await Client.get(loan.client_id)
    client.total_loans += 1
    client.total_borrowed += loan.amount
    await client.save()
    await log_audit("loan", str(loan.id), AuditAction.LOAN_DISBURSED, user, {"amount": loan.amount})

    return {"message": "Prêt décaissé", "loan_id": str(loan.id)}


@router.post("/{loan_id}/early-repayment", response_model=EarlyRepaymentOut)
async def early_repayment(data: EarlyRepaymentCreate, user: User = Depends(get_current_user)):
    client = await Client.find_one(Client.user_id == str(user.id))
    if not client:
        raise HTTPException(status_code=404, detail="Profil client introuvable")

    loan = await Loan.get(data.loan_id)
    if not loan or loan.client_id != str(client.id):
        raise HTTPException(status_code=404, detail="Prêt introuvable")
    if loan.status not in [LoanStatus.ACTIVE, LoanStatus.EXTENDED]:
        raise HTTPException(status_code=400, detail="Prêt non actif")

    product = await LoanProduct.get(loan.product_id)
    discount_pct = product.early_repayment_discount if product else 0.0
    discount = loan.balance * (discount_pct / 100) if discount_pct > 0 else 0.0
    amount_to_pay = min(data.amount, loan.balance - discount)

    loan.amount_paid += amount_to_pay
    loan.balance = loan.total_amount - loan.amount_paid

    if loan.balance <= 0 or loan.balance <= 0.01:
        loan.status = LoanStatus.COMPLETED
        loan.completed_at = datetime.now(timezone.utc)
        loan.balance = 0
    await loan.save()

    repayments = await Repayment.find(
        Repayment.loan_id == str(loan.id),
        Repayment.status == RepaymentStatus.PENDING,
    ).sort([("due_date", 1)]).to_list()

    remaining = amount_to_pay
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

    client.total_repaid += amount_to_pay
    await client.save()
    await log_audit("loan", str(loan.id), AuditAction.EARLY_REPAYMENT, user, {"amount": amount_to_pay, "discount": discount})

    return EarlyRepaymentOut(
        id=str(loan.id), loan_id=str(loan.id),
        original_balance=loan.total_amount - loan.amount_paid + amount_to_pay,
        amount_paid=amount_to_pay, discount_applied=discount,
        new_balance=loan.balance, status=loan.status.value,
        created_at=str(datetime.now(timezone.utc)),
    )


@router.post("/{loan_id}/extend", response_model=ExtensionOut)
async def extend_loan(data: ExtensionCreate, user: User = Depends(get_current_user)):
    if user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Accès refusé")

    loan = await Loan.get(data.loan_id)
    if not loan or loan.status not in [LoanStatus.ACTIVE, LoanStatus.EXTENDED]:
        raise HTTPException(status_code=400, detail="Prêt non éligible à une extension")

    product = await LoanProduct.get(loan.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produit introuvable")

    if loan.extensions_used >= product.max_extensions:
        raise HTTPException(status_code=400, detail=f"Maximum {product.max_extensions} extensions atteint")

    ext_fee = loan.balance * (product.extension_fee / 100) if product.extension_fee > 0 else 0
    previous_due = loan.due_date
    loan.due_date = loan.due_date + timedelta(days=data.additional_days)
    loan.extensions_used += 1
    loan.extension_history.append({
        "previous_due": str(previous_due),
        "new_due": str(loan.due_date),
        "days": data.additional_days,
        "fee": ext_fee,
        "reason": data.reason,
        "at": str(datetime.now(timezone.utc)),
    })
    loan.status = LoanStatus.EXTENDED
    loan.updated_at = datetime.now(timezone.utc)
    await loan.save()
    await log_audit("loan", str(loan.id), AuditAction.LOAN_EXTENDED, user, {"additional_days": data.additional_days, "fee": ext_fee})

    client = await Client.get(loan.client_id)
    if client:
        try:
            await notify_extension_approved(str(client.id), str(loan.id), str(loan.due_date), phone=client.phone)
        except Exception:
            pass

    return ExtensionOut(
        id=str(loan.id), loan_id=str(loan.id),
        previous_due_date=str(previous_due),
        new_due_date=str(loan.due_date),
        extension_days=data.additional_days,
        extension_fee=ext_fee,
        extensions_remaining=product.max_extensions - loan.extensions_used,
        created_at=str(datetime.now(timezone.utc)),
    )


@router.get("/me", response_model=List[LoanOut])
async def get_my_loans(user: User = Depends(get_current_user)):
    client = await Client.find_one(Client.user_id == str(user.id))
    if not client:
        raise HTTPException(status_code=404, detail="Profil client introuvable")
    loans = await Loan.find(Loan.client_id == str(client.id)).to_list()
    return [LoanOut(
        id=str(l.id), client_id=l.client_id, product_id=l.product_id,
        amount=l.amount, currency=l.currency, term_days=l.term_days,
        interest_rate=l.interest_rate, interest_amount=l.interest_amount,
        processing_fee=l.processing_fee, total_amount=l.total_amount,
        amount_paid=l.amount_paid, balance=l.balance,
        status=l.status.value, purpose=l.purpose,
        due_date=str(l.due_date) if l.due_date else None,
        created_at=str(l.created_at),
    ) for l in loans]


@router.get("/{loan_id}/repayments", response_model=List[RepaymentOut])
async def get_repayments(loan_id: str, user: User = Depends(get_current_user)):
    repayments = await Repayment.find(Repayment.loan_id == loan_id).to_list()
    return [RepaymentOut(
        id=str(r.id), loan_id=r.loan_id, installment_number=r.installment_number,
        amount_due=r.amount_due, amount_paid=r.amount_paid,
        due_date=str(r.due_date), status=r.status.value, late_fee=r.late_fee,
    ) for r in repayments]


@router.get("/{loan_id}/history")
async def get_loan_history(loan_id: str, user: User = Depends(get_current_user)):
    logs = await AuditLog.find(
        AuditLog.entity_type == "loan",
        AuditLog.entity_id == loan_id,
    ).sort([("created_at", -1)]).to_list()
    return [{"action": l.action.value, "actor": l.actor_name, "details": l.details,
             "timestamp": str(l.created_at)} for l in logs]


@router.get("/overdue")
async def get_overdue_loans(user: User = Depends(get_current_user)):
    if user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.AGENT]:
        raise HTTPException(status_code=403, detail="Accès refusé")

    now = datetime.now(timezone.utc)
    active_loans = await Loan.find(In(Loan.status, [LoanStatus.ACTIVE, LoanStatus.EXTENDED])).to_list()
    overdue = []
    for loan in active_loans:
        if loan.due_date and loan.due_date < now:
            days_overdue = (now - loan.due_date).days
            client = await Client.get(loan.client_id)
            overdue.append({
                "loan_id": str(loan.id),
                "client_name": client.full_name if client else "N/A",
                "phone": client.phone if client else "N/A",
                "amount": loan.amount,
                "balance": loan.balance,
                "days_overdue": days_overdue,
                "due_date": str(loan.due_date),
            })
    return sorted(overdue, key=lambda x: x["days_overdue"], reverse=True)


@router.get("/export")
async def export_loans_csv(user: User = Depends(get_current_user)):
    if user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Accès refusé")

    loans = await Loan.find_all().to_list()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Client ID", "Amount", "Currency", "Status", "Balance", "Paid", "Created"])
    for l in loans:
        writer.writerow([str(l.id), l.client_id, l.amount, l.currency, l.status.value,
                         l.balance, l.amount_paid, str(l.created_at)])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=loans_export.csv"},
    )
