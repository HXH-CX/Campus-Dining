"""图片上传：先传后引用。

落盘路径 uploads/YYYY/MM/<uuid>.<ext>，URL 直接返回给前端，发帖时作为 images 数组的元素。
文件名一律随机，不使用用户原始文件名，避免路径穿越与重名覆盖。
"""

import asyncio
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import BadRequest
from app.utils.image_validator import max_size_bytes, validate_food_image


async def save_image(file: UploadFile) -> tuple[str, int]:
    filename = file.filename or ""
    if not filename:
        raise BadRequest("缺少文件名")

    content = await file.read()
    size = len(content)
    if size == 0:
        raise BadRequest("文件内容为空")
    if size > max_size_bytes():
        raise BadRequest(f"图片不能超过 {settings.UPLOAD_MAX_MB}MB")

    if not await validate_food_image(filename, size, content[:16]):
        raise BadRequest("仅支持 jpg/jpeg/png/webp，且文件内容需与扩展名一致")

    suffix = Path(filename).suffix.lower()
    rel_dir = f"{datetime.now():%Y/%m}"
    target = settings.upload_path / rel_dir / f"{uuid4().hex}{suffix}"
    await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(target.write_bytes, content)

    return f"/uploads/{rel_dir}/{target.name}", size
