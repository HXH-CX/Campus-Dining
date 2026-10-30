"""应用配置。所有可变项走环境变量 / .env，代码里不写死连接串。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_NAME: str = "校园食光 API"
    APP_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    DATABASE_URL: str = "mysql+asyncmy://root:root@127.0.0.1:3306/campus_foodie"
    DB_ECHO: bool = False

    JWT_SECRET: str = "dev-only-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7

    UPLOAD_DIR: str = "./uploads"
    UPLOAD_MAX_MB: int = 5
    UPLOAD_ALLOWED_EXT: str = "jpg,jpeg,png,webp"

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # 热榜进程内缓存时长（秒），同时是 APScheduler 预热周期
    HOT_CACHE_TTL_SECONDS: int = 3600

    @property
    def upload_path(self) -> Path:
        path = Path(self.UPLOAD_DIR)
        return path if path.is_absolute() else BASE_DIR / path

    @property
    def allowed_ext(self) -> set[str]:
        return {f".{e.strip().lower().lstrip('.')}" for e in self.UPLOAD_ALLOWED_EXT.split(",") if e.strip()}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
