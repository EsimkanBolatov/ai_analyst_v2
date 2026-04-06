from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    role = relationship("Role", back_populates="users")
    budgets = relationship("UserBudget", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship(
        "UserTransaction",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="UserTransaction.user_id",
    )
    submitted_reports = relationship(
        "ModerationQueue",
        back_populates="reporter",
        cascade="all, delete-orphan",
        foreign_keys="ModerationQueue.user_id",
    )
    resolved_reports = relationship(
        "ModerationQueue",
        back_populates="resolver",
        foreign_keys="ModerationQueue.resolved_by_user_id",
    )
    assistant_messages = relationship(
        "AssistantMessage",
        back_populates="user",
        cascade="all, delete-orphan",
    )
