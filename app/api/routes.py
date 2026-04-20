# app/api/routes.py

from fastapi import APIRouter
from app.core.config import settings
from app.schemas.ticket import TicketRequest
from app.schemas.response import TicketResponse
from app.services.analyzer import analyze_ticket_logic

router = APIRouter()

# Health func to check API is running or not
@router.get("/health")
def health():
    return {
        "status": "ok",
        "app_name": settings.app_name
    }


# that function analyze the user ticket
@router.post("/analyze-ticket", response_model=TicketResponse)
def analyze_ticket(ticket: TicketRequest):

    result = analyze_ticket_logic(ticket)

    return result