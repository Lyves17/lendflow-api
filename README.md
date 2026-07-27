# LendFlow API

Global Fintech Lending Platform - Multi-region, Multi-currency, Multi-provider.

## Tech Stack
- Python 3.12 + FastAPI
- MongoDB (Beanie ODM)
- JWT Authentication

## Regions
- USA (Stripe) | Europe (Stripe) | Africa (MTN, Orange, Wave) | Asia (Razorpay, M-Pesa)

## Features
- Auth (Register/Login/JWT)
- Clients + KYC
- Loan Products (per country)
- Loan Lifecycle: Request -> Approve -> Disburse -> Repay -> Complete
- Early Repayment with discount
- Loan Extension
- Credit Score (300-850)
- Payment processing (multi-provider)
- Notifications (SMS/Email)
- Reminders (upcoming/overdue)
- Dashboard stats
- CSV export
- Audit trail
- Webhooks

## Quick Start
```bash
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Docs
http://localhost:8000/docs
