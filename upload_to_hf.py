"""
Upload CodeReviewEnv to Hugging Face Spaces manually.
Handles the README frontmatter and file upload properly.
"""

import os
import sys
from pathlib import Path
from huggingface_hub import HfApi, upload_folder

REPO_ID = "chetna1910/CodeReviewEnv"
PROJECT_DIR = Path(r"c:\Users\chetn\OpenEnv")

# Files/dirs to exclude from upload
EXCLUDE_PATTERNS = [
    ".git",
    ".git/*",
    "__pycache__",
    "__pycache__/*",
    "**/__pycache__",
    "**/__pycache__/*",
    "*.pyc",
    "outputs",
    "outputs/*",
    ".env",
    "upload_to_hf.py",
]


def create_hf_readme():
    """Create README with proper HF Space frontmatter."""
    # Read existing README
    readme_path = PROJECT_DIR / "README.md"
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Add HF Space frontmatter
    frontmatter = """---
title: CodeReviewEnv
emoji: "\U0001F50D"
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: mit
app_port: 8000
---

"""
    return frontmatter + content


def create_root_dockerfile():
    """Create a Dockerfile at root level for HF Spaces."""
    return """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY server/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Copy application code
COPY . /app/

# Create outputs directory
RUN mkdir -p /app/outputs/logs /app/outputs/evals

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
"""


def main():
    api = HfApi()

    # Verify auth
    user_info = api.whoami()
    print(f"Authenticated as: {user_info['name']}")

    # Ensure space exists
    try:
        api.repo_info(REPO_ID, repo_type="space")
        print(f"Space {REPO_ID} exists")
    except Exception:
        print(f"Creating space {REPO_ID}...")
        api.create_repo(
            repo_id=REPO_ID,
            repo_type="space",
            space_sdk="docker",
            exist_ok=True,
        )
        print(f"Space created!")

    # Write temporary files for upload
    tmp_readme = PROJECT_DIR / "README_HF.md"
    tmp_dockerfile = PROJECT_DIR / "Dockerfile"

    with open(tmp_readme, "w", encoding="utf-8") as f:
        f.write(create_hf_readme())
    print("Created HF README with frontmatter")

    with open(tmp_dockerfile, "w", encoding="utf-8") as f:
        f.write(create_root_dockerfile())
    print("Created root Dockerfile for HF Spaces")

    # Rename README_HF.md to README.md for upload, backup original
    original_readme = PROJECT_DIR / "README.md"
    backup_readme = PROJECT_DIR / "README_BACKUP.md"

    os.rename(original_readme, backup_readme)
    os.rename(tmp_readme, original_readme)

    try:
        print(f"Uploading to {REPO_ID}...")
        upload_folder(
            folder_path=str(PROJECT_DIR),
            repo_id=REPO_ID,
            repo_type="space",
            ignore_patterns=EXCLUDE_PATTERNS,
        )
        print(f"\nDeployment successful!")
        print(f"View your Space at: https://huggingface.co/spaces/{REPO_ID}")
    finally:
        # Restore original README
        os.rename(original_readme, tmp_readme)
        os.rename(backup_readme, original_readme)
        # Clean up temp files
        if tmp_readme.exists():
            os.remove(tmp_readme)
        if tmp_dockerfile.exists():
            os.remove(tmp_dockerfile)
        print("Cleaned up temporary files")


if __name__ == "__main__":
    main()
