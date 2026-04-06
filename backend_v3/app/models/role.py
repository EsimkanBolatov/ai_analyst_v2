from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

DEFAULT_ROLES: dict[str, str] = {
    "User": "Regular customer account.",
    "Moderator": "Reviews fraud reports from users.",
    "RiskManager": "Oversees fraud and moderation operations.",
    "Admin": "Full system access.",
}


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    users = relationship("User", back_populates="role")
