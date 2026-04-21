
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
[ Prompt Builder ]    ← inject the rule alerts  
        ↓
[ LLM Processing ]
        ↓
[ JSON Parser + Retry Handler ]
        ↓
[ Rule Overrides ]    ← again override rule
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
- LLM → understanding + interpretation layer
- Rule Engine → safety + business control layer
- Final output = combination of both (not one system alone)

---

## API Endpoints

### 1. Health Check

#### GET `/health`

##### Response:
```json
{
  "status": "ok"
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

## Human Review is triggers when

**Human review is required when:**  

- Refund request detected
- Legal or chargeback threat
- Cancellation request
- Abusive language
- Security/data breach mention
- Confidence score < 0.6
- Vague or unclear message
- If ANY condition is true → needs_human_review = true   

**Why Hybrid Approach?**  
- LLM = understanding layer (probabilistic)
- Rules = safety layer (deterministic)

- Note: Ensures safe + predictable system behavior. 

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

## Test Scenarios

**Run :**
```bash
pytest
```
**Covered Cases:**   
- Duplicate billing complaint
- Payment failure (calm user)
- Account login issue
- Refund angry request
- Feature request complaint
- Vague ticket
- Bug report
- Legal threat / chargeback   

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

- No database storage
- No authentication layer
- Depends on external LLM API
- Rule system is keyword-based (not ML-based)  

---

## Future Improvements

- Add database (ticket history storage)
- Replace keyword rules with NLP model
- Add async queue processing
- Add admin dashboard
- Add batch processing API

---

## How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Environment setup
cp .env.example .env
# .env mein apni GEMINI_API_KEY daalo

# 3. Run server
uvicorn main:app --reload
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