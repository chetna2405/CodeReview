import random
import time
from locust import HttpUser, task, between

class BenchmarkUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        # Create a session
        payload = {"task_id": "simple_review", "seed": random.randint(1, 10000)}
        res = self.client.post("/api/reset", json=payload)
        self.episode_id = res.json().get("metadata", {}).get("episode_id", "")
        self.step_count = 0

    @task
    def execute_step(self):
        if not self.episode_id:
            return
        
        if self.step_count > 3:
            # Terminate and start a new episode
            self.client.post(
                "/api/step",
                json={
                    "action_type": "approve",
                    "comment_id": "",
                    "severity": "",
                    "message": "Looks good.",
                    "line_number": 0,
                    "question": "",
                    "reason": ""
                },
                headers={"X-Episode-ID": self.episode_id}
            )
            self.on_start()
            return
            
        # Normal step
        action_payload = {
            "action_type": "add_comment",
            "line_number": random.randint(1, 10),
            "severity": "minor",
            "message": "Mock review comment.",
            "comment_id": "",
            "question": "",
            "reason": ""
        }
        self.client.post("/api/step", json=action_payload, headers={"X-Episode-ID": self.episode_id})
        self.step_count += 1
