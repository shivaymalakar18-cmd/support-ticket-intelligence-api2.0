import re
from dataclasses import dataclass, field
from typing import Optional
from app.utils.logger import logger

# Trigger phrase lists 

LEGAL_THREATS = [
    "i will sue", "i am going to sue",
    "filing a lawsuit", "take you to court",
    "my lawyer will", "contacted my lawyer",
    "consumer court", "consumer forum",
    "small claims", "regulatory complaint",
    "i will file a chargeback",      # complete phrase
    "going to file a chargeback",    # complete phrase
    "filing a chargeback",           # complete phrase
    "will chargeback",               # complete phrase
    "dispute this charge",
    "reverse the charge",
    "i will report you",
]
ABUSIVE_PATTERNS = [
    r"\bmoron\b",
    r"\bidiot\b",
    r"\bstupid\b",
    r"\bscam\w*\b",      # scam, scammer, scammers
    r"\bfraud\w*\b",     # fraud, frauds, fraudulent
    r"\bthief\b",
    r"\bthieves\b",      # plural
    r"\bscammer\w*\b",   # scammer, scammers
    r"\bcriminal\w*\b",  # criminal, criminals
]

REFUND_DEMANDS = [
    "i want a refund", "give me a refund",
    "refund my money", "return my payment",
    "demand a refund", "full refund",
    "immediate refund", "process a refund",
    "i need a refund",
    "i want my money back",  
    "give me my money back", 
]

CANCELLATION_DEMANDS = [
    "cancel my account", "cancel my subscription",
    "delete my account", "close my account",
    "i want to cancel", "terminate my account",
]



# Result dataclass 
@dataclass
class RuleResult:
    needs_human_review: bool = False
    review_reasons: list[str] = field(default_factory=list)
    forced_priority: Optional[str] = None
    inject_context: list[str] = field(default_factory=list)


def apply_rules(ticket) -> RuleResult:
    text = (
        (ticket.message or "") + " " + (ticket.subject or "")
    ).lower().strip()

    result = RuleResult()

    # Legal or chargeback threats
    for phrase in LEGAL_THREATS:
        if phrase in text:
            logger.info(f"[RULE] Legal threat matched: '{phrase}'")
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
            logger.info(f"[RULE] Abusive pattern matched: '{pattern}'")
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
            logger.info(f"[RULE] Refund demand matched: '{phrase}'")
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
            logger.info(f"[RULE] Cancellation demand matched: '{phrase}'")
            result.needs_human_review = True
            result.forced_priority = result.forced_priority or "high"
            result.review_reasons.append("Account cancellation requested")
            result.inject_context.append(
                "ALERT: Customer wants to cancel their account. "
                "Do NOT confirm cancellation in draft_reply. "
                "Acknowledge and say the team will follow up."
            )
            break

    logger.info(f"from Rule engine --> {result}")

    return result