from fastapi import APIRouter

from .routers import vcd

api_v1_router = APIRouter()
api_v1_router.include_router(vcd.router)
