"""
Author persona module for CodeReviewEnv.

Simulates different PR author response styles via Mistral-7B-Instruct-v0.3
on the HuggingFace Inference API.

Two variants:
  - generate_author_response()       — synchronous (for scripts / tests)
  - generate_author_response_async() — async (for FastAPI routes — non-blocking)

Both fall back silently to canned responses when HF_TOKEN is absent or the
API call fails, ensuring the environment always runs without a token.
"""

import os
import random
from typing import Literal, Optional

PersonaType = Literal["defensive", "collaborative", "dismissive"]

_FALLBACK_RESPONSES: dict[str, list[str]] = {
    "defensive": [
        "I don't think this is an issue. The code works as intended.",
        "We handle this case upstream, so it's not a problem here.",
        "That's how it is in the legacy codebase — I copied it from there.",
        "I tested this locally and it didn't crash for me.",
    ],
    "collaborative": [
        "Good catch! I'll update it before merging.",
        "Ah, I missed that edge case. Thanks for pointing it out.",
        "You're right. Should I also check it in the other function?",
        "Makes sense, I will add a fix for this.",
    ],
    "dismissive": [
        "Not a blocker.",
        "Can we just merge this? We need to ship.",
        "LGTM to me.",
        "I'll address this in a separate PR.",
    ],
}

_SYSTEM_PROMPTS: dict[str, str] = {
    "defensive": (
        "You are a defensive software engineer reviewing a pull request. "
        "An AI agent has just commented on your code. You feel attacked and believe your code is mostly correct. "
        "Push back on most comments, explain why your code is fine, and only yield if it's an undeniable critical bug. "
        "Keep your response short (1-2 sentences)."
    ),
    "collaborative": (
        "You are a collaborative software engineer. "
        "An AI agent has just commented on your PR. You value code quality and are eager to improve. "
        "Engage thoughtfully, acknowledge good catches, and ask clarifying questions if needed. "
        "Keep your response short (1-2 sentences)."
    ),
    "dismissive": (
        "You are a rushed, dismissive software engineer. "
        "An AI agent has commented on your PR. You just want to ship the code. "
        "Ignore minor comments, accept only absolute blockers. "
        "Keep your response extremely short (1 sentence)."
    ),
}

HF_INFERENCE_URL = (
    "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
)
_TIMEOUT_SECONDS = 5.0  # Tight timeout to avoid blocking event loop


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _fallback_response(persona: str) -> str:
    """Return a random canned response for the given persona."""
    return random.choice(_FALLBACK_RESPONSES.get(persona, _FALLBACK_RESPONSES["defensive"]))


def _build_payload(persona: str, comment_message: str, is_true_positive: bool) -> dict:
    sys_prompt = _SYSTEM_PROMPTS.get(persona, _SYSTEM_PROMPTS["defensive"])
    context_hint = (
        "The AI code review agent points out a legitimate bug."
        if is_true_positive
        else "The AI code review agent points out a potential issue."
    )
    prompt = (
        f"<s>[INST] {sys_prompt}\n\n"
        f"Context: {context_hint}\n"
        f'AI Agent Comment: "{comment_message}"\n\n'
        f"Your response as the PR author: [/INST]"
    )
    return {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 60,
            "temperature": 0.7,
            "return_full_text": False,
        },
    }


def _parse_response(data) -> Optional[str]:
    if isinstance(data, list) and data:
        text = data[0].get("generated_text", "").strip().strip('"')
        return text if text else None
    return None


# ─── Async version (use in FastAPI routes) ───────────────────────────────────


async def generate_author_response_async(
    persona: PersonaType,
    comment_message: str,
    is_true_positive: bool = False,
    hf_token: Optional[str] = None,
) -> str:
    """
    Async author response — does NOT block the event loop.

    Uses httpx.AsyncClient with a 5s timeout. Falls back to canned responses
    on any error (network, timeout, parse failure, missing token).
    """
    token = hf_token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        return _fallback_response(persona)

    try:
        import httpx

        payload = _build_payload(persona, comment_message, is_true_positive)
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                HF_INFERENCE_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            text = _parse_response(resp.json())
            return text if text else _fallback_response(persona)
    except Exception as e:
        # Never raise — always return a usable string
        return _fallback_response(persona)


# ─── Sync version (preserved for scripts/tests) ───────────────────────────────


def generate_author_response(
    persona: PersonaType,
    comment_message: str,
    is_true_positive: bool = False,
    hf_token: Optional[str] = None,
) -> str:
    """
    Synchronous author response for use in scripts, tests, or non-async contexts.

    For async (FastAPI) contexts use generate_author_response_async() instead.
    """
    token = hf_token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        return _fallback_response(persona)

    try:
        import httpx

        payload = _build_payload(persona, comment_message, is_true_positive)
        with httpx.Client(timeout=_TIMEOUT_SECONDS) as client:
            resp = client.post(
                HF_INFERENCE_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            text = _parse_response(resp.json())
            return text if text else _fallback_response(persona)
    except Exception as e:
        return _fallback_response(persona)
