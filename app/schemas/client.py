from pydantic import BaseModel
from typing import Optional, Dict, Any


class ClientCreate(BaseModel):
    phone: str
    country_code: str
    region: str
    currency: str = "USD"
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    id_type: Optional[str] = None
    id_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None


class KYCSubmit(BaseModel):
    id_type: str
    id_number: str
    id_front_url: Optional[str] = None
    id_back_url: Optional[str] = None
    selfie_url: Optional[str] = None


class ClientOut(BaseModel):
    id: str
    user_id: str
    phone: str
    country_code: str
    region: str
    currency: str
    full_name: str
    kyc_status: str
    credit_score: int
    total_loans: int
    total_repaid: float
    total_borrowed: float
    default_count: int
