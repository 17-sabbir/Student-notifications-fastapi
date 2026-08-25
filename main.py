from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.core.cors import setup_cors
from app.core.rate_limit import setup_rate_limit
from app.db.session import engine, Base
from app.routers import auth, notifications, admin, devices
from app.services.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    start_scheduler()
    yield


app = FastAPI(
    title="Student Notifications API",
    description="FastAPI backend for student notification system",
    version="1.0.0",
    lifespan=lifespan,
)

setup_cors(app)
setup_rate_limit(app)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(devices.router, prefix="/devices", tags=["devices"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
