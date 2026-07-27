from motor.motor_asyncio import AsyncIOMotorClient
from beanie import Document, init_beanie
from app.core.config import settings

client: AsyncIOMotorClient = None
db = None


async def init_db():
    global client, db
    client = AsyncIOMotorClient(settings.MONGO_URL, serverSelectionTimeoutMS=120000, connectTimeoutMS=60000, socketTimeoutMS=60000)
    db = client[settings.MONGO_DB_NAME]

    from app.models.user import User
    from app.models.client import Client
    from app.models.loan import Loan, LoanProduct, Repayment
    from app.models.payment import Payment
    from app.models.audit import AuditLog
    from app.models.notification import Notification, WebhookConfig, WebhookLog

    await init_beanie(
        database=db,
        document_models=[
            User, Client, Loan, LoanProduct, Repayment, Payment,
            AuditLog, Notification, WebhookConfig, WebhookLog,
        ]
    )


def get_database():
    return db
