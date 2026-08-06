from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.ulid import generate_ulid
from app.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username_normalized", name="uq_users_username_normalized"),
        Index("ix_users_active_role", "is_active", "role"),
        CheckConstraint("role IN ('admin', 'user')", name="ck_users_role"),
        CheckConstraint("token_version > 0", name="ck_users_token_version_positive"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=generate_ulid)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    username_normalized: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    token_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    password_changed_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False)


class UserSettings(TimestampMixin, Base):
    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Asia/Shanghai", server_default="Asia/Shanghai"
    )
