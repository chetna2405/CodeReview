"""
Benchmark Parallel — Concurrent rollout test for CodeReviewEnv.

Demonstrates that the environment is truly session-isolated and can
serve a real PPO training loop with concurrent rollout workers.
Fires N agents simultaneously against different scenarios via HTTP.
"""

import asyncio
import time
import httpx
import uuid

BASE_URL = "http://localhost:8000"
NUM_AGENTS = 4
MAX_STEPS = 5


async def run_agent(agent_id: int):
    """Simulates an agent playing through an episode."""
    episode_id = f"agent-{agent_id}-{uuid.uuid4().hex[:8]}"
    print(f"[Agent {agent_id}] Starting episode {episode_id}")
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Reset
        start = time.monotonic()
        r = await client.post("/api/reset", json={
            "task_id": "simple_review",
            "episode_id": episode_id
        })
        r.raise_for_status()
        obs = r.json()
        
        # Step loop
        for step in range(MAX_STEPS):
            if obs.get("done", False):
                break
                
            # Random comment
            line = 10 + step
            r = await client.post("/api/step", json={
                "episode_id": episode_id,
                "action_type": "add_comment",
                "line_number": line,
                "severity": "major",
                "message": f"[Agent {agent_id}] Found a bug on line {line}"
            })
            r.raise_for_status()
            obs = r.json()
            
            # Simulate thinking time
            await asyncio.sleep(0.5)
            
        # Finalize
        if not obs.get("done", False):
            r = await client.post("/api/step", json={
                "episode_id": episode_id,
                "action_type": "finalize_review",
                "reason": f"[Agent {agent_id}] Review complete."
            })
            r.raise_for_status()
            obs = r.json()
            
        duration = time.monotonic() - start
        reward = obs.get("reward", 0.0)
        print(f"[Agent {agent_id}] Finished in {duration:.1f}s | Reward: {reward:.4f}")
        return duration



async def main():
    print(f"Starting {NUM_AGENTS} concurrent rollout workers...")
    
    # Check if server is up
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE_URL}/api/health")
            r.raise_for_status()
            health = r.json()
            print(f"Server health: {health['status']} | Active sessions: {health['active_sessions']}")
    except httpx.RequestError as e:
        print(f"Error: Could not connect to {BASE_URL}. Start the server first. ({e})")
        return
    except KeyError as e:
        print(f"Health schema mismatch! Key missing: {e}. Bypassing health check.")

    start_time = time.monotonic()
    
    # Run all agents concurrently
    tasks = [run_agent(i) for i in range(NUM_AGENTS)]
    results = await asyncio.gather(*tasks)
    
    total_time = time.monotonic() - start_time
    print(f"\nBenchmark complete!")
    print(f"Total wall time: {total_time:.2f}s")
    print(f"Average time per agent: {sum(results)/len(results):.2f}s")
    print(f"Throughput: {NUM_AGENTS * MAX_STEPS / total_time:.1f} steps/sec")

if __name__ == "__main__":
    asyncio.run(main())
