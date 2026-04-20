
# app/schemas/ticket.py

from pydantic import BaseModel, EmailStr
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