from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.models.user import User, UserRole
from app.schemas.user import UserRegister, UserLogin, TokenResponse, UserOut
from app.core.security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse)
async def register(data: UserRegister):
    existing = await User.find_one(User.email == data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")

    user_count = await User.find_all().count()
    role = UserRole.ADMIN if user_count == 0 else UserRole.CLIENT

    user = User(
        email=data.email,
        phone=data.phone,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=role,
    )
    await user.insert()

    token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    return TokenResponse(access_token=token, user_id=str(user.id), role=user.role.value)


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin):
    user = await User.find_one(User.email == data.email)
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")

    token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    return TokenResponse(access_token=token, user_id=str(user.id), role=user.role.value)


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return UserOut(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role.value,
        is_active=user.is_active,
        is_verified=user.is_verified,
    )


class PromoteRequest(BaseModel):
    user_id: str
    role: str


@router.post("/promote", response_model=UserOut)
async def promote_user(data: PromoteRequest, user: User = Depends(get_current_user)):
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Seul un admin peut promouvoir")

    target = await User.get(data.user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    try:
        new_role = UserRole(data.role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Rôle invalide")

    target.role = new_role
    await target.save()

    return UserOut(
        id=str(target.id), email=target.email, full_name=target.full_name,
        phone=target.phone, role=target.role.value,
        is_active=target.is_active, is_verified=target.is_verified,
    )
