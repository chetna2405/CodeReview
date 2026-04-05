from huggingface_hub import HfApi

api = HfApi()
info = api.whoami()
print(f"Authenticated as: {info['name']}")

api.upload_file(
    path_or_fileobj="inference.py",
    path_in_repo="inference.py",
    repo_id="chetna1910/CodeReviewEnv",
    repo_type="space",
    commit_message="Add inference.py with [START]/[STEP]/[END] log format",
)
print("inference.py uploaded to HF Space successfully!")
