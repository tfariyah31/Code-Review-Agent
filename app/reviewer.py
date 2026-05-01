import json
import time
import os
from app.llm_client import client, MODEL

MAX_DIFF_CHARS = 6_000   # ~2000 tokens — guard before hitting API
MAX_RETRIES    = 3
RETRY_DELAYS   = [1, 2, 4]  # seconds — exponential backoff

# ── Tool definitions ──────────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "flag_issue",
            "description": "Flag a specific code issue found in the PR diff",
            "parameters": {
                "type": "object",
                "properties": {
                    "line": {
                        "type": "integer",
                        "description": "Line number where the issue occurs"
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Severity of the issue"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Clear explanation of why this is an issue"
                    },
                    "suggestion": {
                        "type": "string",
                        "description": "Concrete suggestion to fix the issue"
                    },
                },
                "required": ["line", "severity", "reason", "suggestion"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "score_risk",
            "description": "Give an overall risk score for the entire PR diff",
            "parameters": {
                "type": "object",
                "properties": {
                    "score": {
                        "type": "integer",
                        "description": "Risk score from 0 (no risk) to 10 (critical)"
                    },
                    "summary": {
                        "type": "string",
                        "description": "One or two sentence summary of the overall review"
                    },
                },
                "required": ["score", "summary"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are a senior software engineer performing a code review.
You will receive a PR diff and must:
1. Call flag_issue for every distinct problem you find (bugs, security issues, bad practices, missing error handling).
2. Call score_risk exactly once with an overall risk score and a summary.

Be specific. Reference line numbers. Do not invent issues that aren't in the diff."""


# ── Core review function ──────────────────────────────────────────────────────

def review_diff(diff: str) -> dict:
    if not diff or not diff.strip():
        raise ValueError("Diff cannot be empty")

    if len(diff) > MAX_DIFF_CHARS:
        raise ValueError(
            f"Diff too large ({len(diff)} chars). "
            f"Maximum is {MAX_DIFF_CHARS} chars (~2000 tokens). "
            f"Split into smaller PRs."
        )

    last_error = None

    for attempt, delay in enumerate(RETRY_DELAYS, start=1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": f"Review this PR diff:\n\n{diff}"},
                ],
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=1000,
            )

            message = response.choices[0].message
            issues  = []
            risk    = None

            if not message.tool_calls:
                return {
                    "issues": [],
                    "risk":   {"score": 0, "summary": message.content or "No structured review returned."},
                    "model":  MODEL,
                    "usage":  _parse_usage(response.usage),
                }

            for tool_call in message.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                debug = os.getenv("DEBUG", "false").lower() == "true"
                if debug:
                    print(f"[DEBUG] Tool called: {name} | args: {args}")

                if name == "flag_issue":
                    issues.append(args)
                elif name == "score_risk":
                    risk = args

            if risk is None:
                high_count   = sum(1 for i in issues if i.get("severity") == "high")
                medium_count = sum(1 for i in issues if i.get("severity") == "medium")
                risk = {
                    "score":   min(10, high_count * 3 + medium_count * 1),
                    "summary": f"Found {len(issues)} issue(s). Risk auto-calculated from severity counts.",
                }

            return {
                "issues": issues,
                "risk":   risk,
                "model":  MODEL,
                "usage":  _parse_usage(response.usage),
            }

        except Exception as e:
            last_error = e
            err_str    = str(e).lower()
            is_rate_limit = any(k in err_str for k in ["rate limit", "429", "too many requests"])

            if is_rate_limit and attempt < MAX_RETRIES:
                print(f"[RETRY] Rate limit hit. Attempt {attempt}/{MAX_RETRIES}. "
                      f"Waiting {delay}s...")
                time.sleep(delay)
                continue

            # Non-retryable error — raise immediately
            if not is_rate_limit:
                raise RuntimeError(f"LLM call failed: {str(e)}") from e

    raise RuntimeError(
        f"LLM call failed after {MAX_RETRIES} attempts. Last error: {last_error}"
    )

# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_usage(usage) -> dict:
    return {
        "prompt_tokens":     usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens":      usage.total_tokens,
    }

