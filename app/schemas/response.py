
# app/schemas/response.py

from pydantic import BaseModel, Field
from typing import Optional
from app.schemas.enums import CategoryEnum, PriorityEnum, SentimentEnum

# pydantic schema (Response validation)
class TicketResponse(BaseModel):
    category: CategoryEnum
    priority: PriorityEnum
    sentiment: SentimentEnum
    summary: str
    draft_reply: str
    needs_human_review: bool
    review_reason: Optional[str] = None
    confidence_score: float = Field(ge=0.0, le=1.0)