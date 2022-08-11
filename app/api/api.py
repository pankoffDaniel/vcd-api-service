from fastapi import APIRouter

from .v1.api import api_v1_router

api_router = APIRouter()
api_router.include_router(api_v1_router, prefix='/v1')
