# app/modules/routes.py

from fastapi import APIRouter
from app.core.config import settings
from app.dto.ticket import TicketRequest
from app.dto.response import TicketResponse
from app.modules.services.analyzer import analyze_ticket_logic
from app.observability.metrics import increment, get_metrics
import logging
logger = logging.getLogger(__name__)
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
async def analyze_ticket(ticket: TicketRequest):

    try:
        logger.info(f"[API] /analyze-ticket called")

        result = await analyze_ticket_logic(ticket)
        increment("total_tickets")

        if result.needs_human_review:
            increment("human_review_tickets")

        logger.info(
            f"[API] Ticket processed | id={ticket.ticket_id}"
        )

        return result

    except Exception as e:
        logger.error(f"[API] Failed to process ticket: {e}")
        raise
 
@router.get("/stats")
def stats():
    return get_metrics()
        