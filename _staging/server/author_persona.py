"""
Author persona module for CodeReviewEnv.

Allows simulating different types of PR authors (defensive, collaborative, dismissive)
that respond to agent comments via an LLM.
"""

import os
import random
from typing import Literal

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

def generate_author_response(
    persona: PersonaType,
    comment_message: str,
    is_true_positive: bool = False,
    hf_token: str = None
) -> str:
    """
    Generate an author response to an agent's comment.
    
    Uses HuggingFace Inference API if a token is provided, otherwise falls back
    to canned responses.
    """
    if not hf_token:
        # Fallback
        return random.choice(_FALLBACK_RESPONSES.get(persona, _FALLBACK_RESPONSES["defensive"]))

    try:
        from huggingface_hub import InferenceClient
        client = InferenceClient(
            model="meta-llama/Llama-3.1-8B-Instruct",
            token=hf_token,
        )

        sys_prompt = _SYSTEM_PROMPTS.get(persona, _SYSTEM_PROMPTS["defensive"])
        context_hint = "The AI code review agent points out a legitimate bug." if is_true_positive else "The AI code review agent points out an issue."
        
        prompt = f"{sys_prompt}\n\nContext: {context_hint}\nAI Agent Comment: \"{comment_message}\"\n\nYour response as the author:"

        response = client.text_generation(
            prompt,
            max_new_tokens=60,
            temperature=0.7,
        )
        return response.strip().strip('"')
    except Exception as e:
        print(f"Warning: LLM author persona generation failed: {e}")
        return random.choice(_FALLBACK_RESPONSES.get(persona, _FALLBACK_RESPONSES["defensive"]))
