import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def get_client() -> OpenAI:
    """
    Returns an OpenAI-compatible client based on LLM_PROVIDER env var.
    Switch providers by changing .env only — zero code changes needed.
    """
    provider = os.getenv("LLM_PROVIDER", "groq").lower()

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set in .env")
        return OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )

    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in .env")
        return OpenAI(api_key=api_key)

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: '{provider}'. Use 'groq' or 'openai'.")


def get_model() -> str:
    """
    Returns the model name from .env.
    Groq default:   llama-3.3-70b-versatile
    OpenAI default: gpt-4o-mini
    """
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    defaults = {
        "groq": "llama-3.3-70b-versatile",
        "openai": "gpt-4o-mini",
    }
    return os.getenv("LLM_MODEL", defaults.get(provider, "llama-3.3-70b-versatile"))


# Module-level singletons — imported by other modules
client = get_client()
MODEL  = get_model()