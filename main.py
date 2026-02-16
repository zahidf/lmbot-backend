from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.infrastructure.persistence.database import init_db
from app.infrastructure.config.settings import get_settings
from app.presentation.api.v1 import chatbot
from app.presentation.api.v1 import documents
from app.presentation.api.v1 import triage

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):

    await init_db()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered customer service platform",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/")
async def root():
    return {"message": "Lanemark Customer Service API", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Routers
app.include_router(chatbot.router, prefix="/api/v1", tags=["chatbot"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(triage.router, prefix="/api/v1", tags=["triage"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)