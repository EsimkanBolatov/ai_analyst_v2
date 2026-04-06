from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BlacklistEntry(Base):
    __tablename__ = "blacklist_entries"
    __table_args__ = (UniqueConstraint("data_type", "value", name="uq_blacklist_type_value"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    data_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_report_id: Mapped[int | None] = mapped_column(
        ForeignKey("moderation_queue.id"),
        nullable=True,
        index=True,
    )
    approved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    source_report = relationship("ModerationQueue", back_populates="blacklist_entry")
    approved_by = relationship("User", foreign_keys=[approved_by_user_id], back_populates="approved_blacklist_entries")
