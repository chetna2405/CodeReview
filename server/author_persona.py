"""
Author persona module for CodeReviewEnv.

Allows simulating different types of PR authors (defensive, collaborative, dismissive)
that respond to agent comments via an LLM (Mistral-7B-Instruct-v0.3 on HF Inference API).

Falls back silently to hardcoded responses on any error or missing token.
"""

import os
import random
from typing import Literal, Optional

PersonaType = Literal["defensive", "collaborative", "dismissive"]

_FALLBACK_RESPONSES = {
    "defensive": [
        "I don't think this is an issue. The code works as intended.",
        "We handle this case upstream, so it's not a problem here.",
        "That's how it is in the legacy codebase, I copied it from there.",
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
    ]
}

_SYSTEM_PROMPTS = {
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
        "An AI agent has commented on your PR. You just want to ship the code and don't care about 'nits' or 'style' or 'minor bugs'. "
        "Ignore minor comments, accept only absolute blockers. "
        "Keep your response extremely short (1 sentence)."
    )
}

HF_INFERENCE_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"


def _fallback_response(persona: str) -> str:
    """Return a random canned response for the given persona."""
    return random.choice(_FALLBACK_RESPONSES.get(persona, _FALLBACK_RESPONSES["defensive"]))


def generate_author_response(
    persona: PersonaType,
    comment_message: str,
    is_true_positive: bool = False,
    hf_token: Optional[str] = None
) -> str:
    """
    Generate an author response to an agent's comment.
    
    Uses HuggingFace Inference API (Mistral-7B-Instruct-v0.3) via httpx if a token
    is provided, otherwise falls back to canned responses.

    Args:
        persona: Author personality type.
        comment_message: The agent's comment text.
        is_true_positive: Whether the agent's comment is actually correct.
        hf_token: HuggingFace API token (also checked from env vars).

    Returns:
        Author's response string.
    """
    # Resolve token
    token = hf_token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        return _fallback_response(persona)

    try:
        import httpx

        sys_prompt = _SYSTEM_PROMPTS.get(persona, _SYSTEM_PROMPTS["defensive"])
        context_hint = (
            "The AI code review agent points out a legitimate bug."
            if is_true_positive
            else "The AI code review agent points out a potential issue that may or may not be valid."
        )

        prompt = (
            f"<s>[INST] {sys_prompt}\n\n"
            f"Context: {context_hint}\n"
            f"AI Agent Comment: \"{comment_message}\"\n\n"
            f"Your response as the PR author: [/INST]"
        )

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 60,
                "temperature": 0.7,
                "return_full_text": False,
            },
        }

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                HF_INFERENCE_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        # Parse response — HF returns list of {generated_text: ...}
        if isinstance(data, list) and data:
            text = data[0].get("generated_text", "").strip().strip('"')
            if text:
                return text

        return _fallback_response(persona)

    except Exception as e:
        print(f"Warning: LLM author persona generation failed: {e}")
        return _fallback_response(persona)
