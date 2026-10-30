from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。Alembic 的 target_metadata 取 Base.metadata。"""
