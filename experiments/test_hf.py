import requests
import os

token = os.environ.get("HF_TOKEN")
if not token:
    print("NO HF_TOKEN")
else:
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.post(
        "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-Coder-1.5B-Instruct",
        headers=headers,
        json={"inputs": "Code review this PR"}
    )
    print(res.status_code, res.json())
