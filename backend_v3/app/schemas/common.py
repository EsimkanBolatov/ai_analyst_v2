from pydantic import BaseModel


class AdminSummary(BaseModel):
    users: int
    transactions: int
    moderation_items: int
