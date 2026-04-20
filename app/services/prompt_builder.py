

# app/services/prompt_builder.py
# Builds a fresh user prompt for every ticket request.
# Injects ticket data + rule engine alerts dynamically.

from app.schemas.ticket import TicketRequest
from app.services.deterministic_rules import RuleResult


def build_user_prompt(ticket: TicketRequest, rule_result: RuleResult) -> str:
    """
    Builds the dynamic USER turn of the LLM call.
    System prompt is always the same (system.py).
    This function injects ticket data + rule alerts per request.
    """

    # Rule alerts block — shown prominently if rules fired
    if rule_result.inject_context:
        alerts_block = (
            "RULE ENGINE ALERTS - read these before analyzing:\n"
            + "\n".join(f"  * {ctx}" for ctx in rule_result.inject_context)
            + "\n\n"
            "  needs_human_review is PRE-SET to true by the rule engine.\n"
            "  You may NOT override this to false.\n"
        )
    else:
        alerts_block = ""

    # Optional fields — only include if present
    optional_lines = []

    if ticket.product_area:
        optional_lines.append(f"Product area : {ticket.product_area}")

    if ticket.reported_at:
        optional_lines.append(
            f"Reported at  : {ticket.reported_at.isoformat()}"
        )

    if ticket.attachments_meta:
        files = ", ".join(
            f"{a.get('filename', '?')} ({a.get('type', '?')})"
            for a in ticket.attachments_meta
        )
        optional_lines.append(f"Attachments  : {files}")

    optional_block = "\n".join(optional_lines)

    # Assemble all sections — skip empty ones
    sections = [
        alerts_block,
        "TICKET",
        "--------------------------------------",
        f"Ticket ID    : {ticket.ticket_id}",
        f"Customer     : {ticket.customer_name}",
        f"Email        : {ticket.customer_email}",
        f"Channel      : {ticket.channel.value}",
        optional_block,
        "",
        f"Subject      : {ticket.subject}",
        "",
        "Message:",
        ticket.message.strip(),
        "",
        "--------------------------------------",
        "Analyze the ticket above. Return ONLY the JSON object.",
    ]

    return "\n".join(s for s in sections if s.strip())