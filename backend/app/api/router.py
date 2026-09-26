from fastapi import APIRouter
from app.api.endpoints import health, sites, surveys, images, image_quality, photogrammetry, materials, deterioration, damage_mapping, temporal, demo

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(sites.router)
api_router.include_router(surveys.router)
api_router.include_router(images.router)
api_router.include_router(image_quality.router)
api_router.include_router(photogrammetry.router)
api_router.include_router(materials.router)
api_router.include_router(deterioration.router)
api_router.include_router(damage_mapping.router)
api_router.include_router(temporal.router)
api_router.include_router(demo.router)



