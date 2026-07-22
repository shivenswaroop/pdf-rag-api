"""LLM answer generation via OpenRouter."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from openai import APIStatusError, OpenAI

load_dotenv()

logger = logging.getLogger(__name__)

API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("HUNYUAN_API_KEY")
# Primary free model. Gemma free is often upstream-limited; gpt-oss is a solid free default.
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b:free")
# Comma-separated free fallbacks tried automatically on 429/unavailable.
_FALLBACK_DEFAULT = (
    "google/gemma-4-31b-it:free,"
    "google/gemma-4-26b-a4b-it:free,"
    "nvidia/nemotron-3-nano-30b-a3b:free,"
    "nvidia/nemotron-nano-9b-v2:free"
)
FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv("LLM_FALLBACK_MODELS", _FALLBACK_DEFAULT).split(",")
    if m.strip()
]

client = OpenAI(
    api_key=API_KEY,
    base_url="https://openrouter.ai/api/v1",
)

REFUSAL_MESSAGE = (
    "I cannot answer this question from the provided document content."
)


def _model_chain() -> list[str]:
    seen: set[str] = set()
    chain: list[str] = []
    for model in [MODEL, *FALLBACK_MODELS]:
        if model and model not in seen:
            # Only allow free OpenRouter variants.
            if not model.endswith(":free"):
                logger.warning("Skipping non-free model slug: %s", model)
                continue
            seen.add(model)
            chain.append(model)
    return chain


def generate_answer(question: str, context: str) -> str:
    """Generate an answer grounded strictly in the given context."""
    if not API_KEY or API_KEY.startswith("your_"):
        raise RuntimeError(
            "Missing OPENROUTER_API_KEY (or HUNYUAN_API_KEY) environment variable. "
            "Copy .env.example to .env and set a real OpenRouter key."
        )

    messages = [
        {
            "role": "system",
            "content": (
                "You must answer ONLY from the provided context. "
                "If the answer exists in the context, answer confidently and concisely. "
                "If it does not exist, reply exactly: "
                f"{REFUSAL_MESSAGE}"
            ),
        },
        {
            "role": "user",
            "content": f"Context:\n\n{context}\n\nQuestion:\n\n{question}",
        },
    ]

    models = _model_chain()
    last_error: Exception | None = None

    for model in models:
        try:
            logger.info("Calling LLM model=%s", model)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
            )
            content = response.choices[0].message.content
            return content.strip() if content else REFUSAL_MESSAGE
        except APIStatusError as exc:
            last_error = exc
            # Retry next free model on rate limit / not found / unavailable.
            if exc.status_code in (404, 429, 503):
                logger.warning(
                    "Model %s failed with %s; trying next free fallback",
                    model,
                    exc.status_code,
                )
                continue
            logger.exception("LLM request failed for model=%s", model)
            raise
        except Exception as exc:
            last_error = exc
            logger.exception("LLM request failed for model=%s", model)
            raise

    assert last_error is not None
    logger.exception("All free LLM models failed")
    raise last_error
