#!/usr/bin/env python3
"""Generate the full CodeReviewEnv scenario corpus (50+ scenarios)."""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))

def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ── EASY PUBLIC (15 scenarios) ────────────────────────────────────────────────
easy_public = [
  {
    "id": "scenario_001", "source": {"repo": "psf/requests", "note": "sanitized"},
    "difficulty": "easy", "language": "python",
    "diff_text": "--- a/utils.py\n+++ b/utils.py\n@@ -10,7 +10,7 @@\n def get_users(ids):\n     results = []\n-    for i in range(len(ids)):\n+    for i in range(len(ids) - 1):\n         results.append(db.fetch(ids[i]))\n     return results",
    "commit_message": "Optimize user fetching loop",
    "pr_description": "Minor loop optimization.",
    "file_path": "utils.py", "file_context": "def get_users(ids):\n    results = []\n    for i in range(len(ids) - 1):\n        results.append(db.fetch(ids[i]))\n    return results",
    "gold_annotations": [{"line": 13, "type": "bug", "severity": "critical", "issue": "Off-by-one: range(len(ids)-1) skips the last element.", "reference": ""}]
  },
  {
    "id": "scenario_002", "source": {"repo": "django/django", "note": "sanitized"},
    "difficulty": "easy", "language": "python",
    "diff_text": "--- a/api/views.py\n+++ b/api/views.py\n@@ -5,8 +5,6 @@\n def get_profile(request):\n     user_id = request.GET.get('user_id')\n-    if user_id is None:\n-        return HttpResponse(status=400)\n     user = User.objects.get(id=user_id)\n     return JsonResponse(user.to_dict())",
    "commit_message": "Simplify profile view",
    "pr_description": "Removes redundant None check.",
    "file_path": "api/views.py", "file_context": "def get_profile(request):\n    user_id = request.GET.get('user_id')\n    user = User.objects.get(id=user_id)\n    return JsonResponse(user.to_dict())",
    "gold_annotations": [{"line": 7, "type": "bug", "severity": "critical", "issue": "Removed None check — User.objects.get(id=None) raises unhandled exception.", "reference": ""}]
  },
  {
    "id": "scenario_003", "source": {"repo": "pallets/flask", "note": "sanitized"},
    "difficulty": "easy", "language": "python",
    "diff_text": "--- a/config.py\n+++ b/config.py\n@@ -3,4 +3,6 @@\n import os\n SECRET_KEY = os.environ.get('SECRET_KEY', 'changeme')\n+API_TOKEN = 'sk-proj-abc123def456ghi789'\n DEBUG = True",
    "commit_message": "Add API token for analytics",
    "pr_description": "Adds analytics provider token.",
    "file_path": "config.py", "file_context": "import os\nSECRET_KEY = os.environ.get('SECRET_KEY', 'changeme')\nAPI_TOKEN = 'sk-proj-abc123def456ghi789'\nDEBUG = True",
    "gold_annotations": [{"line": 4, "type": "security", "severity": "critical", "issue": "Hardcoded API token in source. Use os.environ.get() instead.", "reference": "OWASP A02:2021"}]
  },
  {
    "id": "scenario_004", "source": {"repo": "psf/black", "note": "sanitized"},
    "difficulty": "easy", "language": "python",
    "diff_text": "--- a/auth/login.py\n+++ b/auth/login.py\n@@ -6,10 +6,8 @@\n def authenticate(username, password):\n     user = User.find(username)\n     if not user:\n         return None\n-    if not user.check_password(password):\n-        return None\n     return user",
    "commit_message": "Simplify auth flow",
    "pr_description": "Removes redundant password check.",
    "file_path": "auth/login.py", "file_context": "def authenticate(username, password):\n    user = User.find(username)\n    if not user:\n        return None\n    return user",
    "gold_annotations": [{"line": 11, "type": "security", "severity": "critical", "issue": "Password verification removed — any password authenticates any user.", "reference": "OWASP A07:2021"}]
  },
  {
    "id": "scenario_005", "source": {"repo": "apache/airflow", "note": "sanitized"},
    "difficulty": "easy", "language": "python",
    "diff_text": "--- a/models/user.py\n+++ b/models/user.py\n@@ -4,4 +4,4 @@\n class User:\n     def __init__(self, name, email, age):\n         self.name = name\n-        self.email = email\n+        self.emal = email\n         self.age = age",
    "commit_message": "Refactor User model",
    "pr_description": "Minor model cleanup.",
    "file_path": "models/user.py", "file_context": "class User:\n    def __init__(self, name, email, age):\n        self.name = name\n        self.emal = email\n        self.age = age",
    "gold_annotations": [{"line": 7, "type": "bug", "severity": "critical", "issue": "Typo: self.emal should be self.email — breaks all code accessing user.email.", "reference": ""}]
  },
  {
    "id": "scenario_006", "source": {"repo": "encode/httpx", "note": "sanitized"},
    "difficulty": "easy", "language": "python",
    "diff_text": "--- a/cache.py\n+++ b/cache.py\n@@ -5,8 +5,6 @@\n class Cache:\n     def __init__(self, ttl=300):\n         self._data = {}\n-        self._timestamps = {}\n         self._ttl = ttl\n     def get(self, key):\n-        if key in self._data and not self._is_expired(key):\n+        if key in self._data:\n             return self._data[key]",
    "commit_message": "Simplify cache — TTL not needed",
    "pr_description": "Removes TTL tracking to reduce complexity.",
    "file_path": "cache.py", "file_context": "class Cache:\n    def __init__(self, ttl=300):\n        self._data = {}\n        self._ttl = ttl\n    def get(self, key):\n        if key in self._data:\n            return self._data[key]\n        return None",
    "gold_annotations": [{"line": 10, "type": "bug", "severity": "major", "issue": "TTL expiry removed — cache grows unboundedly. Memory leak in long-running processes.", "reference": ""}]
  },
  {
    "id": "scenario_007", "source": {"repo": "tiangolo/fastapi", "note": "sanitized"},
    "difficulty": "easy", "language": "python",
    "diff_text": "--- a/inventory.py\n+++ b/inventory.py\n@@ -8,7 +8,7 @@\n def update_stock(pid, qty):\n     product = Product.get(pid)\n     if product is None:\n-        raise ProductNotFoundError(f'Product {pid} not found')\n+        return\n     product.stock += qty\n     product.save()\n     return True",
    "commit_message": "Handle missing products gracefully",
    "pr_description": "Avoids exception for missing products.",
    "file_path": "inventory.py", "file_context": "def update_stock(pid, qty):\n    product = Product.get(pid)\n    if product is None:\n        return\n    product.stock += qty\n    product.save()\n    return True",
    "gold_annotations": [{"line": 11, "type": "bug", "severity": "major", "issue": "Silent None return violates bool return type. Callers can't distinguish missing product from failure.", "reference": ""}]
  },
  {
    "id": "scenario_008", "source": {"repo": "celery/celery", "note": "sanitized"},
    "difficulty": "easy", "language": "python",
    "diff_text": "--- a/scheduler.py\n+++ b/scheduler.py\n@@ -6,8 +6,8 @@\n DELAYS = [1, 5, 15, 60]\n def run_with_retry(fn, max_retries=3):\n     for attempt in range(max_retries):\n         try:\n             return fn()\n-        except Exception as e:\n+        except Exception:\n             time.sleep(DELAYS[attempt])",
    "commit_message": "Remove unused variable in retry loop",
    "pr_description": "Removes linter warning for unused 'e'.",
    "file_path": "scheduler.py", "file_context": "DELAYS = [1, 5, 15, 60]\ndef run_with_retry(fn, max_retries=3):\n    for attempt in range(max_retries):\n        try:\n            return fn()\n        except Exception:\n            time.sleep(DELAYS[attempt])",
    "gold_annotations": [
      {"line": 11, "type": "bug", "severity": "major", "issue": "DELAYS[attempt] IndexError if max_retries > 4. No bounds check.", "reference": ""},
      {"line": 11, "type": "style", "severity": "minor", "issue": "Exception swallowed silently. Add logging for debuggability.", "reference": ""}
    ]
  },
  {
    "id": "scenario_009", "source": {"repo": "psf/requests", "note": "sanitized"},
    "difficulty": "easy", "language": "python",
    "diff_text": "--- a/utils/strings.py\n+++ b/utils/strings.py\n@@ -2,6 +2,6 @@\n def truncate(text, max_len=100):\n-    if len(text) <= max_len:\n+    if len(text) < max_len:\n         return text\n-    return text[:max_len - 3] + '...'\n+    return text[:max_len] + '...'",
    "commit_message": "Fix edge case in truncate",
    "pr_description": "Fixes truncation for exact-length strings.",
    "file_path": "utils/strings.py", "file_context": "def truncate(text, max_len=100):\n    if len(text) < max_len:\n        return text\n    return text[:max_len] + '...'",
    "gold_annotations": [
      {"line": 3, "type": "bug", "severity": "minor", "issue": "< should be <= : strings at exactly max_len now get truncated unnecessarily.", "reference": ""},
      {"line": 5, "type": "bug", "severity": "major", "issue": "text[:max_len]+'...' exceeds max_len by 3. Should be text[:max_len-3]+'...'.", "reference": ""}
    ]
  },
  {
    "id": "scenario_010", "source": {"repo": "django/django", "note": "sanitized"},
    "difficulty": "easy", "language": "python",
    "diff_text": "--- a/models/user.py\n+++ b/models/user.py\n@@ -8,4 +8,4 @@\n     def is_adult(self):\n-        return self.age >= 18\n+        return self.age > 18",
    "commit_message": "Fix age validation",
    "pr_description": "Corrects adult age check.",
    "file_path": "models/user.py", "file_context": "class User:\n    def is_adult(self):\n        return self.age > 18",
    "gold_annotations": [{"line": 9, "type": "bug", "severity": "major", "issue": "> 18 excludes exactly-18-year-olds who are legal adults. Should be >= 18.", "reference": ""}]
  },
  {
    "id": "scenario_011", "source": {"repo": "encode/starlette", "note": "sanitized"},
    "difficulty": "easy", "language": "python",
    "diff_text": "--- a/middleware.py\n+++ b/middleware.py\n@@ -10,6 +10,4 @@\n def rate_limit(request, limit=100):\n     key = request.client.host\n-    if not redis.exists(key):\n-        redis.setex(key, 60, 0)\n     count = redis.incr(key)\n     return count <= limit",
    "commit_message": "Simplify rate limiter",
    "pr_description": "Removes redundant init — incr creates key.",
    "file_path": "middleware.py", "file_context": "def rate_limit(request, limit=100):\n    key = request.client.host\n    count = redis.incr(key)\n    return count <= limit",
    "gold_annotations": [{"line": 13, "type": "bug", "severity": "major", "issue": "Without setex, the key never expires. Rate limit window is permanent — one request bans the IP forever.", "reference": ""}]
  },
  {
    "id": "scenario_012", "source": {"repo": "pallets/flask", "note": "sanitized"},
    "difficulty": "easy", "language": "python",
    "diff_text": "--- a/helpers.py\n+++ b/helpers.py\n@@ -1,6 +1,6 @@\n import hashlib\n def hash_password(pw):\n-    return hashlib.sha256(pw.encode()).hexdigest()\n+    return hashlib.md5(pw.encode()).hexdigest()",
    "commit_message": "Switch to faster hash for passwords",
    "pr_description": "MD5 is faster than SHA-256 for our use case.",
    "file_path": "helpers.py", "file_context": "import hashlib\ndef hash_password(pw):\n    return hashlib.md5(pw.encode()).hexdigest()",
    "gold_annotations": [{"line": 3, "type": "security", "severity": "critical", "issue": "MD5 is cryptographically broken for passwords. Use bcrypt, argon2, or at minimum SHA-256 with salt.", "reference": "OWASP A02:2021"}]
  },
  {
    "id": "scenario_013", "source": {"repo": "aio-libs/aiohttp", "note": "sanitized"},
    "difficulty": "easy", "language": "python",
    "diff_text": "--- a/db.py\n+++ b/db.py\n@@ -4,6 +4,4 @@\n async def get_conn():\n     conn = await pool.acquire()\n-    try:\n-        yield conn\n-    finally:\n-        await pool.release(conn)\n+    return conn",
    "commit_message": "Simplify connection helper",
    "pr_description": "Returns connection directly instead of context manager.",
    "file_path": "db.py", "file_context": "async def get_conn():\n    conn = await pool.acquire()\n    return conn",
    "gold_annotations": [{"line": 5, "type": "bug", "severity": "critical", "issue": "Connection leak: pool.release() never called. Pool exhausts under load causing deadlock.", "reference": ""}]
  },
  {
    "id": "scenario_014", "source": {"repo": "boto/boto3", "note": "sanitized"},
    "difficulty": "easy", "language": "python",
    "diff_text": "--- a/config.py\n+++ b/config.py\n@@ -1,4 +1,4 @@\n AWS_REGION = 'us-east-1'\n-AWS_SECRET = os.environ.get('AWS_SECRET')\n+AWS_SECRET = 'AKIAIOSFODNN7EXAMPLE'\n BUCKET = 'prod-data'",
    "commit_message": "Hardcode AWS key for local dev",
    "pr_description": "Hardcoded for easier local development.",
    "file_path": "config.py", "file_context": "AWS_REGION = 'us-east-1'\nAWS_SECRET = 'AKIAIOSFODNN7EXAMPLE'\nBUCKET = 'prod-data'",
    "gold_annotations": [{"line": 2, "type": "security", "severity": "critical", "issue": "AWS secret key committed to source. Rotate immediately. Use environment variable.", "reference": "OWASP A02:2021"}]
  },
  {
    "id": "scenario_015", "source": {"repo": "psf/black", "note": "sanitized"},
    "difficulty": "easy", "language": "python",
    "diff_text": "--- a/parser.py\n+++ b/parser.py\n@@ -3,6 +3,5 @@\n def parse_config(path):\n-    if not os.path.exists(path):\n-        raise FileNotFoundError(f'Config not found: {path}')\n     with open(path) as f:\n         return json.load(f)",
    "commit_message": "Remove redundant file check",
    "pr_description": "open() already raises FileNotFoundError.",
    "file_path": "parser.py", "file_context": "def parse_config(path):\n    with open(path) as f:\n        return json.load(f)",
    "gold_annotations": [{"line": 4, "type": "bug", "severity": "minor", "issue": "Removing explicit check loses the descriptive error message with file path. open() error is less clear.", "reference": ""}]
  },
]

# ── MEDIUM PUBLIC (12 scenarios) ──────────────────────────────────────────────
medium_public = [
  {
    "id": "scenario_016", "source": {"repo": "celery/celery", "note": "sanitized"},
    "difficulty": "medium", "language": "python",
    "diff_text": "--- a/tasks/worker.py\n+++ b/tasks/worker.py\n@@ -12,9 +12,7 @@\n def process_batch(items):\n     results = []\n-    lock = threading.Lock()\n     threads = []\n     for item in items:\n-        def worker(i):\n-            with lock:\n-                results.append(process(i))\n+        def worker(i):\n+            results.append(process(i))\n         t = threading.Thread(target=worker, args=(item,))\n         threads.append(t)\n         t.start()\n     for t in threads:\n         t.join()\n     return results",
    "commit_message": "Remove lock — process() is thread-safe",
    "pr_description": "Lock was unnecessary overhead.",
    "file_path": "tasks/worker.py", "file_context": "import threading\ndef process_batch(items):\n    results = []\n    threads = []\n    for item in items:\n        def worker(i):\n            results.append(process(i))\n        t = threading.Thread(target=worker, args=(item,))\n        threads.append(t)\n        t.start()\n    for t in threads:\n        t.join()\n    return results",
    "gold_annotations": [
      {"line": 19, "type": "bug", "severity": "critical", "issue": "Race condition: list.append() is not atomic in all Python implementations. Lock was needed.", "reference": ""},
      {"line": 17, "type": "bug", "severity": "major", "issue": "Late binding closure bug: all thread workers capture same loop variable. Use args=(item,) correctly.", "reference": ""}
    ]
  },
  {
    "id": "scenario_017", "source": {"repo": "sqlalchemy/sqlalchemy", "note": "sanitized"},
    "difficulty": "medium", "language": "python",
    "diff_text": "--- a/db/queries.py\n+++ b/db/queries.py\n@@ -5,6 +5,6 @@\n def search_users(name):\n-    query = 'SELECT * FROM users WHERE name = %s'\n-    return db.execute(query, (name,))\n+    query = f'SELECT * FROM users WHERE name = \"{name}\"'\n+    return db.execute(query)",
    "commit_message": "Simplify search query construction",
    "pr_description": "Use f-string for cleaner query.",
    "file_path": "db/queries.py", "file_context": "def search_users(name):\n    query = f'SELECT * FROM users WHERE name = \"{name}\"'\n    return db.execute(query)",
    "gold_annotations": [{"line": 8, "type": "security", "severity": "critical", "issue": "SQL injection: f-string interpolation replaced parameterized query. Input not sanitized.", "reference": "OWASP A03:2021"}]
  },
  {
    "id": "scenario_018", "source": {"repo": "encode/django-rest-framework", "note": "sanitized"},
    "difficulty": "medium", "language": "python",
    "diff_text": "--- a/api/serializers.py\n+++ b/api/serializers.py\n@@ -15,8 +15,6 @@\n class UserSerializer(serializers.Serializer):\n     email = serializers.EmailField()\n-    def validate_email(self, value):\n-        if User.objects.filter(email=value).exists():\n-            raise serializers.ValidationError('Email already registered')\n-        return value\n     def create(self, data):\n         return User.objects.create(**data)",
    "commit_message": "Remove duplicate email validation — handled by DB",
    "pr_description": "DB unique constraint handles duplicates.",
    "file_path": "api/serializers.py", "file_context": "class UserSerializer(serializers.Serializer):\n    email = serializers.EmailField()\n    def create(self, data):\n        return User.objects.create(**data)",
    "gold_annotations": [{"line": 18, "type": "bug", "severity": "major", "issue": "Removing app-level check means IntegrityError leaks to client as 500. Should return 400 with friendly message.", "reference": ""}]
  },
  {
    "id": "scenario_019", "source": {"repo": "aio-libs/aiohttp", "note": "sanitized"},
    "difficulty": "medium", "language": "python",
    "diff_text": "--- a/session.py\n+++ b/session.py\n@@ -8,6 +8,4 @@\n async def fetch(url, session):\n-    async with session.get(url) as resp:\n-        resp.raise_for_status()\n-        return await resp.json()\n+    resp = await session.get(url)\n+    return await resp.json()",
    "commit_message": "Simplify HTTP fetch helper",
    "pr_description": "Removes context manager overhead.",
    "file_path": "session.py", "file_context": "async def fetch(url, session):\n    resp = await session.get(url)\n    return await resp.json()",
    "gold_annotations": [
      {"line": 11, "type": "bug", "severity": "major", "issue": "Response not used as context manager — underlying connection not released. Resource leak.", "reference": ""},
      {"line": 11, "type": "bug", "severity": "minor", "issue": "raise_for_status() removed — HTTP 4xx/5xx silently returned as JSON parse errors.", "reference": ""}
    ]
  },
  {
    "id": "scenario_020", "source": {"repo": "tornadoweb/tornado", "note": "sanitized"},
    "difficulty": "medium", "language": "python",
    "diff_text": "--- a/handlers.py\n+++ b/handlers.py\n@@ -10,7 +10,5 @@\n class FileHandler(BaseHandler):\n     def get(self, path):\n-        safe_path = os.path.normpath(os.path.join(BASE_DIR, path))\n-        if not safe_path.startswith(BASE_DIR):\n-            raise HTTPError(403)\n+        safe_path = os.path.join(BASE_DIR, path)\n         with open(safe_path) as f:\n             self.write(f.read())",
    "commit_message": "Simplify file serving path handling",
    "pr_description": "Removes redundant path normalization.",
    "file_path": "handlers.py", "file_context": "class FileHandler(BaseHandler):\n    def get(self, path):\n        safe_path = os.path.join(BASE_DIR, path)\n        with open(safe_path) as f:\n            self.write(f.read())",
    "gold_annotations": [{"line": 14, "type": "security", "severity": "critical", "issue": "Path traversal: removed normpath + prefix check allows ../../etc/passwd access.", "reference": "OWASP A01:2021"}]
  },
  {
    "id": "scenario_021", "source": {"repo": "pallets/werkzeug", "note": "sanitized"},
    "difficulty": "medium", "language": "python",
    "diff_text": "--- a/crypto.py\n+++ b/crypto.py\n@@ -4,6 +4,6 @@\n import hmac, hashlib\n def verify_token(token, stored):\n-    return hmac.compare_digest(token, stored)\n+    return token == stored",
    "commit_message": "Simplify token comparison",
    "pr_description": "Direct equality is simpler and equivalent.",
    "file_path": "crypto.py", "file_context": "import hmac, hashlib\ndef verify_token(token, stored):\n    return token == stored",
    "gold_annotations": [{"line": 5, "type": "security", "severity": "critical", "issue": "Timing attack: == short-circuits on first mismatch. Use hmac.compare_digest() for constant-time comparison.", "reference": "OWASP A02:2021"}]
  },
  {
    "id": "scenario_022", "source": {"repo": "encode/httpx", "note": "sanitized"},
    "difficulty": "medium", "language": "python",
    "diff_text": "--- a/pagination.py\n+++ b/pagination.py\n@@ -7,6 +7,6 @@\n def paginate(items, page, size=20):\n-    start = (page - 1) * size\n+    start = page * size\n     end = start + size\n     return items[start:end]",
    "commit_message": "Fix pagination offset",
    "pr_description": "Corrects page offset calculation.",
    "file_path": "pagination.py", "file_context": "def paginate(items, page, size=20):\n    start = page * size\n    end = start + size\n    return items[start:end]",
    "gold_annotations": [{"line": 8, "type": "bug", "severity": "major", "issue": "page*size skips first page (page=1 starts at item 20). Should be (page-1)*size.", "reference": ""}]
  },
  {
    "id": "scenario_023", "source": {"repo": "boto/botocore", "note": "sanitized"},
    "difficulty": "medium", "language": "python",
    "diff_text": "--- a/retry.py\n+++ b/retry.py\n@@ -6,6 +6,6 @@\n def with_retry(fn, max_retries=3, backoff=2):\n     delay = 1\n     for i in range(max_retries):\n         try:\n             return fn()\n-        except TransientError:\n+        except Exception:\n             time.sleep(delay)\n             delay *= backoff",
    "commit_message": "Retry on all exceptions",
    "pr_description": "Retry on any error, not just transient ones.",
    "file_path": "retry.py", "file_context": "def with_retry(fn, max_retries=3, backoff=2):\n    delay = 1\n    for i in range(max_retries):\n        try:\n            return fn()\n        except Exception:\n            time.sleep(delay)\n            delay *= backoff",
    "gold_annotations": [{"line": 11, "type": "bug", "severity": "major", "issue": "Catching bare Exception retries on programming errors (TypeError, etc) that won't resolve with retry.", "reference": ""}]
  },
  {
    "id": "scenario_024", "source": {"repo": "marshmallow-code/marshmallow", "note": "sanitized"},
    "difficulty": "medium", "language": "python",
    "diff_text": "--- a/schema.py\n+++ b/schema.py\n@@ -9,6 +9,4 @@\n class UserSchema(Schema):\n     name = fields.Str(required=True)\n     role = fields.Str()\n-    class Meta:\n-        unknown = EXCLUDE\n",
    "commit_message": "Remove Meta class — not needed",
    "pr_description": "Simplify schema, Meta was boilerplate.",
    "file_path": "schema.py", "file_context": "class UserSchema(Schema):\n    name = fields.Str(required=True)\n    role = fields.Str()",
    "gold_annotations": [{"line": 12, "type": "security", "severity": "minor", "issue": "Removing EXCLUDE means unknown fields pass through deserialization. Mass assignment risk.", "reference": "OWASP A08:2021"}]
  },
  {
    "id": "scenario_025", "source": {"repo": "redis/redis-py", "note": "sanitized"},
    "difficulty": "medium", "language": "python",
    "diff_text": "--- a/pubsub.py\n+++ b/pubsub.py\n@@ -14,7 +14,5 @@\n class EventBus:\n     def publish(self, channel, data):\n-        payload = json.dumps(data)\n-        if len(payload) > MAX_SIZE:\n-            raise ValueError('Payload too large')\n+        payload = json.dumps(data)\n         self.redis.publish(channel, payload)",
    "commit_message": "Remove payload size check",
    "pr_description": "Redis handles large payloads fine.",
    "file_path": "pubsub.py", "file_context": "class EventBus:\n    def publish(self, channel, data):\n        payload = json.dumps(data)\n        self.redis.publish(channel, payload)",
    "gold_annotations": [{"line": 17, "type": "bug", "severity": "major", "issue": "Unbounded payload allows memory exhaustion DoS. Redis pub/sub has practical size limits.", "reference": ""}]
  },
  {
    "id": "scenario_026", "source": {"repo": "pydantic/pydantic", "note": "sanitized"},
    "difficulty": "medium", "language": "python",
    "diff_text": "--- a/validators.py\n+++ b/validators.py\n@@ -5,4 +5,4 @@\n def validate_age(v):\n-    if not isinstance(v, int) or v < 0 or v > 150:\n+    if not isinstance(v, int) or v < 0:\n         raise ValueError('Invalid age')\n     return v",
    "commit_message": "Loosen age validation",
    "pr_description": "Remove arbitrary 150 upper bound.",
    "file_path": "validators.py", "file_context": "def validate_age(v):\n    if not isinstance(v, int) or v < 0:\n        raise ValueError('Invalid age')\n    return v",
    "gold_annotations": [{"line": 6, "type": "bug", "severity": "minor", "issue": "Removing upper bound allows absurd values (age=99999) corrupting downstream analytics.", "reference": ""}]
  },
  {
    "id": "scenario_027", "source": {"repo": "mitsuhiko/jinja", "note": "sanitized"},
    "difficulty": "medium", "language": "python",
    "diff_text": "--- a/render.py\n+++ b/render.py\n@@ -6,6 +6,6 @@\n from jinja2 import Environment\n-env = Environment(autoescape=True)\n+env = Environment(autoescape=False)\n def render(template_str, context):\n     t = env.from_string(template_str)\n     return t.render(**context)",
    "commit_message": "Disable autoescape for raw HTML support",
    "pr_description": "Some templates need unescaped HTML.",
    "file_path": "render.py", "file_context": "from jinja2 import Environment\nenv = Environment(autoescape=False)\ndef render(template_str, context):\n    t = env.from_string(template_str)\n    return t.render(**context)",
    "gold_annotations": [{"line": 7, "type": "security", "severity": "critical", "issue": "autoescape=False opens XSS vulnerability if any user-controlled data reaches templates.", "reference": "OWASP A03:2021"}]
  },
]

# ── HARD PUBLIC (8 scenarios) ─────────────────────────────────────────────────
hard_public = [
  {
    "id": "scenario_028", "source": {"repo": "django/django", "note": "sanitized"},
    "difficulty": "hard", "language": "python",
    "diff_text": "--- a/views/upload.py\n+++ b/views/upload.py\n@@ -12,10 +12,7 @@\n def upload_file(request):\n     f = request.FILES['file']\n-    name = os.path.basename(f.name)\n-    if not name.endswith(('.jpg','.png','.gif')):\n-        return HttpResponse(status=400)\n     dest = os.path.join(UPLOAD_DIR, f.name)\n     with open(dest, 'wb') as out:\n         out.write(f.read())",
    "commit_message": "Simplify upload handler",
    "pr_description": "Remove redundant validation.",
    "file_path": "views/upload.py", "file_context": "def upload_file(request):\n    f = request.FILES['file']\n    dest = os.path.join(UPLOAD_DIR, f.name)\n    with open(dest, 'wb') as out:\n        out.write(f.read())",
    "gold_annotations": [
      {"line": 15, "type": "security", "severity": "critical", "issue": "Arbitrary file upload: type validation removed. Attacker can upload .php/.py shell.", "reference": "OWASP A01:2021"},
      {"line": 15, "type": "security", "severity": "critical", "issue": "Path traversal via f.name — user controls filename. Use secure_filename().", "reference": "OWASP A01:2021"},
      {"line": 17, "type": "bug", "severity": "major", "issue": "f.read() loads entire file into memory. DoS via large file upload.", "reference": ""}
    ]
  },
  {
    "id": "scenario_029", "source": {"repo": "pallets/flask", "note": "sanitized"},
    "difficulty": "hard", "language": "python",
    "diff_text": "--- a/api/exec.py\n+++ b/api/exec.py\n@@ -8,6 +8,6 @@\n @app.route('/run')\n def run_code():\n     code = request.args.get('code', '')\n-    restricted = RestrictedPython.compile(code)\n-    exec(restricted, {})\n+    exec(code)\n     return 'ok'",
    "commit_message": "Remove RestrictedPython overhead",
    "pr_description": "Simplify code execution endpoint.",
    "file_path": "api/exec.py", "file_context": "@app.route('/run')\ndef run_code():\n    code = request.args.get('code', '')\n    exec(code)\n    return 'ok'",
    "gold_annotations": [{"line": 11, "type": "security", "severity": "critical", "issue": "Remote code execution: unfiltered exec() of user input. Full server compromise.", "reference": "OWASP A03:2021"}]
  },
  {
    "id": "scenario_030", "source": {"repo": "encode/django-rest-framework", "note": "sanitized"},
    "difficulty": "hard", "language": "python",
    "diff_text": "--- a/api/admin.py\n+++ b/api/admin.py\n@@ -10,7 +10,5 @@\n @require_POST\n def delete_user(request, user_id):\n-    if not request.user.is_staff:\n-        return HttpResponseForbidden()\n     user = User.objects.get(id=user_id)\n     user.delete()\n     return JsonResponse({'status': 'deleted'})",
    "commit_message": "Remove stale permission check",
    "pr_description": "Auth handled by middleware now.",
    "file_path": "api/admin.py", "file_context": "@require_POST\ndef delete_user(request, user_id):\n    user = User.objects.get(id=user_id)\n    user.delete()\n    return JsonResponse({'status': 'deleted'})",
    "gold_annotations": [
      {"line": 13, "type": "security", "severity": "critical", "issue": "Authorization check removed — any authenticated user can delete any other user.", "reference": "OWASP A01:2021"},
      {"line": 14, "type": "security", "severity": "major", "issue": "IDOR: user_id from URL not validated against ownership. Horizontal privilege escalation.", "reference": "OWASP A01:2021"}
    ]
  },
  {
    "id": "scenario_031", "source": {"repo": "yaml/pyyaml", "note": "sanitized"},
    "difficulty": "hard", "language": "python",
    "diff_text": "--- a/loader.py\n+++ b/loader.py\n@@ -3,4 +3,4 @@\n import yaml\n def load_config(path):\n     with open(path) as f:\n-        return yaml.safe_load(f)\n+        return yaml.load(f)",
    "commit_message": "Use yaml.load for full feature support",
    "pr_description": "safe_load was too restrictive.",
    "file_path": "loader.py", "file_context": "import yaml\ndef load_config(path):\n    with open(path) as f:\n        return yaml.load(f)",
    "gold_annotations": [{"line": 5, "type": "security", "severity": "critical", "issue": "yaml.load() without Loader= allows arbitrary Python object deserialization. Use yaml.safe_load().", "reference": "OWASP A08:2021"}]
  },
  {
    "id": "scenario_032", "source": {"repo": "requests/requests", "note": "sanitized"},
    "difficulty": "hard", "language": "python",
    "diff_text": "--- a/client.py\n+++ b/client.py\n@@ -7,6 +7,6 @@\n def fetch(url):\n-    resp = requests.get(url, timeout=10, verify=True)\n+    resp = requests.get(url, timeout=10, verify=False)\n     resp.raise_for_status()\n     return resp.json()",
    "commit_message": "Disable SSL verification for compatibility",
    "pr_description": "Some internal services have self-signed certs.",
    "file_path": "client.py", "file_context": "def fetch(url):\n    resp = requests.get(url, timeout=10, verify=False)\n    resp.raise_for_status()\n    return resp.json()",
    "gold_annotations": [{"line": 8, "type": "security", "severity": "critical", "issue": "verify=False disables TLS certificate validation — MITM attacks undetectable. Use custom CA bundle instead.", "reference": "OWASP A07:2021"}]
  },
  {
    "id": "scenario_033", "source": {"repo": "tiangolo/fastapi", "note": "sanitized"},
    "difficulty": "hard", "language": "python",
    "diff_text": "--- a/auth/jwt.py\n+++ b/auth/jwt.py\n@@ -8,7 +8,7 @@\n import jwt\n def decode_token(token):\n-    return jwt.decode(token, SECRET, algorithms=['HS256'])\n+    return jwt.decode(token, options={'verify_signature': False})",
    "commit_message": "Skip JWT verification in dev mode",
    "pr_description": "Makes local development easier.",
    "file_path": "auth/jwt.py", "file_context": "import jwt\ndef decode_token(token):\n    return jwt.decode(token, options={'verify_signature': False})",
    "gold_annotations": [{"line": 9, "type": "security", "severity": "critical", "issue": "JWT signature verification disabled — any token accepted. Complete authentication bypass.", "reference": "OWASP A07:2021"}]
  },
  {
    "id": "scenario_034", "source": {"repo": "django/django", "note": "sanitized"},
    "difficulty": "hard", "language": "python",
    "diff_text": "--- a/views/render.py\n+++ b/views/render.py\n@@ -6,6 +6,6 @@\n from django.template import Template, Context\n def render_user_template(request, template_text):\n     user_data = {'user': request.user, 'query': request.GET}\n-    t = Template(template_text)\n+    t = Template(template_text)  # user-supplied\n     return HttpResponse(t.render(Context(user_data)))",
    "commit_message": "Add comment for clarity",
    "pr_description": "Clarifies that template is user-supplied.",
    "file_path": "views/render.py", "file_context": "from django.template import Template, Context\ndef render_user_template(request, template_text):\n    user_data = {'user': request.user, 'query': request.GET}\n    t = Template(template_text)\n    return HttpResponse(t.render(Context(user_data)))",
    "gold_annotations": [{"line": 9, "type": "security", "severity": "critical", "issue": "Server-Side Template Injection: user-controlled template_text rendered by Django engine. Read env vars, execute code.", "reference": "OWASP A03:2021"}]
  },
  {
    "id": "scenario_035",
    "source": {"repo": "cross-file-example", "note": "synthetic cross-file dependency bug"},
    "difficulty": "hard", "language": "python",
    "diff_text": "--- a/services/user_service.py\n+++ b/services/user_service.py\n@@ -10,4 +10,4 @@\n def get_user_id(username: str) -> str:  # BUG: was int\n-    result = db.query('SELECT id FROM users WHERE name=%s', (username,))\n-    return result[0][0]  # returns int\n+    result = db.query(f'SELECT id FROM users WHERE name=\"{username}\"')\n+    return str(result[0][0])  # now returns str\n",
    "commit_message": "Stringify user ID for JSON compat",
    "pr_description": "JSON serialization needed string user IDs.",
    "file_path": "services/user_service.py",
    "file_context": "# services/user_service.py\ndef get_user_id(username: str) -> str:\n    result = db.query(f'SELECT id FROM users WHERE name=\"{username}\"')\n    return str(result[0][0])\n\n# profile_service.py (unchanged, but broken)\n# def load_profile(user_id: int):\n#     offset = user_id * PAGE_SIZE  # TypeError: str * int at runtime",
    "gold_annotations": [
      {"line": 11, "type": "security", "severity": "critical", "issue": "SQL injection: f-string query construction. Parameterized query removed.", "reference": "OWASP A03:2021"},
      {"line": 12, "type": "bug", "severity": "major", "issue": "Return type changed int→str breaks profile_service.py:load_profile() which multiplies user_id*PAGE_SIZE. Cross-file type contract violation.", "reference": ""}
    ]
  },
]

# ── HIDDEN EASY (3) ───────────────────────────────────────────────────────────
easy_hidden = [
  {
    "id": "scenario_h_001", "source": {"repo": "psf/requests", "note": "sanitized — hidden eval set"},
    "difficulty": "easy", "language": "python",
    "diff_text": "--- a/utils.py\n+++ b/utils.py\n@@ -4,4 +4,4 @@\n def divide(a, b):\n-    if b == 0: raise ZeroDivisionError('b cannot be zero')\n+    pass\n     return a / b",
    "commit_message": "Remove redundant guard", "pr_description": "Python raises ZeroDivisionError anyway.",
    "file_path": "utils.py", "file_context": "def divide(a, b):\n    return a / b",
    "gold_annotations": [{"line": 5, "type": "bug", "severity": "major", "issue": "Removed explicit guard loses descriptive message. Callers catching ZeroDivisionError expect it; error contract changed.", "reference": ""}]
  },
  {
    "id": "scenario_h_002", "source": {"repo": "encode/httpx", "note": "sanitized — hidden eval set"},
    "difficulty": "easy", "language": "python",
    "diff_text": "--- a/config.py\n+++ b/config.py\n@@ -2,3 +2,3 @@\n DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'\n-DB_PASS = os.environ.get('DB_PASSWORD')\n+DB_PASS = 'super_secret_prod_pass'",
    "commit_message": "Hardcode DB pass for testing", "pr_description": "Temporary for integration tests.",
    "file_path": "config.py", "file_context": "DB_PASS = 'super_secret_prod_pass'",
    "gold_annotations": [{"line": 3, "type": "security", "severity": "critical", "issue": "Database password hardcoded in source. Use environment variable.", "reference": "OWASP A02:2021"}]
  },
  {
    "id": "scenario_h_003", "source": {"repo": "django/django", "note": "sanitized — hidden eval set"},
    "difficulty": "easy", "language": "python",
    "diff_text": "--- a/views.py\n+++ b/views.py\n@@ -5,6 +5,4 @@\n def get_item(request, item_id):\n-    if not request.user.is_authenticated:\n-        return redirect('/login')\n     item = Item.objects.get(id=item_id)\n     return render(request, 'item.html', {'item': item})",
    "commit_message": "Remove auth check — nginx handles it", "pr_description": "Auth enforced at nginx layer.",
    "file_path": "views.py", "file_context": "def get_item(request, item_id):\n    item = Item.objects.get(id=item_id)\n    return render(request, 'item.html', {'item': item})",
    "gold_annotations": [{"line": 7, "type": "security", "severity": "critical", "issue": "Auth check removed — unauthenticated users can access items if nginx bypass exists.", "reference": "OWASP A01:2021"}]
  },
]

# ── HIDDEN MEDIUM (2) ─────────────────────────────────────────────────────────
medium_hidden = [
  {
    "id": "scenario_h_004", "source": {"repo": "celery/celery", "note": "sanitized — hidden eval set"},
    "difficulty": "medium", "language": "python",
    "diff_text": "--- a/tasks.py\n+++ b/tasks.py\n@@ -6,6 +6,6 @@\n @app.task\n def send_email(user_id, template):\n     user = User.objects.get(id=user_id)\n-    body = Template(template).render(user=user)\n+    body = template.format(user=user)\n     mailer.send(user.email, body)",
    "commit_message": "Use .format() instead of Template", "pr_description": "Simpler string formatting.",
    "file_path": "tasks.py", "file_context": "@app.task\ndef send_email(user_id, template):\n    user = User.objects.get(id=user_id)\n    body = template.format(user=user)\n    mailer.send(user.email, body)",
    "gold_annotations": [
      {"line": 9, "type": "security", "severity": "critical", "issue": "str.format() with user-controlled template allows attribute access: {user.__class__.__bases__[0]...}", "reference": "OWASP A03:2021"},
      {"line": 8, "type": "bug", "severity": "minor", "issue": "No error handling if user_id not found — DoesNotExist crashes the task.", "reference": ""}
    ]
  },
  {
    "id": "scenario_h_005", "source": {"repo": "sqlalchemy/sqlalchemy", "note": "sanitized — hidden eval set"},
    "difficulty": "medium", "language": "python",
    "diff_text": "--- a/models.py\n+++ b/models.py\n@@ -12,6 +12,4 @@\n class Order(Base):\n     total = Column(Float)\n-    @validates('total')\n-    def validate_total(self, key, value):\n-        assert value >= 0, 'Total must be non-negative'\n-        return value\n",
    "commit_message": "Remove validator — DB constraint handles it", "pr_description": "DB has CHECK constraint.",
    "file_path": "models.py", "file_context": "class Order(Base):\n    total = Column(Float)",
    "gold_annotations": [{"line": 15, "type": "bug", "severity": "major", "issue": "App-level validation removed. DB constraint raises cryptic IntegrityError instead of clean ValidationError.", "reference": ""}]
  },
]

# ── HIDDEN HARD (2) ───────────────────────────────────────────────────────────
hard_hidden = [
  {
    "id": "scenario_h_006", "source": {"repo": "pallets/flask", "note": "sanitized — hidden eval set"},
    "difficulty": "hard", "language": "python",
    "diff_text": "--- a/app.py\n+++ b/app.py\n@@ -15,6 +15,6 @@\n @app.route('/redirect')\n def do_redirect():\n     url = request.args.get('next', '/')\n-    if not url.startswith('/'):\n-        abort(400)\n+    return redirect(url)",
    "commit_message": "Allow external redirects for OAuth", "pr_description": "OAuth flows need external redirects.",
    "file_path": "app.py", "file_context": "@app.route('/redirect')\ndef do_redirect():\n    url = request.args.get('next', '/')\n    return redirect(url)",
    "gold_annotations": [{"line": 18, "type": "security", "severity": "critical", "issue": "Open redirect: user-controlled URL used without validation. Phishing via trusted domain.", "reference": "OWASP A01:2021"}]
  },
  {
    "id": "scenario_h_007", "source": {"repo": "encode/starlette", "note": "sanitized — hidden eval set"},
    "difficulty": "hard", "language": "python",
    "diff_text": "--- a/middleware/csrf.py\n+++ b/middleware/csrf.py\n@@ -8,7 +8,5 @@\n class CSRFMiddleware:\n     async def __call__(self, scope, receive, send):\n         if scope['type'] == 'http':\n-            token = scope['headers'].get(b'x-csrf-token')\n-            if not token or token != self.secret:\n-                raise HTTPException(status_code=403)\n         await self.app(scope, receive, send)",
    "commit_message": "Remove CSRF check — using SameSite cookies now", "pr_description": "SameSite=Strict makes CSRF tokens redundant.",
    "file_path": "middleware/csrf.py", "file_context": "class CSRFMiddleware:\n    async def __call__(self, scope, receive, send):\n        if scope['type'] == 'http':\n            pass\n        await self.app(scope, receive, send)",
    "gold_annotations": [
      {"line": 12, "type": "security", "severity": "critical", "issue": "CSRF protection removed. SameSite=Strict alone is insufficient (browser support varies, subdomains not covered).", "reference": "OWASP A01:2021"},
      {"line": 12, "type": "bug", "severity": "major", "issue": "Middleware now does nothing but pass through — dead code. Remove entirely or fix.", "reference": ""}
    ]
  },
]

BASE = os.path.join(ROOT, "data", "scenarios")
for i, s in enumerate(easy_public, 1):
    save(os.path.join(BASE, "public", "easy", f"scenario_{i:03d}.json"), s)
for i, s in enumerate(medium_public, 16):
    save(os.path.join(BASE, "public", "medium", f"scenario_{i:03d}.json"), s)
for i, s in enumerate(hard_public, 28):
    save(os.path.join(BASE, "public", "hard", f"scenario_{i:03d}.json"), s)
for i, s in enumerate(easy_hidden, 1):
    save(os.path.join(BASE, "hidden", "easy", f"scenario_h_{i:03d}.json"), s)
for i, s in enumerate(medium_hidden, 1):
    save(os.path.join(BASE, "hidden", "medium", f"scenario_h_{i:03d}.json"), s)
for i, s in enumerate(hard_hidden, 1):
    save(os.path.join(BASE, "hidden", "hard", f"scenario_h_{i:03d}.json"), s)

print(f"✓ Easy public: {len(easy_public)}")
print(f"✓ Medium public: {len(medium_public)}")
print(f"✓ Hard public: {len(hard_public)}")
print(f"✓ Easy hidden: {len(easy_hidden)}")
print(f"✓ Medium hidden: {len(medium_hidden)}")
print(f"✓ Hard hidden: {len(hard_hidden)}")
print(f"✓ Total: {len(easy_public)+len(medium_public)+len(hard_public)+len(easy_hidden)+len(medium_hidden)+len(hard_hidden)} scenarios written")
