from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.core.db_migrations import migrate_sqlite_tables
import app.models  # Register all ORM models with Base.metadata
from app.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create SQLite database tables on startup
    Base.metadata.create_all(bind=engine)
    migrate_sqlite_tables()
    yield



app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
    ## Cultural Heritage Site Deterioration Monitoring Using Photogrammetry
    
    A research-grade decision support platform that combines:
    - **Optical Image Quality Assessment** (blur, exposure, resolution, feature tracking)
    - **Photogrammetric 3D Reconstruction** (SfM + MVS abstraction)
    - **Material Substrate Classification** (Sandstone, Granite, Brick, Lime Mortar)
    - **Deterioration Detection** (Cracks, Spalling, Erosion, Biological Growth)
    - **2D-to-3D Damage Mapping**
    - **Multi-Temporal Change Quantification**
    - **Scientific Reliability & Risk Prioritization**
    - **Actionable Monitoring Recommendations**
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": "0.1.0",
        "status": "operational",
        "docs_url": "/docs",
        "health_url": f"{settings.API_V1_PREFIX}/health",
    }
