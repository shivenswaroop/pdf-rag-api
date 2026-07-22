"""LLM answer generation via OpenRouter."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger(__name__)

API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("HUNYUAN_API_KEY")
MODEL = os.getenv("LLM_MODEL", "tencent/hy3:free")

client = OpenAI(
    api_key=API_KEY,
    base_url="https://openrouter.ai/api/v1",
)

REFUSAL_MESSAGE = (
    "I cannot answer this question from the provided document content."
)


def generate_answer(question: str, context: str) -> str:
    """Generate an answer grounded strictly in the given context."""
    if not API_KEY or API_KEY.startswith("your_"):
        raise RuntimeError(
            "Missing OPENROUTER_API_KEY (or HUNYUAN_API_KEY) environment variable. "
            "Copy .env.example to .env and set a real OpenRouter key."
        )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
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
                    "content": (
                        f"Context:\n\n{context}\n\nQuestion:\n\n{question}"
                    ),
                },
            ],
        )
        content = response.choices[0].message.content
        return content.strip() if content else REFUSAL_MESSAGE
    except Exception:
        logger.exception("LLM request failed")
        raise
