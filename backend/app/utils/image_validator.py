"""图片校验（MVP 为 Mock）。

PRD/Tech Design 已定稿：MVP 不接真实 AI 视觉模型，只校验扩展名、大小、
以及文件头魔数，防止改后缀伪装。未来替换 validate_food_image 的实现即可，
上传接口与业务代码都不需要改。
"""

from pathlib import Path

from app.core.config import settings

# 常见图片格式的文件头；只做"是不是图片"，不判断内容是否为美食
_MAGIC_NUMBERS: dict[str, tuple[bytes, ...]] = {
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".webp": (b"RIFF",),
}


def max_size_bytes() -> int:
    return settings.UPLOAD_MAX_MB * 1024 * 1024


def check_extension(filename: str) -> bool:
    return Path(filename).suffix.lower() in settings.allowed_ext


def check_magic(head: bytes, suffix: str) -> bool:
    candidates = _MAGIC_NUMBERS.get(suffix.lower())
    if candidates is None:
        return False
    if suffix.lower() == ".webp":
        # WEBP 头是 "RIFF....WEBP"，只判 RIFF 会放过 wav，这里再确认偏移 8 起是 WEBP
        return head.startswith(b"RIFF") and head[8:12] == b"WEBP"
    return any(head.startswith(magic) for magic in candidates)


async def validate_food_image(filename: str, size: int, head: bytes) -> bool:
    """校验是否为可接受的图片文件。

    :param filename: 原始文件名（只取扩展名，不落盘用原名）
    :param size: 文件字节数
    :param head: 文件前 16 字节左右内容
    """
    if not check_extension(filename):
        return False
    if size <= 0 or size > max_size_bytes():
        return False
    if not check_magic(head, Path(filename).suffix):
        return False
    # TODO: 接入 AI 视觉模型判断是否为美食
    return True
