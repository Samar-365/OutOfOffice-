---
title: Give your code a job. Go touch grass: OutOfOffice AI 🌳
published: true
tags: devchallenge, hf26challenge, ai, showdev, productivity
cover_image: https://raw.githubusercontent.com/Samar-365/OutOfOffice-/main/docs/assets/banner.png
canonical_url: https://github.com/Samar-365/OutOfOffice-
---

*This is a submission for the [Hacktoberfest 2026: Week 1 AI Challenge](https://dev.to/challenges).*

---

# 🌿 The Dilemma: Watching Spinners vs. Touching Grass

As developers, we spend countless hours waiting for static analyzers to crawl our repos, waiting for test suites to execute, and staring at terminal output while debugging AST imports and dead code.

What if you could give your codebase an autonomous directive, **close your laptop**, step away into the fresh outdoor air for 30 minutes to touch grass, and return to find:
1. All dead code scanned and unreferenced exports pruned.
2. Failing tests investigated in the AST and surgically patched on an isolated Git branch.
3. A warm **ElevenLabs voice debrief** narrating everything that happened while you were outside?

Introducing **OutOfOffice AI** 🌳 — the local-first, autonomous coding agent built for developer work-life harmony.

---

## ⚡ What OutOfOffice AI Does

OutOfOffice AI is an end-to-end autonomous coding agent that runs **100% locally on your machine** using **Google Gemma 2** via Ollama. It decouples the coding agent lifecycle from your web browser so you can safely shut down your tab, close your screen, and step away.

```
       [ Developer clicks "GO TOUCH GRASS" ]
                        │
                        ▼
    ┌────────────────────────────────────────┐
    │     FastAPI Background Job Runner      │
    └───────────────────┬────────────────────┘
                        │ (Spawns independent worker thread)
                        ▼
    ┌────────────────────────────────────────┐
    │     LangGraph Autonomous StateGraph    │
    │  ┌───────────┐         ┌───────────┐   │
    │  │  Planner  │ ──────> │ Executor  │   │
    │  └─────┬─────┘         └─────┬─────┘   │
    │        │                     │         │
    │        ▼                     ▼         │
    │  ┌───────────┐         ┌───────────┐   │
    │  │Investigate│ ──────> │   Fixer   │   │
    │  └───────────┘         └─────┬─────┘   │
    │                              │         │
    │                              ▼         │
    │                        ┌───────────┐   │
    │                        │ Reporter  │   │
    │                        └───────────┘   │
    └───────────────────┬────────────────────┘
                        │
         ┌──────────────┴──────────────┐
         ▼                             ▼
┌──────────────────┐          ┌───────────────────┐
│ Sentry Telemetry │          │ ElevenLabs Voice  │
│  (Custom Spans)  │          │   (Audio Debrief) │
└──────────────────┘          └───────────────────┘
```

---

## 🚀 Key Features

### 1. 🛡️ Deterministic Safety Sandbox
- **Audit Mode**: Comprehensive read-only audit across AST symbols, npm/pip manifests, and linter diagnostics with zero repository mutations.
- **Fix Mode**: Creates an isolated `agent/outofoffice-<timestamp>` Git branch, applies line-bounded AST patches, re-runs test suites, and verifies 100% green status before reporting.

### 2. 🌳 Real-Time "Grass Touched" Away Tracker
- Tracks exact developer screen-freedom duration.
- Awards progressive outdoor milestone tiers:
  - 🌱 **Sprout Explorer** (<5 mins)
  - 🌿 **Meadow Stroller** (5–15 mins)
  - 🌳 **Park Ranger** (15–30 mins)
  - 🏔️ **Mountain Monk** (>30 mins)

### 3. 🎙️ ElevenLabs Voice Debrief
- Upon returning to your desk, OutOfOffice AI synthesizes a personalized audio brief:
  > *"Welcome back! While you were outside touching grass for 28 minutes, OutOfOffice AI analyzed 114 files, resolved 2 failing tests, and verified your build is green."*
- Features local offline Web Speech API synthesis fallback for instant, zero-configuration out-of-the-box operation.

### 4. 📊 Sentry Agent Tracing & Telemetry
- Instruments every LangGraph node execution, tool call (`repo_discovery`, `test_runner`, `patcher`), and LLM inference with dedicated Sentry spans (`ai.agent`, `ai.tool.call`, `ai.model.inference`).
- Visualizes interactive Gantt waterfall profiles in the UI.

### 5. 💾 Zero-Loss SQLite Rehydration
- Every step, terminal log, finding, and diff is committed immediately to SQLite.
- Close your browser, restart your computer, or refresh the page at any time — OutOfOffice AI rehydrates the full historical timeline instantly.

---

## 🛠️ Architecture & Tech Stack

| Layer | Technologies |
|---|---|
| **Local AI Inference** | **Google Gemma 2 (9B / 2B)** via Ollama |
| **Agent Orchestration** | **LangGraph** (StateGraph cyclic planning & tool loop) |
| **Backend Framework** | **Python 3.11 + FastAPI + AnyIO** |
| **Persistence & State** | **SQLite + SQLAlchemy ORM** with Alembic migrations |
| **Observability** | **Sentry Python SDK** (Custom AI agent tracing spans) |
| **Audio & Voice** | **ElevenLabs API** + Local Web Speech API streaming |
| **Frontend UI** | **React 18 + Vite + TypeScript + TailwindCSS** |
| **Icons & Design** | Lucide Icons, Glassmorphism, Neon Forest theme |

---

## 📸 Screen-by-Screen Walkthrough

### 1. Mission Control Dashboard
Configure target local repositories with automatic branch detection, select one-click presets (*"Find Dead Code & Prune"*, *"Fix Failing Tests"*), toggle Audit/Fix mode, and click the pulsing **`[ 🌳 GO TOUCH GRASS ]`** button.

```
+-------------------------------------------------------------------------------+
|  🌳 OutOfOffice AI        [Dashboard]  [Away]  [Trace]  [Results]  (Ollama: gemma2) |
+-------------------------------------------------------------------------------+
|  Target Repo: [ C:\projects\my-app                               ] [Validate] |
|  ✓ Valid Git Repo (main) • 114 files • TypeScript, Python • pytest detected   |
|                                                                               |
|  [ 🧹 Find Dead Code & Prune ]    [ 🧪 Fix Failing Tests ]                     |
|                                                                               |
|  Mode: [ 🛡️ Audit Mode ]  [ ⚡ Fix Mode ]                                       |
|                                                                               |
|                   +---------------------------------------+                   |
|                   |         [ 🌳 GO TOUCH GRASS ]          |                   |
|                   +---------------------------------------+                   |
+-------------------------------------------------------------------------------+
```

---

### 2. Headless Away Screen
A relaxing, minimalist full-screen display with live counting grass timer, nature ambience audio toggle, and reassurance that the local agent is running safely in the background.

```
+-------------------------------------------------------------------------------+
|  🛡️ Local Background Agent Active • Safe to close or lock screen               |
|                                                                               |
|                                     🌳                                        |
|                          Outdoor Level: Park Ranger                           |
|                                                                               |
|                                 00:24:18                                      |
|            "Full deep outdoor immersion. Tests verified green."                |
|                                                                               |
|               [ 2,400 Estimated Steps ]     [ 24 Mins Saved ]                 |
|                                                                               |
|  Status: Agent is running static analysis on AST nodes...                     |
|                                                                               |
|              +-------------------------------------------------+              |
|              |      [ I'm Back! Check Results & Voice Debrief ]|              |
|              +-------------------------------------------------+              |
+-------------------------------------------------------------------------------+
```

---

### 3. Live Agent Telemetry & Sentry Waterfall
Real-time step timeline with expandable stdout/stderr terminal drawers, latency profiling, and Sentry waterfall breakdown.

```
+-------------------------------------------------------------------------------+
|  Latency: 4.82s  |  LLM Inferences: 3 (Gemma 2)  |  Tools: 5  |  Findings: 2  |
+-------------------------------------------------------------------------------+
|  #1 ✓ AST Discovery & File Indexing          repo_discovery             340ms |
|  #2 ✓ Cross-Reference Symbol Search          search_engine              820ms |
|  #3 ✓ Test Suite Execution                   test_runner               1450ms |
|  #4 ✓ Surgical AST Patch Synthesis           patcher                    410ms |
|  #5 ✓ Post-Fix Green Verification            test_runner               1210ms |
+-------------------------------------------------------------------------------+
```

---

### 4. Results Hub & Unified Diff Viewer
Listen to the ElevenLabs voice briefing, review radial health scores (`95/100`), inspect syntax-highlighted unified diffs, and 1-click merge or export DEV.to summaries.

```
+-------------------------------------------------------------------------------+
|  🔊 Welcome-Back Voice Debrief (ElevenLabs)                                   |
|  [▶ Play Debrief]  0:00 ========================= 0:18                        |
|  "Welcome back! While you touched grass for 24 minutes, OutOfOffice AI        |
|   analyzed 114 files, resolved 2 failing tests, and your build is 100% green."|
+-------------------------------------------------------------------------------+
|  [ Health Score: 95/100 ]   [ Tests: 14/14 Green ]   [ Grass: 24 mins away ]  |
+-------------------------------------------------------------------------------+
|  Unified Code Diffs (app/calculator.py):             [ Merge ]  [ Discard ]    |
|  @@ -8,3 +8,3 @@                                                              |
|   def subtract(a: int, b: int) -> int:                                        |
|  -    return a + b                                                            |
|  +    return a - b                                                            |
+-------------------------------------------------------------------------------+
```

---

## 💻 Code Highlight: Sentry Custom Agent Spans

Here is how OutOfOffice AI instruments LangGraph nodes and tool calls using custom Sentry spans:

```python
# backend/app/integrations/sentry_telemetry.py
@asynccontextmanager
async def trace_tool(self, tool_name: str, job_id: str, args: Optional[Dict[str, Any]] = None):
    """Trace an individual tool execution with Sentry and local waterfall ledger."""
    span_id = f"tool-{uuid.uuid4().hex[:8]}"
    start_time = time.perf_counter()
    
    span_record = SpanRecord(
        span_id=span_id,
        job_id=job_id,
        op=f"ai.tool.call.{tool_name}",
        description=f"Tool Invocations: {tool_name}",
        data={"arguments": args or {}},
    )
    self._active_spans[span_id] = span_record

    try:
        if self._is_enabled and sentry_sdk:
            with sentry_sdk.start_span(op="ai.tool.call", description=f"Tool: {tool_name}") as sentry_span:
                sentry_span.set_data("tool.name", tool_name)
                yield sentry_span
        else:
            yield None
        span_record.finish(status="ok")
    except Exception as exc:
        span_record.finish(status="error")
        raise
```

---

## 🧪 Comprehensive Test Verification

OutOfOffice AI is covered by **77 comprehensive tests** spanning unit, integration, and E2E scenarios:

- ✅ **AST & Parser Tests**: Python & TypeScript syntax tree symbol extraction.
- ✅ **Test Runner & Git Sandbox**: Isolated branch creation and rollback.
- ✅ **Sentry & ElevenLabs Integration**: Telemetry waterfall and voice fallback.
- ✅ **Durability & Rehydration**: Zero-loss state recovery after browser disconnection.
- ✅ **Full E2E Scenarios**: Autonomous execution on sample TypeScript & Python repositories.

```bash
# Run the complete test suite
python -m pytest
# ============================= 77 passed in 25.63s =============================
```

---

## 📦 Try It Out Locally

```bash
# 1. Clone the repository
git clone https://github.com/Samar-365/OutOfOffice-.git
cd OutOfOffice-

# 2. Setup and run backend
pip install -r requirements.txt
uvicorn backend.app.main:app --reload

# 3. Setup and run frontend
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`, give your code a job, and **go touch grass!** 🌳

---

## 🌟 Acknowledgements

Built with ❤️ for **Hacktoberfest 2026: Week 1 AI Challenge**. Special thanks to:
- **Google Gemma 2** for local-first structured intelligence
- **LangChain / LangGraph** for stateful cyclic agent orchestration
- **Sentry** for AI agent distributed tracing
- **ElevenLabs** for voice debrief synthesis
