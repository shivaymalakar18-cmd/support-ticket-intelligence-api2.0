import re
from dataclasses import dataclass, field
from typing import Optional


# Trigger phrase lists 

LEGAL_THREATS = [
    "i will sue", "i am going to sue", "filing a lawsuit",
    "take you to court", "my lawyer", "consumer court",
    "consumer forum", "small claims", "regulatory complaint",
    "chargeback", "dispute this charge", "reverse the charge",
    "i will report you",
]

ABUSIVE_PATTERNS = [
    r"\bmoron\b", r"\bidiot\b", r"\bstupid\b", r"\bscam\b",
    r"\bfraud\b", r"\bthief\b", r"\bscammer\b", r"\bcriminal\b",
]

REFUND_DEMANDS = [
    "i want a refund", "give me a refund", "refund my money",
    "money back", "return my payment", "demand a refund",
    "full refund", "immediate refund", "process a refund",
    "i need a refund",
]

CANCELLATION_DEMANDS = [
    "cancel my account", "cancel my subscription",
    "delete my account", "close my account",
    "i want to cancel", "terminate my account",
]

HIGH_PRIORITY_SIGNALS = [
    "urgent", "immediately", "asap", "right now",
    "not working at all", "completely broken",
    "cannot access", "locked out", "lost access",
    "data loss", "lost my data", "data breach",
    "security incident",
]


# Result dataclass 
@dataclass
class RuleResult:
    needs_human_review: bool = False
    review_reasons: list[str] = field(default_factory=list)
    forced_priority: Optional[str] = None
    inject_context: list[str] = field(default_factory=list)


# Core rule engine 

def apply_rules(ticket) -> RuleResult:
    """
    Runs deterministic rules on ticket text.
    Returns RuleResult — analyzer uses this to:
      1. Inject context into LLM prompt
      2. Override LLM output after response
    """
    text = (
        (ticket.message or "") + " " + (ticket.subject or "")
    ).lower().strip()

    result = RuleResult()

    # Legal or chargeback threats
    for phrase in LEGAL_THREATS:
        if phrase in text:
            result.needs_human_review = True
            result.forced_priority = "high"
            result.review_reasons.append(
                f"Legal or financial threat detected: '{phrase}'"
            )
            result.inject_context.append(
                "ALERT: This ticket contains a legal or financial threat. "
                "Draft reply must be formal, empathetic, and non-committal. "
                "Do NOT admit fault or make any promises."
            )
            break

    # Abusive language
    for pattern in ABUSIVE_PATTERNS:
        if re.search(pattern, text):
            result.needs_human_review = True
            result.review_reasons.append("Abusive language detected")
            result.inject_context.append(
                "ALERT: Abusive language is present in this ticket. "
                "Reply must be calm and professional. "
                "Do not match the customer's hostile tone."
            )
            break

    # Explicit refund demand
    for phrase in REFUND_DEMANDS:
        if phrase in text:
            result.needs_human_review = True
            result.forced_priority = result.forced_priority or "high"
            result.review_reasons.append("Explicit refund demand")
            result.inject_context.append(
                "ALERT: Customer is demanding a refund. "
                "Do NOT promise or confirm any refund in draft_reply. "
                "Acknowledge the request and say it will be reviewed."
            )
            break

    # Cancellation demand
    for phrase in CANCELLATION_DEMANDS:
        if phrase in text:
            result.needs_human_review = True
            result.forced_priority = result.forced_priority or "high"
            result.review_reasons.append("Account cancellation requested")
            result.inject_context.append(
                "ALERT: Customer wants to cancel their account. "
                "Do NOT confirm cancellation in draft_reply. "
                "Acknowledge and say the team will follow up."
            )
            break

    # High priority urgency signals (no review needed, just bump priority)
    for phrase in HIGH_PRIORITY_SIGNALS:
        if phrase in text:
            result.forced_priority = result.forced_priority or "high"
            break

    # Very short or vague message
    word_count = len((ticket.message or "").split())
    if word_count < 8:
        result.needs_human_review = True
        result.review_reasons.append(
            "Message too short to analyze reliably"
        )
        result.inject_context.append(
            "NOTE: This ticket is very short and vague. "
            "Set confidence_score low (below 0.60). "
            "Ask one specific clarifying question in draft_reply."
        )

    return result