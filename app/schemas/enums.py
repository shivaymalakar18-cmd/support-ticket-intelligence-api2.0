

# app/schemas/enums.py
# Enum values

from enum import Enum
class ChannelEnum(str, Enum):
    email = "email"
    chat = "chat"
    web = "web"

class CategoryEnum(str, Enum):
    billing = "billing"
    technical = "technical"
    refund = "refund"
    account = "account"
    feature_request = "feature_request"
    complaint = "complaint"
    other = "other"

class PriorityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class SentimentEnum(str, Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"