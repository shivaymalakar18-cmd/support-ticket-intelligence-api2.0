
# app/observability/metrics.py

metrics = {
    "total_tickets": 0,
    "fallback_tickets": 0,
    "human_review_tickets": 0,
    "llm_response_tickets": 0
}


def increment(key: str):
    metrics[key] += 1


def get_metrics():
    return metrics