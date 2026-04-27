
# app/modules/services/analyzer.py

import json
import re
import time
import uuid

from app.dto.ticket import TicketRequest
from app.dto.response import TicketResponse
from app.dto.enums import PriorityEnum
from app.prompts.system import SYSTEM_PROMPT
from app.modules.services.prompt_builder import build_user_prompt
from app.modules.services.deterministic_rules import apply_rules
from app.modules.services.llm import call_llm
from app.observability.metrics import increment
import logging

logger = logging.getLogger(__name__)

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



async def analyze_ticket_logic(ticket: TicketRequest) -> TicketResponse:
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
    logger.info(f"[{request_id}] Running rule engine")
    rule_result = apply_rules(ticket)

    if rule_result.inject_context:
        logger.info(
            f"[{request_id}] Rules fired: {rule_result.review_reasons}"
        )

    # Build prompt
    user_prompt = build_user_prompt(ticket, rule_result)
    logger.debug(f"[{request_id}] Prompt built")

    # attempt 1 -> LLM Call
    result = None

    try:
        logger.info(f"[{request_id}] Calling LLM (attempt 1)")

        raw = await call_llm(SYSTEM_PROMPT, user_prompt)
        # logger.info(f"from llm --- > {raw}")
        logger.debug(f"[{request_id}] LLM raw response received")

        result = _parse(raw)

        logger.debug(f"[{request_id}] LLM response parsed successfully")
        logger.info(f"[{request_id}] LLM attempt 1 succeeded")

    except Exception as e:
        logger.error(
            f"[{request_id}] Failed to parse LLM response: {e}"
        )
        logger.warning(
            f"[{request_id}] LLM attempt 1 failed: {e} | retrying..."
        )

        # Retry with strict prompt (previouse mistake from LLM + user prompt = retry machenism)
        try:
            logger.info(f"[{request_id}] Calling LLM (attempt 2)")

            raw = await call_llm(SYSTEM_PROMPT, user_prompt + RETRY_SUFFIX)
            # logger.info(f"from llm --- > {raw}")
            logger.debug(f"[{request_id}] LLM raw response received")

            result = _parse(raw)
            logger.info(f"[{request_id}] LLM attempt 2 succeeded")

        except Exception as e2:
            logger.error(
                f"[{request_id}] LLM attempt 2 failed: {e2}. Using fallback response."
            )
            logger.error(f"[{request_id}] Fallback response used")

            fallback_used = True
            result = _fallback("LLM output parsing failed after retry")

    if not fallback_used:
        increment("llm_response_tickets")

        logger.info(
            f"[{request_id}] LLM raw decision | "
            f"review={result.needs_human_review} | "
            f"confidence={result.confidence_score}"
        )

        if rule_result.needs_human_review:
            logger.info(
                f"[{request_id}] Rule vs LLM decision | "
                f"rule_review={rule_result.needs_human_review} | "
                f"llm_review={result.needs_human_review}"
            )

            if result.needs_human_review:
                # Both flagged - combine reasons
                reasons = []
                if rule_result.review_reasons:
                    reasons.extend(rule_result.review_reasons)
                if result.review_reason:
                    reasons.append(result.review_reason)
                result.needs_human_review = True
                result.review_reason = (
                    ", ".join(reasons) if reasons else None
                )

            elif result.confidence_score > 0.80:
                # Only rules flagged - LLM confident -> trust LLM
                result.needs_human_review = False

            else:
                # Only rules flagged - LLM uncertain -> safe side
                result.needs_human_review = True
                result.review_reason = (
                    ", ".join(rule_result.review_reasons)
                    if rule_result.review_reasons
                    else None
                )

        # Priority - rules upgrade only if LLM uncertain
        if rule_result.forced_priority:
            RANK = {"low": 0, "medium": 1, "high": 2}
            
            current = (
                result.priority.value
                if hasattr(result.priority, "value")
                else result.priority
            )

            forced = rule_result.forced_priority

            if (
                RANK[forced] > RANK[current]
                and result.confidence_score < 0.80
            ):
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