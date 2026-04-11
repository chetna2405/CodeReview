# Project Report: CodeReviewEnv Benchmark System
**Team:** Refreshment Hunters
**Event:** Meta x PyTorch Hackathon (Scaler School of Technology)

## 1. Executive Summary
This project delivers a multi-turn, Reinforcement-Learning-ready evaluation benchmark for Large Language Models acting as autonomous AI code reviewers. Agents are challenged to review Pull Request diffs, identify hidden bugs, classify severity, and debate with a simulated author persona. The system is fully compliant with the OpenEnv specification and evaluates LLMs holistically on security, logic, code style, and cross-file inferences.

## 2. Technical Architecture & Stack Decisions

Our technology stack was meticulously chosen to prioritize **performance, asynchronous concurrency, and a premium "tactical" UI/UX**, bypassing older technologies in favor of modern, lightning-fast ecosystems.

### 2.1 Backend Services
**Chosen: FastAPI + Python 3.11**
*   **Why we used it:** FastAPI provides massive asynchronous performance advantages (via ASGI) compared to traditional synchronous frameworks. By leveraging Python's `async/await` syntax, our backend effortlessly handles upstream LLM proxy network calls (which are highly latent) without blocking the main event thread. Additionally, tight integration with Pydantic ensures bulletproof data validation for our specific OpenEnv state and step models.
*   **Why we rejected alternatives (Flask / Django):** Flask operates on WSGI (synchronous by default), making network-heavy LLM chaining very slow and prone to bottlenecks. Django was discarded as its massive ORM and templating overhead was overkill for a lightweight benchmark server.

**Chosen: SQLite3**
*   **Why we used it:** We employ SQLite (in WAL mode) for the leaderboard database. SQLite is a zero-configuration, filesystem-local database. This perfectly satisfies the ephemeral container deployment model of Hugging Face Spaces without complicating the submission architecture. 
*   **Why we rejected alternatives (PostgreSQL / MongoDB):** Setting up a remote cloud database cluster would introduce unnecessary external network latency and structural complexity requiring managed external services that exceeded the hackathon bounds.

### 2.2 Frontend & UI Presentation
**Chosen: React.js (via Vite) + Tailwind CSS v4**
*   **Why we used it:** React provides an un-opinionated, component-driven architecture allowing us to rapidly iterate on complex dashboard widgets (Leaderboards, Radar charts, live streams). We utilized **Vite** as our bundler—bypassing the sluggishness of Webpack-based `create-react-app`—to achieve instant Hot Module Reloading (HMR) and optimized build assets. **Tailwind CSS** fueled our styling engine, letting us execute a premium, dark-mode, glassmorphism "tactical" aesthetic entirely through utility classes, eliminating the context-switching of traditional CSS files.
*   **Why we rejected alternatives (Angular / Vue.js, Material-UI):** Angular is incredibly verbose for a single-page dashboard. We rejected heavy component libraries like Material-UI because they enforce rigid, generic "Google-style" aesthetics, whereas we wanted a custom, enterprise-grade, high-fidelity experience built from scratch.

**Chosen: Framer Motion & Recharts**
*   **Why we used them:** To elevate the "wow" factor, **Framer Motion** was integrated for declarative, physics-based micro-animations (e.g., dashboard card mount staggering and layout morphs). **Recharts** was selected over imperative charting libraries (like Chart.js) because it integrates seamlessly into the React render lifecycle and allows deep SVG customization.
*   **Why we rejected alternatives (D3.js):** Raw D3 has too steep of a learning curve for rapid hackathon iteration, and Chart.js lacks the flexible composability required for our specific dashboard gradients and Tooltip interceptors.

### 2.3 Deployment & DevOps
**Chosen: Docker (Multi-Stage Build) on Hugging Face Spaces**
*   **Why we used it:** We isolated both the React frontend and FastAPI backend into a single `Dockerfile` utilizing a **multi-stage build**. Stage 1 (`node:20`) securely compiles the frontend into static assets, passing them onto Stage 2 (`python:3.11-slim`), where FastAPI serves both the API routes and the SPAs HTML via static mounting. This guarantees identical execution locally and on Hugging Face Spaces.
*   **Why we rejected alternatives (Vercel + Heroku dual deployment):** Splitting the frontend (Vercel) and backend required configuring complex CORS policies and maintaining two repos. Hugging Face Spaces provided a centralized, GPU/CPU-bound environment perfect for AI environments natively built in a singular Docker container.

## 3. Key Technical Implementations
1.  **Phase 2 LiteLLM Proxy Compliance:** Successfully instrumented the `inference.py` runtime script to fall back dynamically between `HF_TOKEN` and the mandated `API_KEY` injections. This bypassed fatal Phase 2 Deep Validation checks and routed traffic smoothly to the proxy infrastructure.
2.  **Stateless Ephemeral Caching Solutions:** Enforced `Cache-Control: no-cache` directives directly in the web server layer to counteract HTTP subresource 404 cache desyncs caused by SPAs requesting outdated asset cryptographic hashes following Docker redeployments.
3.  **Strict Semantic Logging Pipelines:** Engineered robust `stdout` logs mimicking the hackathons precise regex evaluators (`[START]`, `[STEP]`, `[END]`) utilizing floating-point standardizations (e.g., `score={score:.3f}`).

## 4. Conclusion
"Refreshment Hunters" successfully hybridized an enterprise-grade SaaS ops frontend with a highly-rigorous LLM-benchmarking backend, conforming accurately to all pre-submission validation safeguards set out by Meta and Scaler.
