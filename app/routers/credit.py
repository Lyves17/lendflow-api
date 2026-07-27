from fastapi import APIRouter, HTTPException, Depends

from app.models.user import User, UserRole
from app.models.client import Client
from app.schemas.loan import CreditScoreOut
from app.services.credit_score import update_client_credit_score
from app.core.security import get_current_user

router = APIRouter(prefix="/credit", tags=["Credit Score"])


@router.get("/score/{client_id}", response_model=CreditScoreOut)
async def get_credit_score(client_id: str, user: User = Depends(get_current_user)):
    if user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.AGENT]:
        client = await Client.find_one(Client.user_id == str(user.id))
        if not client or str(client.id) != client_id:
            raise HTTPException(status_code=403, detail="Accès refusé")

    try:
        result = await update_client_credit_score(client_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return CreditScoreOut(
        client_id=client_id,
        current_score=result["current_score"],
        factors=result["factors"],
        max_loan_amount=result["max_loan_amount"],
        recommended_products=result["recommended_products"],
        risk_level=result["risk_level"],
    )


@router.get("/score", response_model=CreditScoreOut)
async def get_my_credit_score(user: User = Depends(get_current_user)):
    client = await Client.find_one(Client.user_id == str(user.id))
    if not client:
        raise HTTPException(status_code=404, detail="Profil client introuvable")

    try:
        result = await update_client_credit_score(str(client.id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return CreditScoreOut(
        client_id=str(client.id),
        current_score=result["current_score"],
        factors=result["factors"],
        max_loan_amount=result["max_loan_amount"],
        recommended_products=result["recommended_products"],
        risk_level=result["risk_level"],
    )
