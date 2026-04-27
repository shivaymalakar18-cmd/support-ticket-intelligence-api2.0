# Design Note

## Rules vs Model Usage

This system uses a hybrid approach where responsibilities
are clearly divided between the Rule Engine and the LLM.

### Rule Engine handles:
- Explicit safety triggers -
  legal threats, refund demands, cancellation, abusive language
- Context injection into LLM prompt for risky cases
- Priority upgrade when LLM is uncertain (confidence < 0.80)
- needs_human_review can only be set to true by rules, never false

### LLM handles:
- Intent classification (action vs info distinction)
- Negation detection ("I do NOT want a refund")
- Sentiment analysis (positive, neutral, negative)
- Category classification (billing, technical, refund, etc.)
- Confidence scoring with reasoning
- Summary and draft reply generation

### Why this split?
Rule Engine enforces deterministic safety guarantees -
certain triggers must always escalate regardless of LLM output.
LLM provides natural language understanding that no keyword
list can replicate.
Neither system alone is sufficient:
- LLM only -> non-deterministic, no hard safety guarantees
- Rules only -> language blind, always incomplete

---

## Known Failure Points

### 1. Rule Engine - Negation Blind
The rule engine uses keyword matching and does not detect negation.

### 2. LLM Self-Reported Confidence
LLM generates its own confidence score - if reasoning is flawed,
it can be confidently wrong.

### 3. Single LLM Provider
Gemini downtime = degraded system - only safe fallback available.

### 4. Chargeback Context Ambiguity
Chargeback word alone does not determine category -
underlying issue may be technical, billing, or unknown.

### 5. Long Prompt Attention Dilution
System prompt is large — LLM may under-attend to middle sections.

### 6. previous_conversation Not Injected
The previous_conversation field is accepted in input
but not currently passed to the LLM prompt.

---

## Next Improvements

### Short Term
- Inject previous_conversation into LLM prompt
- Add negation detection in rule engine
- Fix attachment meta field access in prompt builder

### Medium Term
- Multiple LLM providers with circuit breaker pattern
  (Gemini -> OpenAI -> Anthropic fallback chain)
- Database persistence - MySQL for ticket history and audit trail
- Persistent metrics - reset on server restart currently
- API authentication and rate limiting

### Long Term
- ML pre-classifier for obvious cases
  (LLM called only for ambiguous tickets - cost reduced 60-70%)
- NLP layer - spaCy for negation detection and entity extraction
- Embeddings + Vector Database - similar past tickets as LLM context
- Human feedback loop - agents correct wrong decisions,
  system improves over time
- Confidence calibration from historical data
  (track actual accuracy vs LLM self-reported confidence)