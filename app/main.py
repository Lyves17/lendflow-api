import socket
socket.setdefaulttimeout(120)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.routers import auth, clients, loans, payments, dashboard, notifications, reminders, credit

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(clients.router, prefix="/api/v1")
app.include_router(loans.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(reminders.router, prefix="/api/v1")
app.include_router(credit.router, prefix="/api/v1")


@app.on_event("startup")
async def startup():
    await init_db()

    from app.models.user import User, UserRole
    admin_exists = await User.find_one(User.role == UserRole.ADMIN)
    if not admin_exists:
        first_users = await User.find_all().to_list()
        first_user = min(first_users, key=lambda u: u.created_at) if first_users else None
        if first_user:
            first_user.role = UserRole.ADMIN
            await first_user.save()
            print(f"[BOOTSTRAP] {first_user.email} promu ADMIN automatiquement")


@app.get("/")
async def root():
    return {"app": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok"}
