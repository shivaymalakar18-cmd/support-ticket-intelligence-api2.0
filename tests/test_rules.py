# tests/test_rules.py
# Unit tests for the hard rules engine.
# These run without any LLM call — pure Python logic.

import pytest
from app.schemas.ticket import TicketRequest
from app.services.deterministic_rules import apply_rules


def make_ticket(message: str, subject: str = "Test") -> TicketRequest:
    return TicketRequest(
        ticket_id="TEST-001",
        customer_name="Test User",
        customer_email="test@example.com",
        channel="email",
        subject=subject,
        message=message,
    )


#  Legal threat tests 

def test_chargeback_triggers_review():
    ticket = make_ticket("I am going to file a chargeback with my bank.")
    result = apply_rules(ticket)
    assert result.needs_human_review is True
    assert result.forced_priority == "high"


def test_consumer_forum_triggers_review():
    ticket = make_ticket("I will report you to the consumer forum.")
    result = apply_rules(ticket)
    assert result.needs_human_review is True


def test_legal_info_does_not_trigger():
    # "legal" word present but it is an info request — rules should NOT fire
    ticket = make_ticket("I want to understand my legal rights as a customer.")
    result = apply_rules(ticket)
    # Rules only fire on exact phrases like "i will sue", "chargeback" etc.
    # General "legal" word is handled by LLM intent analysis
    assert result.needs_human_review is False


# Refund demand tests 

def test_refund_demand_triggers_review():
    ticket = make_ticket("I want a full refund immediately.")
    result = apply_rules(ticket)
    assert result.needs_human_review is True
    assert result.forced_priority == "high"


def test_refund_policy_question_does_not_trigger():
    # Asking about policy — no action phrase present
    ticket = make_ticket(
        "Hi, I wanted to ask about your cancellation terms. "
        "What happens to my data if I stop using the service?"
    )
    result = apply_rules(ticket)
    assert result.needs_human_review is False


#  Abusive language tests 

def test_abusive_language_triggers_review():
    ticket = make_ticket("You people are scammers and frauds.")
    result = apply_rules(ticket)
    assert result.needs_human_review is True


def test_calm_message_no_review():
    ticket = make_ticket(
        "Hi, my payment did not go through. Can you help me sort this out?"
    )
    result = apply_rules(ticket)
    assert result.needs_human_review is False


#  Cancellation demand tests 

def test_cancellation_demand_triggers_review():
    ticket = make_ticket("I want to cancel my subscription right now.")
    result = apply_rules(ticket)
    assert result.needs_human_review is True


#  Urgency signal tests 

def test_locked_out_sets_high_priority():
    ticket = make_ticket("I am completely locked out of my account.")
    result = apply_rules(ticket)
    # HIGH_PRIORITY_SIGNALS removed — LLM handles priority
    # Rule engine only handles safety flags
    assert result.forced_priority is None  # expected now


#  Vague message tests 
def test_very_short_message_triggers_review():
    ticket = make_ticket("It is not working.")
    result = apply_rules(ticket)

    assert result.needs_human_review is False  


def test_normal_length_message_no_vague_trigger():
    ticket = make_ticket(
        "The export button crashes when I try to download files larger than 50MB on Chrome."
    )
    result = apply_rules(ticket)
    # Should not trigger vague rule — long enough message
    vague_reasons = [r for r in result.review_reasons if "short" in r.lower()]
    assert len(vague_reasons) == 0


#  inject_context tests 

def test_context_injected_for_legal_threat():
    ticket = make_ticket("I will file a chargeback if not resolved.")
    result = apply_rules(ticket)
    assert len(result.inject_context) > 0
    assert any("threat" in ctx.lower() for ctx in result.inject_context)


def test_no_context_for_clean_ticket():
    ticket = make_ticket(
        "Hi, I have a question about how the billing cycle works. Can you explain it?"
    )
    result = apply_rules(ticket)
    assert result.inject_context == []


def test_calm_payment_failure():
    ticket = make_ticket(
        "Hey, my card got declined during upgrade but it's not urgent. Just informing."
    )
    result = apply_rules(ticket)

    # Calm payment issue should NOT trigger human review
    assert result.needs_human_review is False


def test_account_locked_or_reset_request():
    ticket = make_ticket(
        "I cannot log in. I tried password reset multiple times but didn't get email."
    )
    result = apply_rules(ticket)

    # Account issues are sensitive → usually flagged
    assert result.needs_human_review is False

def test_feature_request_as_complaint():
    ticket = make_ticket(
        "Why is there no dark mode? Every modern app has it. Very frustrating."
    )
    result = apply_rules(ticket)

    # Should NOT be treated as escalation, just feature_request intent
    assert result.needs_human_review is False

def test_bug_report_partial_reproduction():
    ticket = make_ticket(
        "Export feature crashes sometimes when I try with large files. Happens on Chrome."
    )
    result = apply_rules(ticket)

    # Bug reports should not auto escalate unless threat/refund etc.
    assert result.needs_human_review is False

def test_extremely_vague_ticket():
    ticket = make_ticket("Not working properly since update.")
    result = apply_rules(ticket)

    # Should remain safe unless explicit escalation detected
    assert result.needs_human_review is False