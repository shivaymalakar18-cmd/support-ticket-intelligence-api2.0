# tests/test_analyzer.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app  

client = TestClient(app)


def make_payload(**kwargs):
    base = {
        "ticket_id": "TEST-001",
        "customer_name": "Test User",
        "customer_email": "test@example.com",
        "channel": "email",
        "subject": "Test subject",
        "message": "This is a test message with enough words.",
    }
    base.update(kwargs)
    return base


# Mock LLM Responses 

MOCK_BILLING = """{
  "category": "billing",
  "priority": "high",
  "sentiment": "negative",
  "summary": "Customer reports duplicate charge.",
  "draft_reply": "Hi Test, we have noted your concern and will review it shortly.",
  "needs_human_review": true,
  "review_reason": "Explicit refund demand",
  "confidence_score": 0.92
}"""

MOCK_TECHNICAL = """{
  "category": "technical",
  "priority": "medium",
  "sentiment": "neutral",
  "summary": "Customer reports a bug in export feature.",
  "draft_reply": "Hi Test, thank you for reporting this. Our team will look into it.",
  "needs_human_review": false,
  "review_reason": null,
  "confidence_score": 0.88
}"""

MOCK_LOW_CONFIDENCE = """{
  "category": "other",
  "priority": "low",
  "sentiment": "neutral",
  "summary": "Customer message is too vague to analyze.",
  "draft_reply": "Hi Test, could you please provide more details about your issue?",
  "needs_human_review": true,
  "review_reason": "Ticket too vague to analyze safely.",
  "confidence_score": 0.45
}"""

MOCK_FEATURE = """{
  "category": "feature_request",
  "priority": "low",
  "sentiment": "neutral",
  "summary": "Customer is requesting dark mode feature.",
  "draft_reply": "Hi Test, thank you for the suggestion. We will pass this along to our team.",
  "needs_human_review": false,
  "review_reason": null,
  "confidence_score": 0.95
}"""

MOCK_COMPLAINT = """{
  "category": "complaint",
  "priority": "medium",
  "sentiment": "negative",
  "summary": "Customer is frustrated with support response times.",
  "draft_reply": "Hi Test, we are sorry to hear about your experience. We will look into this.",
  "needs_human_review": false,
  "review_reason": null,
  "confidence_score": 0.90
}"""

MOCK_REFUND = """{
  "category": "refund",
  "priority": "high",
  "sentiment": "negative",
  "summary": "Customer is demanding a full refund.",
  "draft_reply": "Hi Test, your refund request has been noted and will be reviewed.",
  "needs_human_review": true,
  "review_reason": "Explicit refund demand",
  "confidence_score": 0.93
}"""

MOCK_ACCOUNT = """{
  "category": "account",
  "priority": "high",
  "sentiment": "negative",
  "summary": "Customer is locked out of their account.",
  "draft_reply": "Hi Test, we have noted your concern and will look into account access.",
  "needs_human_review": false,
  "review_reason": null,
  "confidence_score": 0.91
}"""

MOCK_OTHER = """{
  "category": "other",
  "priority": "low",
  "sentiment": "neutral",
  "summary": "Customer is asking about billing policy.",
  "draft_reply": "Hi Test, could you please clarify which policy you are referring to?",
  "needs_human_review": false,
  "review_reason": null,
  "confidence_score": 0.88
}"""


#  1. Health Check 

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


#  2. Stats Endpoint 

def test_stats_endpoint():
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_tickets" in data
    assert "human_review_tickets" in data
    assert "fallback_tickets" in data


#  3. Missing Required Field 

def test_missing_message_returns_422():
    payload = make_payload()
    del payload["message"]
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 422


#  4. Invalid Channel 

def test_invalid_channel_returns_422():
    payload = make_payload(channel="fax")
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 422


#  5. Empty Body 

def test_empty_body_returns_422():
    response = client.post("/analyze-ticket", json={})
    assert response.status_code == 422


#  6. Duplicate Billing 

@patch("app.services.analyzer.call_llm", return_value=MOCK_BILLING)
def test_duplicate_billing_complaint(mock_llm):
    payload = make_payload(
        message="You charged me twice this month. $49 both times. Please fix this.",
        subject="Charged twice"
    )
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "billing"
    assert data["needs_human_review"] is True


#  7. Calm Payment Failure 

@patch("app.services.analyzer.call_llm", return_value=MOCK_TECHNICAL)
def test_calm_payment_failure(mock_llm):
    payload = make_payload(
        message="Hey my card got declined on upgrade. Not urgent just flagging it.",
        subject="Payment failed"
    )
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["needs_human_review"] is False


#  8. Account Locked 

@patch("app.services.analyzer.call_llm", return_value=MOCK_ACCOUNT)
def test_account_locked(mock_llm):
    payload = make_payload(
        message="I cannot log in. Tried password reset 3 times. No email received.",
        subject="Cannot login"
    )
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "account"


#  9. Angry Refund Request 

@patch("app.services.analyzer.call_llm", return_value=MOCK_REFUND)
def test_angry_refund_triggers_review(mock_llm):
    payload = make_payload(
        message="I want a full refund immediately. This product is useless.",
        subject="Refund demand"
    )
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["needs_human_review"] is True
    assert data["category"] == "refund"


#  10. Feature Request As Complaint 

@patch("app.services.analyzer.call_llm", return_value=MOCK_FEATURE)
def test_feature_request_as_complaint(mock_llm):
    payload = make_payload(
        message="Why is there no dark mode? Every tool has it. Very frustrating.",
        subject="No dark mode"
    )
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "feature_request"
    assert data["needs_human_review"] is False


#  11. Vague Ticket 

@patch("app.services.analyzer.call_llm", return_value=MOCK_LOW_CONFIDENCE)
def test_vague_ticket_triggers_review(mock_llm):
    payload = make_payload(
        message="not working since morning",
        subject="issue"
    )
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["needs_human_review"] is True
    assert data["confidence_score"] < 0.60


#  12. Bug Report Partial Info 

@patch("app.services.analyzer.call_llm", return_value=MOCK_TECHNICAL)
def test_bug_report_partial_info(mock_llm):
    payload = make_payload(
        message="Export crashes sometimes on large files. Chrome on Windows 11.",
        subject="Export crashing"
    )
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "technical"


#  13. Legal Threat Forces Review 

@patch("app.services.analyzer.call_llm", return_value=MOCK_BILLING)
def test_legal_threat_forces_review(mock_llm):
    payload = make_payload(
        message="I will file a chargeback with my bank if not resolved today.",
        subject="Chargeback threat"
    )
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["needs_human_review"] is True
    assert data["priority"] == "high"


#  14. Abusive Language Forces Review 

@patch("app.services.analyzer.call_llm", return_value=MOCK_BILLING)
def test_abusive_language_forces_review(mock_llm):
    payload = make_payload(
        message="You people are scammers. This is fraud.",
        subject="Fraud"
    )
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["needs_human_review"] is True


#  15. Negation — Not A Threat 

@patch("app.services.analyzer.call_llm", return_value=MOCK_BILLING)
def test_negated_chargeback_not_flagged_by_rules(mock_llm):
    payload = make_payload(
        message="I do NOT want to file a chargeback. My invoice shows $49 instead of $29.",
        subject="Invoice wrong"
    )
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    # Rule engine should not flag this — LLM decides
    data = response.json()
    assert data["category"] == "billing"

#  16. Cancellation Demand Forces Review 

@patch("app.services.analyzer.call_llm", return_value=MOCK_REFUND)
def test_cancellation_demand_forces_review(mock_llm):
    payload = make_payload(
        message="I want to cancel my subscription immediately.",
        subject="Cancel subscription"
    )
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["needs_human_review"] is True


#  17. LLM Failure — Fallback Response 

@patch("app.services.analyzer.call_llm", side_effect=Exception("LLM timeout"))
def test_llm_failure_returns_fallback(mock_llm):
    payload = make_payload()
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["needs_human_review"] is True
    assert data["confidence_score"] == 0.0
    assert data["category"] == "other"


#  18. Malformed LLM Output — Fallback 

@patch("app.services.analyzer.call_llm", return_value="this is not json {{")
def test_malformed_llm_output_returns_fallback(mock_llm):
    payload = make_payload()
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["needs_human_review"] is True
    assert data["confidence_score"] == 0.0


#  19. Response Schema Complete 

@patch("app.services.analyzer.call_llm", return_value=MOCK_TECHNICAL)
def test_response_schema_has_all_fields(mock_llm):
    payload = make_payload()
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    data = response.json()
    required_fields = [
        "category", "priority", "sentiment",
        "summary", "draft_reply",
        "needs_human_review", "confidence_score",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"