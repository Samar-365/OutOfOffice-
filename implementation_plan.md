# OutOfOffice AI — Detailed Implementation Plan
**Project:** Local-First Autonomous AI Coding Agent  
**Hackathon:** Hacktoberfest Open-Source AI Challenge: Week 1 ("Touch Grass")  
**Target Date:** October 5 – October 11, 2026  
**Document Version:** 1.0  

---

## Architecture Overview

```
OutofOffice AI Architecture
├── Frontend (React 18 + Vite + TypeScript + TailwindCSS)
│   ├── Mission Control (Repo Selection, Task Config, Mode Switcher)
│   ├── Agent Trace Visualizer (Sentry Waterfall Spans & Logs)
│   └── Results Hub (ElevenLabs Audio Player, Health Score, Diff Viewer)
│
├── Backend (FastAPI + Python 3.11+ + SQLite + Async Workers)
│   ├── REST API & WebSocket Real-time Stream
│   ├── Job Manager & Durable State Re-hydration
│   ├── LangGraph Cyclic Reasoning Engine
│   └── Tool Harness (Git, AST, Pytest/Jest, Ripgrep, Sentry, ElevenLabs)
│
└── Local AI Core (Ollama + Google Gemma 2 / CodeGemma)
    ├── 100% Offline Local Model Inference
    ├── Structured JSON Action Schema Enforcement
    └── Zero Cloud Leakage / Total Code Privacy
```

---

## Module 1: Core Architecture & Backend Foundation

### 1.1 Config & Environment Management
* **File:** `backend/app/core/config.py`
* **Responsibilities:**
  * Parse `.env` settings using Pydantic `BaseSettings`.
  * Manage configurations for Ollama API URL (`http://localhost:11434`), default model (`gemma2:9b` / `gemma2:2b`), Sentry DSN, and ElevenLabs API key.
  * Define sandbox constraints (allowed path roots, execution timeouts, max file sizes).
* **Inputs/Outputs:** App settings singleton consumed across all backend packages.

### 1.2 Database Engine & Schema Definition
* **Files:** `backend/app/core/database.py`, `backend/app/core/models.py`
* **Responsibilities:**
  * Configure SQLite database engine with async SQLAlchemy or a clean synchronous SQLite session factory with WAL (Write-Ahead Logging) mode.
  * Define core tables:
    * `jobs`: `id`, `repo_path`, `task_prompt`, `mode` (`AUDIT` | `FIX`), `status` (`QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`), `health_score`, `branch_name`, `created_at`, `finished_at`, `away_duration_seconds`.
    * `job_steps`: `id`, `job_id`, `step_index`, `step_name`, `status`, `tool_name`, `stdout`, `latency_ms`, `created_at`.
    * `findings`: `id`, `job_id`, `severity` (`HIGH`, `MEDIUM`, `LOW`), `category` (`DEAD_CODE`, `TEST_FAILURE`, `LINT`, `TYPE_ERROR`), `file_path`, `line_number`, `description`, `evidence`, `confidence`.
    * `code_diffs`: `id`, `job_id`, `file_path`, `original_content`, `patched_content`, `diff_unified`, `status` (`APPLIED`, `ROLLED_BACK`).
    * `audio_briefings`: `id`, `job_id`, `audio_path`, `script_text`, `duration_seconds`.
* **Inputs/Outputs:** Persistent database schema supporting full reload and recovery.

### 1.3 State & Event Bus / WebSockets
* **File:** `backend/app/core/events.py`
* **Responsibilities:**
  * Implement an in-memory Pub/Sub event broadcaster for active jobs.
  * Emit standardized event payloads: `STEP_STARTED`, `STEP_COMPLETED`, `FINDING_DETECTED`, `DIFF_PRODUCED`, `JOB_COMPLETED`, `JOB_FAILED`.
  * Connect WebSocket route `/ws/jobs/{job_id}` to broadcast real-time telemetry to connected frontends.
* **Inputs/Outputs:** Real-time stream enabling zero-lag UI updates without long polling.

### 1.4 API Server & Route Management
* **Files:** `backend/app/main.py`, `backend/app/api/routes_jobs.py`, `backend/app/api/routes_repo.py`
* **Responsibilities:**
  * FastAPI application setup with CORS middleware (allowing local Vite dev server `http://localhost:5173`).
  * Endpoints:
    * `POST /api/repo/validate`: Checks directory existence, Git status, and project metadata.
    * `POST /api/jobs`: Creates and kicks off a new background task.
    * `GET /api/jobs/{job_id}`: Retrieves complete job state and results.
    * `GET /api/jobs/{job_id}/diff`: Returns unified Git diffs.
    * `GET /api/jobs/{job_id}/audio`: Streams or serves generated ElevenLabs audio briefing.
    * `POST /api/jobs/{job_id}/merge`: Merges the agent branch into the working branch.
    * `POST /api/jobs/{job_id}/cancel`: Safely cancels running job and rolls back uncommitted changes.

---

## Module 2: Local AI Inference & Prompt Engineering (Gemma / Ollama)

### 2.1 Ollama Client & Model Adapter
* **File:** `backend/app/integrations/ollama_client.py`
* **Responsibilities:**
  * Wrap `ollama-python` / HTTP client for local communication with the Ollama daemon.
  * Check model availability (`gemma2:9b`, `gemma2:2b`, `codegemma`, `qwen2.5-coder`) and pull automatically if missing.
  * Manage request timeouts, streaming token callbacks, and token count calculations.
* **Inputs/Outputs:** High-speed, local LLM generation interface.

### 2.2 Structured Output Parser & Schema Enforcer
* **File:** `backend/app/agent/schemas.py`
* **Responsibilities:**
  * Define strict Pydantic schemas for LLM outputs:
    * `PlanOutput`: Array of sequential action items with tool names and arguments.
    * `InvestigationOutput`: Root cause analysis, affected files, confidence score, and suggested remediation.
    * `PatchOutput`: Target file path, original block, replacement block, explanation.
    * `ReportOutput`: Health score (0–100), key accomplishments, and voice brief script.
  * Implement retry/repair logic if local model returns malformed JSON.
* **Inputs/Outputs:** Guaranteed schema compliance from local open-weight models.

### 2.3 Prompt Matrix & System Directives
* **File:** `backend/app/agent/prompts.py`
* **Responsibilities:**
  * Tailor system prompts specifically for Google Gemma 2 / CodeGemma capabilities.
  * Enforce truthfulness: Differentiate clearly between hard deterministic findings (e.g. failing test exit code) and probabilistic observations (e.g. possible dead code).
  * Enforce safety constraints: Forbid deletion of config files, editing outside the repo root, and destructive Git commands.
* **Inputs/Outputs:** Formatted prompt templates for Planning, Execution, Investigation, and Report synthesis.

---

## Module 3: Codebase Intelligence & Discovery Engine

### 3.1 Repository Validator & Metadata Extractor
* **File:** `backend/app/tools/repo_discovery.py`
* **Responsibilities:**
  * Validate path permissions, verify `.git` repository presence.
  * Detect language ecosystems: TypeScript/JavaScript (`package.json`), Python (`pyproject.toml`, `setup.py`, `requirements.txt`), Rust (`Cargo.toml`), Go (`go.mod`).
  * Index all source files while honoring `.gitignore` patterns.
* **Inputs/Outputs:** `RepoMetadata` object containing file count, languages, test framework, and Git status.

### 3.2 Tree-Sitter AST & Symbol Parser
* **File:** `backend/app/tools/ast_parser.py`
* **Responsibilities:**
  * Parse source files into ASTs using `tree-sitter`.
  * Extract top-level symbols: functions, classes, exports, interfaces, imports.
  * Build a symbol table mapping exported functions/types across the codebase.
* **Inputs/Outputs:** Symbol map used for dead code detection and refactoring targets.

### 3.3 Reference Finder & Ripgrep Searcher
* **File:** `backend/app/tools/search_engine.py`
* **Responsibilities:**
  * Integrate `ripgrep` (via subprocess) for sub-millisecond regex and literal searches across large codebases.
  * Check cross-file references for exported functions/classes to verify unused code candidates.
  * Return matching line numbers, snippets, and match counts.
* **Inputs/Outputs:** Accurate reference count for any requested symbol.

### 3.4 Dependency & Manifest Inspector
* **File:** `backend/app/tools/dependency_auditor.py`
* **Responsibilities:**
  * Parse dependency declarations (`dependencies`, `devDependencies`, `install_requires`).
  * Cross-reference declared packages against actual `import` / `require` statements across the codebase to spot unused dependencies.
* **Inputs/Outputs:** List of unused or suspicious dependency findings.

---

## Module 4: Deterministic Tool Harness & Safety Sandbox

### 4.1 Git Branch & Diff Manager
* **File:** `backend/app/tools/git_manager.py`
* **Responsibilities:**
  * Query Git state (`git status`, `git branch --show-current`, `git rev-parse HEAD`).
  * In **Fix Mode**: Create dedicated branch `agent/outofoffice-<timestamp>` to isolate changes.
  * Generate unified diffs comparing modified branch to original base branch.
  * Provide rollback function to restore workspace cleanly if tests fail or if user cancels.
  * Ensure `git push` is never called.
* **Inputs/Outputs:** Isolated Git branch and clean unified diff string.

### 4.2 Test Framework Runner & Parser
* **File:** `backend/app/tools/test_runner.py`
* **Responsibilities:**
  * Detect test commands (`npm test`, `npx vitest run`, `npx jest`, `pytest`, `cargo test`).
  * Run test suite in sandboxed subprocess with execution timeout (e.g. 60s max).
  * Parse test output into structured metrics: total tests, passed, failed, skipped, error messages, and failing stack traces.
* **Inputs/Outputs:** `TestResult` object with pass/fail counts and raw output snippets.

### 4.3 Static Analysis & Linter Runner
* **File:** `backend/app/tools/linter_runner.py`
* **Responsibilities:**
  * Detect and execute available linters / type checkers (`npm run lint`, `npx tsc --noEmit`, `flake8`, `mypy`, `ruff`).
  * Parse linter output into structured findings with exact file paths and line numbers.
* **Inputs/Outputs:** Structured lint and type error findings.

### 4.4 Surgical File Patcher & Rollback Engine
* **File:** `backend/app/tools/patcher.py`
* **Responsibilities:**
  * Apply targeted, line-bounded code edits without corrupting entire files.
  * Verify file syntax after applying modifications.
  * Create in-memory backups before writing to disk to allow instant rollback if compilation/tests fail.
* **Inputs/Outputs:** Verified disk modifications with change logs.

---

## Module 5: LangGraph Autonomous Agent Engine

### 5.1 Agent State & Context Definition
* **File:** `backend/app/agent/state.py`
* **Responsibilities:**
  * Define `AgentState` TypedDict:
    * `job_id`: string
    * `repo_path`: string
    * `task_prompt`: string
    * `mode`: string (`AUDIT` | `FIX`)
    * `plan`: list of planned steps
    * `current_step_idx`: int
    * `repo_meta`: dictionary
    * `test_results`: dictionary
    * `findings`: list of Finding objects
    * `diffs`: list of Diff objects
    * `errors`: list of encountered errors
    * `health_score`: int
    * `voice_script`: string
* **Inputs/Outputs:** Unified state flowing across all graph nodes.

### 5.2 Planning & Task Decomposition Node
* **File:** `backend/app/agent/nodes/planner.py`
* **Responsibilities:**
  * Inspect `task_prompt` + `repo_meta` and query Gemma 2 to construct an execution plan.
  * Generates 5–10 ordered steps (e.g., Discovery $\rightarrow$ Run Tests $\rightarrow$ AST Dead Code Scan $\rightarrow$ Linter $\rightarrow$ Investigate Failures $\rightarrow$ Patch Safe Issues $\rightarrow$ Re-test $\rightarrow$ Report).
* **Inputs/Outputs:** Populates `plan` in `AgentState`.

### 5.3 Tool Execution & Feedback Node
* **File:** `backend/app/agent/nodes/executor.py`
* **Responsibilities:**
  * Execute the current planned step by routing to the appropriate tool (`test_runner`, `ast_parser`, `search_engine`, `linter_runner`).
  * Capture execution output, duration, and exit status.
  * Record step execution in SQLite `job_steps`.
* **Inputs/Outputs:** Updated state with tool execution evidence.

### 5.4 Root-Cause Investigation Loop Node
* **File:** `backend/app/agent/nodes/investigator.py`
* **Responsibilities:**
  * Triggered when a test failure, lint violation, or dead code candidate is detected.
  * Feeds the stack trace, relevant source file lines, and caller references to Gemma.
  * Decides whether the issue is safe to fix automatically or should be marked as an audit finding.
* **Inputs/Outputs:** Appends structured `Finding` objects to `AgentState`.

### 5.5 Fix & Validation Cycle Node
* **File:** `backend/app/agent/nodes/fixer.py`
* **Responsibilities:**
  * In **Fix Mode**: Generates surgical patches for confirmed safe issues.
  * Applies patch using `patcher.py`.
  * Immediately triggers `test_runner.py` to validate that the fix resolved the problem without introducing regressions.
  * If tests fail, automatically rolls back the patch and logs the attempt.
* **Inputs/Outputs:** Updated `code_diffs` and validation test status.

### 5.6 Report Synthesis & Health Scoring Node
* **File:** `backend/app/agent/nodes/reporter.py`
* **Responsibilities:**
  * Calculate Repository Health Score (0–100) based on pass rate, dead code ratio, and lint issues.
  * Synthesize an executive report summarizing files checked, issues discovered, and fixes applied.
  * Generate a natural-language script for the ElevenLabs audio briefing.
* **Inputs/Outputs:** Final report markdown and audio script string.

### 5.7 Graph Compilation & State Transitions
* **File:** `backend/app/agent/graph.py`
* **Responsibilities:**
  * Assemble LangGraph `StateGraph` connecting:
    `Planner` $\rightarrow$ `Executor` $\leftrightarrow$ `Investigator` $\rightarrow$ `Fixer` $\rightarrow$ `Validator` $\rightarrow$ `Reporter` $\rightarrow$ `END`.
  * Compile the runnable graph with checkpointers for state recovery.
* **Inputs/Outputs:** Executable LangGraph workflow instance.

---

## Module 6: Background Worker, Headless Persistence & Durability

### 6.1 Asynchronous Job Orchestrator
* **File:** `backend/app/services/job_runner.py`
* **Responsibilities:**
  * Launch LangGraph execution in an independent background worker thread/task (using `asyncio.create_task` or a dedicated background process).
  * Ensure the agent runs completely decoupled from HTTP request lifecycles.
* **Inputs/Outputs:** Thread-safe job execution manager.

### 6.2 SQLite Persistence & Re-hydration Engine
* **File:** `backend/app/services/persistence.py`
* **Responsibilities:**
  * Commit every step, log line, finding, and diff to SQLite immediately as they occur.
  * Provide `rehydrate_job(job_id)` method: when a developer reopens the web browser, this loads the complete historical timeline and current execution status.
* **Inputs/Outputs:** Zero state loss upon browser close or refresh.

### 6.3 "Touch Grass" Away-Time Tracker
* **File:** `backend/app/services/timer_service.py`
* **Responsibilities:**
  * Track exact start timestamp when the user clicks *"Go Touch Grass"*.
  * Calculate total elapsed time upon job completion.
  * Log total "Grass Touched" minutes (e.g. *"38 minutes away from keyboard"*).
* **Inputs/Outputs:** Human-readable away time metric displayed on the results hub.

---

## Module 7: Partner Integrations (Observability & Voice)

### 7.1 Sentry Agent Tracing & Telemetry Spans
* **File:** `backend/app/integrations/sentry_telemetry.py`
* **Responsibilities:**
  * Initialize Sentry SDK with custom agent tracing.
  * Wrap LangGraph node executions and tool invocations with Sentry spans (`ai.agent`, `ai.tool.call`, `ai.model.inference`).
  * Capture latency waterfalls, tokens generated, model temperature, and error exceptions.
* **Inputs/Outputs:** Rich Sentry traces ready for inclusion in DEV.to submission screenshots.

### 7.2 ElevenLabs Voice Debrief Generator
* **File:** `backend/app/integrations/elevenlabs_brief.py`
* **Responsibilities:**
  * Convert the final voice script generated by `reporter.py` into natural speech via ElevenLabs API (using a warm, friendly voice).
  * Example script: *"Welcome back! While you were outside touching grass for 28 minutes, OutOfOffice AI analyzed 114 files, resolved 2 failing tests, and verified your build is green."*
  * Save the generated `.mp3` into the artifacts/audio directory.
* **Inputs/Outputs:** High-quality voice audio file ready for instant playback in the UI.

### 7.3 Local Audio Fallback
* **File:** `backend/app/integrations/audio_streamer.py`
* **Responsibilities:**
  * If no ElevenLabs API key is supplied, fall back gracefully to a built-in browser Web Speech API synthesis or local offline TTS (`pyttsx3`) so the audio feature works 100% out of the box.
* **Inputs/Outputs:** Reliable audio debrief regardless of cloud credentials.

---

## Module 8: React + Vite Frontend Application

### 8.1 Design System & Theme Engine
* **Files:** `frontend/src/index.css`, `frontend/tailwind.config.js`
* **Responsibilities:**
  * Rich, modern UI with deep forest-green accents, sleek dark glassmorphism, vibrant badges, and Lucide icons.
  * Custom animations (glowing pulse on "Touch Grass" button, soothing nature breeze wave on away screen).

### 8.2 State Store & API/WebSocket Client
* **Files:** `frontend/src/services/api.ts`, `frontend/src/services/websocket.ts`
* **Responsibilities:**
  * Manage REST queries for repository validation and job creation.
  * Establish WebSocket listener on `/ws/jobs/{id}` that updates local UI state as steps arrive.
  * Re-connect automatically on page reload.

### 8.3 Screen 1: Mission Control Dashboard
* **File:** `frontend/src/views/Dashboard.tsx`
* **Responsibilities:**
  * Repository Path Input with instant auto-validation and branch display.
  * Task Prompt Input with one-click presets (*"Find Dead Code & Prune"*, *"Fix Failing Tests"*, *"Full Repository Audit"*).
  * Mode Switcher: **Audit Mode** (Safe, Read-Only) vs **Fix Mode** (Isolated Branch Fixes).
  * Hero Call-to-Action: **`[ Launch Task & View Telemetry ]`** button.

### 8.4 Screen 2: Live Agent Trace & Telemetry Visualizer
* **File:** `frontend/src/views/TraceView.tsx`
* **Responsibilities:**
  * Chronological execution timeline showing each completed step, tool invoked, and latency.
  * Expandable raw stdout/stderr terminal log drawers.
  * Sentry trace waterfall preview and filter queries.

### 8.5 Screen 3: Results Hub, Unified Diff Viewer & Audio Player
* **File:** `frontend/src/views/ResultsHub.tsx`
* **Responsibilities:**
  * **ElevenLabs Welcome-Back Audio Player**: Visual audio player with playback controls.
  * **Repository Health Score Card**: Numerical score meter (e.g. `92/100`).
  * **Test Verification**: Pass/Fail summary with test suite proof on isolated branch.
  * **Interactive Unified Diff Viewer**: Syntax-highlighted unified diffs on `agent/outofoffice-*`.
  * **Action Bar**: `[ Merge Branch ]`, `[ Discard Branch ]`, and `[ Copy DEV.to Summary ]`.

---

## Module 9: Verification, Demo & DEV.to Submission

### 9.1 End-to-End Test Verification
* **Tasks:**
  * Create mock/sample repositories (one TypeScript project with unused exports, one Python project with a failing test).
  * Execute complete OutOfOffice AI runs on both repositories.
  * Verify tests pass after fixes are applied.

### 9.2 Headless Recovery Verification
* **Tasks:**
  * Launch a job on a repository.
  * Hard-refresh / close browser window.
  * Re-open window 2 minutes later and confirm UI seamlessly re-hydrates to the active/completed state with all logs intact.

### 9.3 Demo Walkthrough Assets
* **Tasks:**
  * Record short, high-impact video demonstration demonstrating the core flow: Launch $\rightarrow$ Screen Close $\rightarrow$ Outside $\rightarrow$ Return $\rightarrow$ Audio Briefing & Verified Diff.

### 9.4 DEV.to Submission Post Generation
* **File:** `SUBMISSION_DRAFT.md`
* **Tasks:**
  * Format post following the official DEV Challenge Week 1 template.
  * Include tags `#devchallenge`, `#hf26challenge`.
  * Highlight the Gemma 2 local inference, Sentry tracing, and ElevenLabs voice debrief.

---

## Summary of File Deliverables

```
outofoffice/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes_jobs.py
│   │   │   └── routes_repo.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── models.py
│   │   │   └── events.py
│   │   ├── agent/
│   │   │   ├── state.py
│   │   │   ├── schemas.py
│   │   │   ├── prompts.py
│   │   │   └── nodes/
│   │   │       ├── planner.py
│   │   │       ├── executor.py
│   │   │       ├── investigator.py
│   │   │       ├── fixer.py
│   │   │       └── reporter.py
│   │   ├── tools/
│   │   │   ├── repo_discovery.py
│   │   │   ├── ast_parser.py
│   │   │   ├── search_engine.py
│   │   │   ├── dependency_auditor.py
│   │   │   ├── git_manager.py
│   │   │   ├── test_runner.py
│   │   │   ├── linter_runner.py
│   │   │   └── patcher.py
│   │   ├── integrations/
│   │   │   ├── ollama_client.py
│   │   │   ├── sentry_telemetry.py
│   │   │   ├── elevenlabs_brief.py
│   │   │   └── audio_streamer.py
│   │   ├── services/
│   │   │   ├── job_runner.py
│   │   │   ├── persistence.py
│   │   │   └── timer_service.py
│   │   └── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.tsx
│   │   │   ├── TouchGrassTimer.tsx
│   │   │   ├── DiffViewer.tsx
│   │   │   ├── TraceWaterfall.tsx
│   │   │   ├── VoiceBriefPlayer.tsx
│   │   │   └── FindingsTable.tsx
│   │   ├── views/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── AwayScreen.tsx
│   │   │   ├── TraceView.tsx
│   │   │   └── ResultsHub.tsx
│   │   ├── services/
│   │   │   ├── api.ts
│   │   │   └── websocket.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
├── srs.txt
└── implementation_plan.md
```
