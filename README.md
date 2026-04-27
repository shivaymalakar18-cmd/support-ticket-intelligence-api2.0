
# Support Ticket Intelligence API

A production-minded FastAPI service that analyzes **customer support tickets**
using a hybrid of deterministic rules and LLM-based intent analysis.

The system automatically classifies tickets, detects sentiment, assigns
priority, generates a safe draft reply, and determines whether human
review is required — with guaranteed safe fallback behavior when the
LLM is unavailable.

---

## Project Overview

**This system processes customer support tickets and automatically:**

- Classifies the ticket (billing, technical, refund, account, feature_request, complaint, other)
- Detects sentiment (positive, neutral, negative)
- Assigns priority (low, medium, high)
- Generates a concise summary (1–3 lines)
- Generates a safe draft reply (customer-facing)
- Determines whether human review is required

The system ensures **safe automation with human oversight for risky cases**.

---

## Project Structure

```
support-ticket-api/
├── app/
│   ├── main.py
│   ├── api/
│   │   └── routes.py
│   ├── core/
│   │   └── config.py
│   ├── schemas/
│   │   ├── ticket.py
│   │   ├── response.py
│   │   └── enums.py
│   ├── services/
│   │   ├── analyzer.py
│   │   ├── deterministic_rules.py
│   │   ├── llm.py
│   │   └── prompt_builder.py
│   ├── prompts/
│   │   └── system.py
│   ├── observability/
│   │   └── metrics.py
│   └── utils/
│       └── logger.py
├── tests/
│   ├── test_analyzer.py
│   └── test_rules.py
├── .env.example
├── requirements.txt
├── DESIGN.md
└── README.md
```

---

## Tech Stack

- FastAPI
- Pydantic (V2)
- Python 3.10+
- Google GenAI / Gemini LLM
- UUID (request tracking)
- Logging module
- pytest (testing)

---

## System Architecture

```md
[ Client Request ]
        ↓
[ FastAPI Endpoint ]
        ↓
[ Rule Engine ]      
        ↓
[ Prompt Builder ]    <- inject the rule alerts  
        ↓
[ LLM Processing ]
        ↓
[ JSON Parser + Retry Handler ]
        ↓
[ Rule Overrides ]    <- again override rule
        ↓
[ Final Response ]
```
---

## System Design & Decision Flow

- This system follows a hybrid intelligence approach, where responsibilities are clearly separated between LLM and Rule Engine.

### Decision Responsibility Matrix (LLM vs Rule Engine)  

| Field              | Depends On            | Controlled By          |
| ------------------ | --------------------- | ---------------------- |
| confidence_score   | LLM reasoning quality | LLM                    |
| category           | Text classification   | LLM                    |
| sentiment          | Emotion detection     | LLM                    |
| summary            | Text understanding    | LLM                    |
| draft_reply        | Safe response gen     | LLM                    |
| priority           | Business rules        | LLM + Rule Engine      |
| needs_human_review | Safety & risk rules   | LLM + Rule Engine      |
| review_reason      | Safety conditions     | LLM + Rule Engine      |

- Note: Rule Engine can only upgrade priority, never downgrade.
Rule Engine can only set needs_human_review to true, never false.

### Key Idea
- LLM -> understanding + interpretation layer
- Rule Engine -> safety + business control layer
- Final output = combination of both (not one system alone)

---

## API Endpoints

### 1. Health Check

#### GET `/health`

##### Response:
```json
{
  "status": "ok",
  "app_name": "Support Ticket Intelligence API"
}
```

---

### 2. Analyze Ticket: 

#### POST `/analyze-ticket`

##### Request Body
```json

{
  "ticket_id": "T101",
  "customer_name": "Rahul",
  "customer_email": "rahul@gmail.com",
  "channel": "email",
  "subject": "Payment issue",
  "message": "I was charged twice for my order"
}
```

##### Response Body
```json
{
  "category": "billing",
  "priority": "high",
  "sentiment": "negative",
  "summary": "Customer reports a duplicate payment issue.",
  "draft_reply": "Thank you for reaching out. Our team will investigate this issue.",
  "needs_human_review": true,
  "review_reason": "Refund request detected",
  "confidence_score": 0.85
}
```

---

### 3. Stats

#### GET `/stats`

##### Response:
```json
{
  "total_tickets": 10,
  "fallback_tickets": 1,
  "human_review_tickets": 4,
  "llm_response_tickets": 6
}
```

--- 

## Ticket Input Model Fields

| Field                 | Type         | Required | Description        |
| --------------------- | ------------ | -------- | ------------------ |
| ticket_id             | string       | Yes      | Unique ticket ID   |
| customer_name         | string       | Yes      | Customer name      |
| customer_email        | string       | Yes      | Email address      |
| channel               | enum         | Yes      | email / chat / web |
| subject               | string       | Yes      | Ticket subject     |
| message               | string       | Yes      | Main issue         |
| product_area          | string       | No       | Affected module    |
| reported_at           | datetime     | No       | Timestamp          |
| previous_conversation | list[string] | No       | Chat history       |
| attachments_meta      | list[object] | No       | File metadata      |

---

## Human Review Triggers

**Human review is required when:**  

- Refund request detected
- Legal or chargeback threat
- Cancellation request
- Abusive language
- Security/data breach mention
- Confidence score < 0.6
- Vague or unclear message
- If ANY condition is true -> needs_human_review = true   

**Why Hybrid Approach?**  
- LLMs provide strong natural language understanding but are non-deterministic
- Rule Engine enforces deterministic business logic and consistency
- Override layer ensures safety by correcting or upgrading risky outputs
- Hybrid approach balances:
        1. accuracy (LLM understanding)
        2. reliability (rule-based control)
        3. safety (override guarantees)

---

## Error Handling Strategy

### System is designed to never crash:

#### 1. LLM Failure (503 / timeout)

- fallback response returned

#### 2. JSON Parsing Failure

- retry once

#### 3. Retry Failure

- safe fallback response

#### 4. Guaranteed Behavior

- API always returns valid JSON response

---

## Testing

This project includes two types of tests:

### Unit Tests — `tests/test_rules.py`
Tests the deterministic rule engine in isolation.
No LLM call is made — pure Python logic only.

Covers:
- Legal threat detection
- Refund demand detection
- Abusive language detection
- Cancellation demand detection
- Negation cases (e.g. "I do NOT want a refund")
- Clean ticket — no false triggers
- Context injection verification

### Integration Tests — `tests/test_analyzer.py`
Tests the full API pipeline end to end.
LLM is mocked — no real API key required.

Covers:
- Duplicate billing complaint
- Calm payment failure
- Account locked / password reset
- Angry refund request
- Feature request as complaint
- Vague ticket — low confidence triggers review
- Bug report with partial info
- Legal threat / chargeback forces review
- Abusive language forces review
- Negated chargeback — should not flag
- Cancellation demand forces review
- LLM failure — fallback response returned
- Malformed LLM output — fallback response returned
- Response schema completeness check

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test Type
```bash
# Unit tests only
pytest tests/test_rules.py -v

# Integration tests only
pytest tests/test_analyzer.py -v

# Run specific test
pytest tests/ -v -k "test_legal_threat"
```

### Run Without Real API Key
```bash
GEMINI_API_KEY=test pytest tests/ -v
```

### Test Results
```
37 passed in ~8s
18 unit tests
19 integration tests
```

---

## Observability

**System logs include:**  
- request_id (unique tracking)
- processing time
- fallback usage
- human review decision  

### Example Logs
```log
[b7ef2be1] Ticket received: TKT-002
[b7ef2be1] LLM attempt 1 succeeded
[b7ef2be1] Done | time=7.601s | category=billing | priority=high | fallback=False | review=True
```
---

## Limitations

- Rule engine is keyword-based and does not handle negation
  (e.g., "I do NOT want a refund" may be incorrectly flagged)
- LLM confidence score is self-reported and not externally verified
- previous_conversation field is not currently injected into the prompt
- Single LLM provider — if Gemini is unavailable, system relies on fallback
- In-memory metrics reset on server restart
- No authentication layer
- No database persistence

---

## Design Note

See [DESIGN.md](DESIGN.md) for engineering decisions,
failure points, and next improvements.

---

## Future Improvements

### Accuracy & Control
- Currently the system relies on LLM for all semantic understanding
  (intent, sentiment, classification). The LLM is a black box —
  we have no control over its internal reasoning.

- To gain full control over the classification pipeline,
  the following layers will be added externally:

  - **ML Classifier** — scikit-learn or FastText for obvious cases
    (billing, account, technical) — fast, deterministic, no LLM cost
  - **NLP Layer** — spaCy or NLTK for negation detection,
    entity extraction, and language detection
  - **Embeddings** — sentence-transformers to convert tickets
    into vector representations
  - **Vector Database** — Pinecone or ChromaDB to store past tickets
    and retrieve similar resolved cases as context for LLM
  - **Caching** — cache embeddings and similar ticket results
    to reduce redundant LLM calls

- LLM will then handle only genuinely ambiguous cases —
  reducing cost by 60-70% and improving overall accuracy

### Reliability
- Multiple LLM providers with circuit breaker pattern
  (Gemini → OpenAI → Anthropic fallback chain)
- Async task queue — Celery + Redis for background processing

### Data & Observability
- Database persistence for ticket history and audit trail
- Human feedback loop — agents correct wrong decisions,
  model improves over time
- Persistent metrics with business analytics dashboard

### Security
- API authentication and rate limiting
- Per-client request quotas

---

## How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Environment setup
cp .env.example .env
# Add your GEMINI_API_KEY to .env file

# 3. Run server
uvicorn app.main:app --reload
# Server: http://localhost:8000
# Docs:   http://localhost:8000/docs

# 4. Run tests (real API key nahi chahiye)
GEMINI_API_KEY=test pytest tests/ -v
```
---

## Key Design Decisions  

- LLM is NOT fully trusted
- Rules enforce business safety
- Fallback ensures system never crashes
- Every response validated using Pydantic
- Hybrid AI + deterministic architecture  

---

## Final Summary

**This project demonstrates:**

- Real-world backend system design
- FastAPI production API development
- LLM integration with safety guardrails
- Rule-based + AI hybrid decision system
- Robust error handling strategy
- Production-level engineering thinking