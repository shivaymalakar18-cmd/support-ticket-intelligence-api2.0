
# app/schemas/ticket.py

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from app.schemas.enums import ChannelEnum

# this function is used to attech screenshots or imgs of problem like
class AttachmentMeta(BaseModel):
    filename: str
    filetype: str


# Request Validation
class TicketRequest(BaseModel):
    ticket_id: str
    customer_name: str
    customer_email: EmailStr
    channel: ChannelEnum
    subject: str
    message: str

    # optional fields
    product_area: Optional[str] = None
    reported_at: Optional[datetime] = None
    previous_conversation: Optional[List[str]] = None
    attachments_meta: Optional[List[AttachmentMeta]] = None

    @field_validator('message')
    @classmethod
    def message_length(cls, v):
        if len(v) > 2000:
            raise ValueError('Message too long — max 2000 characters')
        return v