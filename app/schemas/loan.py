from pydantic import BaseModel
from typing import Optional, List


class LoanProductCreate(BaseModel):
    name: str
    description: str = ""
    country_code: str
    currency: str
    min_amount: float
    max_amount: float
    min_term_days: int
    max_term_days: int
    interest_rate: float
    interest_type: str = "flat"
    processing_fee: float = 0.0
    late_fee: float = 0.0
    early_repayment_discount: float = 0.0
    max_extensions: int = 2
    extension_fee: float = 0.0


class LoanProductOut(BaseModel):
    id: str
    name: str
    description: str
    country_code: str
    currency: str
    min_amount: float
    max_amount: float
    min_term_days: int
    max_term_days: int
    interest_rate: float
    interest_type: str
    processing_fee: float
    late_fee: float


class LoanCreate(BaseModel):
    product_id: str
    amount: float
    term_days: int
    purpose: str = ""


class LoanOut(BaseModel):
    id: str
    client_id: str
    product_id: str
    amount: float
    currency: str
    term_days: int
    interest_rate: float
    interest_amount: float
    processing_fee: float
    total_amount: float
    amount_paid: float
    balance: float
    status: str
    purpose: str
    due_date: Optional[str] = None
    created_at: str


class LoanApprove(BaseModel):
    approved: bool
    notes: str = ""


class RepaymentOut(BaseModel):
    id: str
    loan_id: str
    installment_number: int
    amount_due: float
    amount_paid: float
    due_date: str
    status: str
    late_fee: float


class EarlyRepaymentCreate(BaseModel):
    loan_id: str
    amount: float
    provider: str


class EarlyRepaymentOut(BaseModel):
    id: str
    loan_id: str
    original_balance: float
    amount_paid: float
    discount_applied: float
    new_balance: float
    status: str
    created_at: str


class ExtensionCreate(BaseModel):
    loan_id: str
    additional_days: int
    reason: str = ""


class ExtensionOut(BaseModel):
    id: str
    loan_id: str
    previous_due_date: str
    new_due_date: str
    extension_days: int
    extension_fee: float
    extensions_remaining: int
    created_at: str


class CalculatorRequest(BaseModel):
    amount: float
    interest_rate: float
    term_days: int
    interest_type: str = "flat"
    processing_fee_percent: float = 0.0


class CalculatorResponse(BaseModel):
    principal: float
    interest_amount: float
    processing_fee: float
    total_amount: float
    daily_payment: float
    monthly_payment: float
    term_days: int


class CreditScoreOut(BaseModel):
    client_id: str
    current_score: int
    factors: dict
    max_loan_amount: float
    recommended_products: List[str]
    risk_level: str


class ReminderOut(BaseModel):
    id: str
    loan_id: str
    client_name: str
    phone: str
    days_overdue: int
    amount_due: float
    amount_overdue: float
    reminder_count: int
    last_reminder: str
    status: str
