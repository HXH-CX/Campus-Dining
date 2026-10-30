from fastapi import APIRouter, File, UploadFile

from app.api.deps import CurrentUser
from app.core.response import ApiResponse, ok
from app.schemas.catalog import UploadOut
from app.services import upload_service

router = APIRouter(prefix="/uploads", tags=["上传"])


@router.post("/images", response_model=ApiResponse[UploadOut], summary="上传单张图片（需登录）")
async def upload_image(_current: CurrentUser, file: UploadFile = File(..., description="jpg/jpeg/png/webp，≤5MB")):
    url, size = await upload_service.save_image(file)
    return ok(UploadOut(url=url, size=size))
