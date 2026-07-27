from pydantic import BaseModel
from typing import Optional


class PaymentCreate(BaseModel):
    loan_id: str
    amount: float
    provider: str


class PaymentOut(BaseModel):
    id: str
    loan_id: str
    client_id: str
    amount: float
    currency: str
    provider: str
    status: str
    provider_tx_id: Optional[str] = None
    created_at: str
