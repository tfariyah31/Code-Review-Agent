# app/main.py
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from app.logger import log_request, get_summary, get_all_logs

from app.models import (
    ReviewRequest,
    ReviewResponse,
    Issue,
    RiskScore,
    UsageStats,
    UsageSummary,
    UsageRecord,
)
from app.reviewer import review_diff

app = FastAPI(
    title="AI Code Review Agent",
    description="GPT-powered PR diff reviewer with function calling",
    version="1.0.0",
)

# ── In-memory store (replaced by a DB in production) ─────────────────────────
review_store: dict[str, ReviewResponse] = {}


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["Meta"])
def health():
    return {"status": "ok", "version": "1.0.0"}


# ── POST /api/review ──────────────────────────────────────────────────────────

@app.post("/api/review", response_model=ReviewResponse, tags=["Review"])
def create_review(request: ReviewRequest):
    try:
        result = review_diff(request.diff)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    review = ReviewResponse(
        id         = str(uuid.uuid4()),
        created_at = datetime.now(timezone.utc).isoformat(),
        model      = result["model"],
        issues     = [Issue(**i) for i in result["issues"]],
        risk       = RiskScore(**result["risk"]),
        usage      = UsageStats(**result["usage"]),
    )

    review_store[review.id] = review

    # Log cost after storing
    log_request(
        review_id         = review.id,
        model             = review.model,
        prompt_tokens     = review.usage.prompt_tokens,
        completion_tokens = review.usage.completion_tokens,
    )

    return review

# ── GET /api/review/{id} ──────────────────────────────────────────────────────

@app.get("/api/review/{review_id}", response_model=ReviewResponse, tags=["Review"])
def get_review(review_id: str):
    """
    Retrieve a past review by ID.
    """
    review = review_store.get(review_id)
    if not review:
        raise HTTPException(status_code=404, detail=f"Review '{review_id}' not found")
    return review


# ── GET /api/usage ────────────────────────────────────────────────────────────

@app.get("/api/usage", tags=["Meta"])
def get_usage():
    """
    Token usage and cost summary across all reviews this session.
    """
    summary = get_summary()
    summary["reviews"] = get_all_logs()
    return summary