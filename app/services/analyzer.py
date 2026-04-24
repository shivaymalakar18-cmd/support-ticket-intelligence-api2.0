
# app/services/analyzer.py

import json
import re
import time
import uuid

from app.schemas.ticket import TicketRequest
from app.schemas.response import TicketResponse
from app.schemas.enums import PriorityEnum
from app.prompts.system import SYSTEM_PROMPT
from app.services.prompt_builder import build_user_prompt
from app.services.deterministic_rules import apply_rules
from app.services.llm import call_llm
from app.utils.logger import logger
from app.observability.metrics import increment

# this is the extra information for retry mechenism to clearify (LLMs previouse answer was un structured or currupted)
RETRY_SUFFIX = (
    "\n\nIMPORTANT: Your previous response was not valid JSON. "
    "Return ONLY the JSON object. "
    "No markdown, no code fences, no explanation. Just the JSON."
)


def _clean_llm_output(text: str) -> str:
    """
    if LLM wrapped the JSON with un neccessory data then cleaning response data -> 
    Handles ```json ... ``` and ``` ... ``` variants.
    """
    if not text:
        return ""

    text = text.strip()

    match = re.search(
        r"```(?:json)?\s*(.*?)\s*```",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        return match.group(1).strip()

    return text


def _parse(raw: str) -> TicketResponse:
    """
    clean raw LLM text, parse JSON, validates against schema
    it raises ValueError or ValidationError on failure.
    """
    cleaned = _clean_llm_output(raw)
    data = json.loads(cleaned)          # raises JSONDecodeError if invalid
    return TicketResponse(**data)       # raises ValidationError if schema wrong


def _fallback(reason: str) -> TicketResponse:
    """ Safe default response or fallback response when LLM fails completely """
    increment("fallback_tickets")
    return TicketResponse(
        category="other",
        priority="medium",
        sentiment="neutral",
        summary="Unable to analyze ticket at this time.",
        draft_reply=(
            "Thank you for reaching out. Our team will review your "
            "request and get back to you shortly."
        ),
        needs_human_review=True,
        review_reason=reason,
        confidence_score=0.0,
    )



def analyze_ticket_logic(ticket: TicketRequest) -> TicketResponse:
    """
    Full analysis pipeline:
      1. Run hard rules
      2. Build prompts
      3. Call LLM (with one retry on parse failure)
      4. Apply rule overrides on LLM output
      5. Return validated AnalysisOutput
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    fallback_used = False

    logger.info(f"[{request_id}] Ticket received: {ticket.ticket_id}")

    # apply hard Rules
    rule_result = apply_rules(ticket)

    if rule_result.inject_context:
        logger.info(
            f"[{request_id}] Rules fired: {rule_result.review_reasons}"
        )

    # Build prompt
    user_prompt = build_user_prompt(ticket, rule_result)

    # attempt 1 -> LLM Call
    result = None

    try:
        raw = call_llm(SYSTEM_PROMPT, user_prompt)
        logger.info(f"from llm --- > {raw}")
        result = _parse(raw)
        logger.info(f"[{request_id}] LLM attempt 1 succeeded")

    except Exception as e:
        logger.warning(
            f"[{request_id}] LLM attempt 1 failed: {e}. Retrying..."
        )

        # Retry with strict prompt (previouse mistake from LLM + user prompt = retry machenism)
        try:
            raw = call_llm(SYSTEM_PROMPT, user_prompt + RETRY_SUFFIX)
            result = _parse(raw)
            logger.info(f"[{request_id}] LLM attempt 2 succeeded")

        except Exception as e2:
            logger.error(
                f"[{request_id}] LLM attempt 2 failed: {e2}. "
                "Using fallback response."
            )
            fallback_used = True
            result = _fallback("LLM output parsing failed after retry")

    # Rule overrides — rules always win
    # if not fallback_used:
    #     increment("llm_response_tickets")
    #     # needs_human_review — rules can only set to true, never false
    #     if rule_result.needs_human_review:
    #         result.needs_human_review = True
    #         if not result.review_reason:
    #             result.review_reason = ", ".join(rule_result.review_reasons)

    #     # priority — rules can only upgrade, never downgrade
    #     if rule_result.forced_priority:
    #         RANK = {"low": 0, "medium": 1, "high": 2}
    #         current = result.priority.value if hasattr(result.priority, "value") else result.priority
    #         forced = rule_result.forced_priority
    #         if RANK[forced] > RANK[current]:
    #             result.priority = PriorityEnum(forced)



    if not fallback_used:
        # Smart override — rules and LLM combined decision
        increment("llm_response_tickets")
        logger.info(
            f"[{request_id}] LLM raw decision | "
            f"review={result.needs_human_review} | "
            f"confidence={result.confidence_score}"
        )
        if rule_result.needs_human_review:
            if result.needs_human_review:
                # Both rules and LLM flagged — definite escalation
                result.needs_human_review = True
                result.review_reason = ", ".join(rule_result.review_reasons)

            elif result.confidence_score >= 0.80:
                # Only rules flagged — LLM is confident and disagrees
                # Trust the LLM decision
                result.needs_human_review = False

            else:
                # Only rules flagged — LLM is uncertain
                # Stay on safe side and escalate
                result.needs_human_review = True
                result.review_reason = ", ".join(rule_result.review_reasons)

        # Priority — rules can only upgrade, never downgrade
        if rule_result.forced_priority:
            RANK = {"low": 0, "medium": 1, "high": 2}
            current = result.priority.value if hasattr(result.priority, "value") else result.priority
            forced = rule_result.forced_priority
            if RANK[forced] > RANK[current]:
                result.priority = PriorityEnum(forced)

    # Log and return 
    processing_time = round(time.time() - start_time, 3)

    logger.info(
        f"[{request_id}] Done | "
        f"time={processing_time}s | "
        f"category={result.category} | "
        f"priority={result.priority} | "
        f"fallback={fallback_used} | "
        f"review={result.needs_human_review}"
    )

    return result