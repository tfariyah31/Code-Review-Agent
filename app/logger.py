import os
from datetime import datetime, timezone

# ── Cost per 1M tokens (USD) — update when pricing changes ───────────────────
PRICING = {
    # Groq (free during dev — set to 0)
    "llama-3.3-70b-versatile": {"prompt": 0.0,    "completion": 0.0},
    "llama-3.1-8b-instant":    {"prompt": 0.0,    "completion": 0.0},

    # OpenAI (swap to these in production)
    "gpt-4o":                  {"prompt": 2.50,   "completion": 10.00},
    "gpt-4o-mini":             {"prompt": 0.15,   "completion": 0.60},
}

# In-memory log — one entry per API call
_log: list[dict] = []


def log_request(
    review_id: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> dict:
    """
    Calculates cost and appends an entry to the in-memory log.
    Returns the log entry so callers can include it in responses.
    """
    rates = PRICING.get(model, {"prompt": 0.0, "completion": 0.0})

    prompt_cost     = (prompt_tokens     / 1_000_000) * rates["prompt"]
    completion_cost = (completion_tokens / 1_000_000) * rates["completion"]
    total_cost      = prompt_cost + completion_cost

    entry = {
        "review_id":         review_id,
        "model":             model,
        "timestamp":         datetime.now(timezone.utc).isoformat(),
        "prompt_tokens":     prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens":      prompt_tokens + completion_tokens,
        "estimated_cost_usd": round(total_cost, 6),
    }

    _log.append(entry)

    # Always print — visible in uvicorn logs
    provider = os.getenv("LLM_PROVIDER", "groq").upper()
    print(
        f"[USAGE] {provider} | {model} | "
        f"prompt={prompt_tokens} completion={completion_tokens} "
        f"total={prompt_tokens + completion_tokens} | "
        f"cost=${total_cost:.6f}"
    )

    return entry


def get_all_logs() -> list[dict]:
    return _log


def get_summary() -> dict:
    if not _log:
        return {
            "total_reviews":       0,
            "total_tokens_used":   0,
            "total_cost_usd":      0.0,
            "avg_tokens_per_review": 0,
        }
    total_tokens = sum(e["total_tokens"] for e in _log)
    total_cost   = sum(e["estimated_cost_usd"] for e in _log)
    return {
        "total_reviews":         len(_log),
        "total_tokens_used":     total_tokens,
        "total_cost_usd":        round(total_cost, 6),
        "avg_tokens_per_review": round(total_tokens / len(_log)),
    }