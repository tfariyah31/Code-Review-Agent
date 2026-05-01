# app/models.py
from pydantic import BaseModel, field_validator
from typing import Literal
import uuid
from datetime import datetime


# ── Request ───────────────────────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    diff: str
    context: str | None = None   # optional: PR title or description

    @field_validator("diff")
    @classmethod
    def diff_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("diff cannot be empty")
        return v


# ── Response building blocks ──────────────────────────────────────────────────

class Issue(BaseModel):
    line:       int
    severity:   Literal["low", "medium", "high"]
    reason:     str
    suggestion: str


class RiskScore(BaseModel):
    score:   int       # 0–10
    summary: str


class UsageStats(BaseModel):
    prompt_tokens:     int
    completion_tokens: int
    total_tokens:      int


# ── Full review response ──────────────────────────────────────────────────────

class ReviewResponse(BaseModel):
    id:         str
    created_at: str
    model:      str
    issues:     list[Issue]
    risk:       RiskScore
    usage:      UsageStats


# ── Usage endpoint response ───────────────────────────────────────────────────

class UsageRecord(BaseModel):
    id:           str
    created_at:   str
    total_tokens: int
    model:        str


class UsageSummary(BaseModel):
    total_reviews:      int
    total_tokens_used:  int
    reviews:            list[UsageRecord]