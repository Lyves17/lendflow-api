from fastapi import APIRouter, HTTPException, Depends
from typing import List

from app.models.user import User, UserRole
from app.models.client import Client, KYCStatus
from app.schemas.client import ClientCreate, KYCSubmit, ClientOut
from app.core.security import get_current_user

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("/", response_model=ClientOut)
async def create_client(data: ClientCreate, user: User = Depends(get_current_user)):
    existing = await Client.find_one(Client.user_id == str(user.id))
    if existing:
        raise HTTPException(status_code=400, detail="Profil client déjà créé")

    client = Client(
        user_id=str(user.id),
        phone=data.phone,
        country_code=data.country_code,
        region=data.region,
        currency=data.currency,
        full_name=data.full_name or user.full_name,
        date_of_birth=data.date_of_birth,
        nationality=data.nationality,
        id_type=data.id_type,
        id_number=data.id_number,
        address=data.address,
        city=data.city,
    )
    await client.insert()
    return ClientOut(
        id=str(client.id), user_id=client.user_id, phone=client.phone,
        country_code=client.country_code, region=client.region, currency=client.currency,
        full_name=client.full_name, kyc_status=client.kyc_status.value,
        credit_score=client.credit_score, total_loans=client.total_loans,
        total_repaid=client.total_repaid, total_borrowed=client.total_borrowed,
        default_count=client.default_count,
    )


@router.get("/me", response_model=ClientOut)
async def get_my_client(user: User = Depends(get_current_user)):
    client = await Client.find_one(Client.user_id == str(user.id))
    if not client:
        raise HTTPException(status_code=404, detail="Profil client introuvable")
    return ClientOut(
        id=str(client.id), user_id=client.user_id, phone=client.phone,
        country_code=client.country_code, region=client.region, currency=client.currency,
        full_name=client.full_name, kyc_status=client.kyc_status.value,
        credit_score=client.credit_score, total_loans=client.total_loans,
        total_repaid=client.total_repaid, total_borrowed=client.total_borrowed,
        default_count=client.default_count,
    )


@router.post("/kyc", response_model=ClientOut)
async def submit_kyc(data: KYCSubmit, user: User = Depends(get_current_user)):
    client = await Client.find_one(Client.user_id == str(user.id))
    if not client:
        raise HTTPException(status_code=404, detail="Profil client introuvable")

    client.id_type = data.id_type
    client.id_number = data.id_number
    client.kyc_status = KYCStatus.SUBMITTED
    client.kyc_data = {
        "id_front_url": data.id_front_url,
        "id_back_url": data.id_back_url,
        "selfie_url": data.selfie_url,
    }
    await client.save()
    return ClientOut(
        id=str(client.id), user_id=client.user_id, phone=client.phone,
        country_code=client.country_code, region=client.region, currency=client.currency,
        full_name=client.full_name, kyc_status=client.kyc_status.value,
        credit_score=client.credit_score, total_loans=client.total_loans,
        total_repaid=client.total_repaid, total_borrowed=client.total_borrowed,
        default_count=client.default_count,
    )


@router.get("/", response_model=List[ClientOut])
async def list_clients(user: User = Depends(get_current_user)):
    if user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.AGENT]:
        raise HTTPException(status_code=403, detail="Accès refusé")
    clients = await Client.find_all().to_list()
    return [
        ClientOut(
            id=str(c.id), user_id=c.user_id, phone=c.phone,
            country_code=c.country_code, region=c.region, currency=c.currency,
            full_name=c.full_name, kyc_status=c.kyc_status.value,
            credit_score=c.credit_score, total_loans=c.total_loans,
            total_repaid=c.total_repaid, total_borrowed=c.total_borrowed,
            default_count=c.default_count,
        ) for c in clients
    ]
