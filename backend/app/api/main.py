from fastapi import APIRouter

from app.api.routes import dicom, files, inference, items, login, private, users, utils
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(dicom.router, prefix="/dicom", tags=["dicom"])
api_router.include_router(inference.router, prefix="/inference", tags=["inference"])


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
