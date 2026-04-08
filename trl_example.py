#!/usr/bin/env python3
"""
trl_example.py — Minimal PPO training loop using CodeReviewEnv + TRL.

Demonstrates how to connect CodeReviewEnv to an RL training loop via the
OpenEnvClient and trl.PPOTrainer. This is a reference implementation —
not production-ready, but shows the full reward signal → training pipeline.

Requirements:
    pip install trl transformers torch openenv-core

Usage:
    python trl_example.py
    python trl_example.py --env-url https://your-space.hf.space
    python trl_example.py --model-name Qwen/Qwen2.5-0.5B-Instruct --steps 50

Colab notebook:
    https://colab.research.google.com/github/your-org/CodeReviewEnv/blob/main/colab_ppo_example.ipynb
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import re
from dataclasses import dataclass, field
from typing import Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


# ─── Config ───────────────────────────────────────────────────────────────────

@dataclass
class TrainingConfig:
    """Configuration for the PPO training run."""
    model_name: str = "Qwen/Qwen2.5-0.5B-Instruct"
    env_url: str = "http://localhost:8000"
    task_id: str = "simple_review"
    max_steps_per_episode: int = 8
    num_episodes: int = 20
    ppo_epochs: int = 2
    learning_rate: float = 1e-5
    batch_size: int = 4
    seed: int = 42
    output_dir: str = "./rl_checkpoints"
    log_every: int = 5


# ─── Env client ───────────────────────────────────────────────────────────────

class CodeReviewEnvClient:
    """
    Lightweight REST client for CodeReviewEnv.

    Wraps /api/reset, /api/step, and /grader into a simple gym-like interface.
    Supports both local (import) and remote (HTTP) modes.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self._session = None

    def _get_session(self):
        if self._session is None:
            import requests
            self._session = requests.Session()
        return self._session

    def reset(self, task_id: str = "simple_review", seed: Optional[int] = None) -> dict:
        """
        Start a new episode.

        Returns:
            obs dict with diff_text, pr_description, commit_message, etc.
        """
        payload = {"task_id": task_id}
        if seed is not None:
            payload["seed"] = seed
        resp = self._get_session().post(f"{self.base_url}/api/reset", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def step(self, action: dict) -> dict:
        """
        Execute one action.

        Args:
            action: Dict with action_type and optional fields
                    (line_number, severity, message, comment_id, reason).

        Returns:
            obs dict with reward, done, existing_comments, author_responses.
        """
        resp = self._get_session().post(f"{self.base_url}/api/step", json=action, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_results(self) -> dict:
        """Get full grader results after episode completion."""
        resp = self._get_session().get(f"{self.base_url}/grader", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def fetch_context(self, file: str = "", lines: str = "1-50") -> dict:
        """
        Fetch additional repository context (costs 1 turn in scored episodes).

        Args:
            file: File path to fetch.
            lines: Line range, e.g. '1-80'.

        Returns:
            dict with content, file, total_lines, related_files.
        """
        resp = self._get_session().get(
            f"{self.base_url}/api/context",
            params={"file": file, "lines": lines},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()


# ─── Prompt builder ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert code reviewer. Analyze PR diffs carefully and identify bugs, security issues, and code quality problems.

You can take ONE action per turn. Available actions (output as JSON):
1. Add a comment: {"action_type": "add_comment", "line_number": <int>, "severity": "<nit|minor|major|critical>", "message": "<description>"}
2. Retract a comment: {"action_type": "retract_comment", "comment_id": "<id>"}
3. Ask for clarification: {"action_type": "request_clarification", "question": "<your question>"}
4. Finalize review: {"action_type": "finalize_review", "reason": "<summary>"}

Focus on real bugs. Avoid flagging non-issues — false positives hurt your score.
Output ONLY the JSON action, nothing else."""


def build_prompt(obs: dict, tokenizer) -> str:
    """
    Build a chat-formatted prompt from a DiffObservation dict.

    Args:
        obs: Observation dict from env.reset() or env.step().
        tokenizer: HuggingFace tokenizer for chat formatting.

    Returns:
        Formatted prompt string ready for model.generate().
    """
    existing = obs.get("existing_comments", [])
    author_responses = obs.get("author_responses", [])

    user_content = f"""## PR Diff
```
{obs.get('diff_text', '')}
```

## Commit Message
{obs.get('commit_message', '')}

## PR Description
{obs.get('pr_description', '')}

## Comments Added So Far ({len(existing)})
{json.dumps(existing, indent=2) if existing else 'None yet'}

## Author Responses
{chr(10).join(f'- {r}' for r in author_responses) if author_responses else 'None yet'}

Step {obs.get('step_num', 0)}/{obs.get('max_steps', 10)}. What is your next action?"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    # Fallback for non-chat tokenizers
    return f"{SYSTEM_PROMPT}\n\n{user_content}\n\nAction:"


def parse_action(text: str) -> dict:
    """
    Parse a JSON action from model output.

    Handles markdown code blocks and partial JSON.

    Args:
        text: Raw model output string.

    Returns:
        Action dict. Falls back to finalize_review on parse failure.
    """
    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    # Extract first {...} block
    match = re.search(r"\{[^{}]+\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"action_type": "finalize_review", "reason": "Could not parse model action."}


# ─── Episode collection ───────────────────────────────────────────────────────

def collect_episode(
    model,
    tokenizer,
    env: CodeReviewEnvClient,
    config: TrainingConfig,
) -> dict:
    """
    Run one complete episode and collect (query, response, reward) triples.

    This is the core data collection function for PPO training.
    The agent runs until done=True or max_steps is reached.

    Args:
        model: HuggingFace CausalLM model.
        tokenizer: Corresponding tokenizer.
        env: CodeReviewEnvClient instance.
        config: Training configuration.

    Returns:
        dict with keys: queries, responses, rewards, final_score, episode_results.
    """
    obs = env.reset(task_id=config.task_id)
    done = obs.get("done", False)

    queries, responses, rewards = [], [], []
    step = 0

    while not done and step < config.max_steps_per_episode:
        # Build prompt
        prompt = build_prompt(obs, tokenizer)
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

        # Generate action
        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=200,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )

        generated = output_ids[0][inputs["input_ids"].shape[1]:]
        response_text = tokenizer.decode(generated, skip_special_tokens=True)

        # Parse and execute action
        action = parse_action(response_text)
        obs = env.step(action)

        reward = float(obs.get("reward", 0.0))
        done = obs.get("done", False)

        queries.append(prompt)
        responses.append(response_text)
        rewards.append(reward)
        step += 1

    # Get final grader results
    episode_results = {}
    if done:
        try:
            episode_results = env.get_results()
        except Exception:
            pass

    return {
        "queries": queries,
        "responses": responses,
        "rewards": rewards,
        "final_score": episode_results.get("composite_score", rewards[-1] if rewards else 0.0),
        "episode_results": episode_results,
    }


# ─── PPO training loop ────────────────────────────────────────────────────────

def train(config: TrainingConfig) -> None:
    """
    Run a minimal PPO training loop using TRL.

    Collects episodes from CodeReviewEnv, computes rewards, and updates
    the model policy using PPO. Saves checkpoints every log_every episodes.

    Args:
        config: TrainingConfig instance.
    """
    try:
        from trl import PPOConfig, PPOTrainer
        from trl.models import AutoModelForCausalLMWithValueHead
    except ImportError:
        print("ERROR: trl not installed. Run: pip install trl")
        sys.exit(1)

    print(f"Loading model: {config.model_name}")
    tokenizer = AutoTokenizer.from_pretrained(config.model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLMWithValueHead.from_pretrained(
        config.model_name,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    )

    ppo_config = PPOConfig(
        model_name=config.model_name,
        learning_rate=config.learning_rate,
        ppo_epochs=config.ppo_epochs,
        batch_size=config.batch_size,
        seed=config.seed,
        log_with="tensorboard" if os.path.exists("runs") else None,
    )

    ppo_trainer = PPOTrainer(config=ppo_config, model=model, tokenizer=tokenizer)
    env = CodeReviewEnvClient(base_url=config.env_url)

    print(f"\nStarting PPO training on CodeReviewEnv")
    print(f"  Task: {config.task_id}")
    print(f"  Episodes: {config.num_episodes}")
    print(f"  Env: {config.env_url}\n")

    all_scores = []

    for ep in range(config.num_episodes):
        episode = collect_episode(model, tokenizer, env, config)

        queries_t = [tokenizer(q, return_tensors="pt")["input_ids"][0] for q in episode["queries"]]
        responses_t = [tokenizer(r, return_tensors="pt")["input_ids"][0] for r in episode["responses"]]
        rewards_t = [torch.tensor(r, dtype=torch.float32) for r in episode["rewards"]]

        if queries_t and responses_t and rewards_t:
            ppo_trainer.step(queries_t, responses_t, rewards_t)

        all_scores.append(episode["final_score"])

        if (ep + 1) % config.log_every == 0:
            recent_mean = sum(all_scores[-config.log_every:]) / config.log_every
            print(f"  Episode {ep+1:3d}/{config.num_episodes} | "
                  f"final_score={episode['final_score']:.3f} | "
                  f"mean_{config.log_every}ep={recent_mean:.3f} | "
                  f"steps={len(episode['rewards'])}")

            # Save checkpoint
            os.makedirs(config.output_dir, exist_ok=True)
            ckpt_path = os.path.join(config.output_dir, f"checkpoint_ep{ep+1}")
            ppo_trainer.model.save_pretrained(ckpt_path)
            tokenizer.save_pretrained(ckpt_path)
            print(f"    Saved checkpoint → {ckpt_path}")

    print(f"\nTraining complete!")
    print(f"  Mean score (all): {sum(all_scores)/len(all_scores):.4f}")
    print(f"  Best score:       {max(all_scores):.4f}")
    print(f"  Final checkpoint: {config.output_dir}/checkpoint_ep{config.num_episodes}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="CodeReviewEnv PPO training example via TRL",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--model-name", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--env-url", default="http://localhost:8000")
    parser.add_argument("--task-id", default="simple_review",
                        choices=["simple_review", "logic_review", "security_review"])
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--steps", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="./rl_checkpoints")
    args = parser.parse_args()

    config = TrainingConfig(
        model_name=args.model_name,
        env_url=args.env_url,
        task_id=args.task_id,
        max_steps_per_episode=args.steps,
        num_episodes=args.episodes,
        learning_rate=args.lr,
        seed=args.seed,
        output_dir=args.output_dir,
    )

    train(config)


if __name__ == "__main__":
    main()
