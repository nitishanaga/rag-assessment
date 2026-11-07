# Agentic RAG Lesson Generator: A 3-Node Architecture

An autonomous, self-healing AI pipeline designed to generate, strictly evaluate, and dynamically optimize educational content about Retrieval-Augmented Generation (RAG). 

Unlike standard linear LLM scripts, this system utilizes a **Decoupled Agentic Architecture** (Generator, Evaluator, and Optimizer) combined with **Persistent Self-Pruning Memory** to iteratively improve its own outputs until they pass a strict, zero-partial-credit JSON rubric.

---

## 🏗️ System Architecture & Data Flow

```text
[Run Initiated] 
       │
       ▼
 ┌──────────────┐      ┌───────────────┐      ┌───────────────┐
 │ Node 1:      │◄─────┤ Node 3:       │◄─────┤ Node 2:       │
 │ Prompt       │      │ Strict JSON   │      │ Content       │
 │ Optimizer    │      │ Evaluator     │      │ Generator     │
 └──────┬───────┘      └───────┬───────┘      └───────▲───────┘
        │                      │                      │
        │ (New Prompt)         ├─ [ALL is True] ──────┤ (Generates Lesson)
        ▼                      │                      │
 [Update State]                ├─ [ANY is False] ─────┘
        │                      ▼
        │             [Stores Distilled Lesson in state/memory.json]
        └─────────────[Logs Updated Prompts in logs/run_log.txt]
```

### The 3-Node Design
1. **The Generator Node:** A standard completion agent designed as a "dumb" actor. It focuses purely on content generation following its active instructions.
2. **The Evaluator Node:** Implements the **LLM-as-a-Judge** pattern. To prevent "partial credit", the evaluator is constrained to output a strict JSON schema. It evaluates the text across **6 independent checkpoints** (`accurate`, `beginner_friendly`, `has_example`, `no_jargon`, `covers_key_points`, `good_flow`). 
3. **The Prompt Optimizer Node:** Ingests the JSON failure reasons, reads distilled lessons from persistent memory, and dynamically rewrites the base instructions for the Generator's next attempt.

---

## 🧠 Engineering Trade-offs & Design Choices

### 1. Strict Boolean JSON Validation
Early iterations relied on parsing text strings, which is brittle. The Evaluator is now forced via API constraints to return a pure JSON object with explicit boolean flags. The Python execution loop implements strict type-checking (`if value is True:`) to guarantee that malformed string responses (like `"false"`) immediately fail the validation gate.

### 2. Distilled, Self-Pruning Memory (`state/memory.json`)
If an agentic system appends raw JSON feedback to a memory file indefinitely, it creates prompt bloat and context exhaustion. To solve this, the Evaluator generates a `"distilled_lesson"` (e.g., *"Rule: Always explicitly mention the augmentation step."*). The system acts as a FIFO buffer, retaining only the 5 most recent *distilled rules*, not raw logs.

### 3. Log Transparency (`logs/run_log.txt`)
When the Optimizer rewrites a prompt, the system logs the *exact new prompt* to `logs/run_log.txt`. This creates an auditable trace showing how the instructions change after a failure.

### 4. Handling the Nuance of RAG Accuracy
Instructing an AI to ensure a RAG lesson is "100% accurate" is technically flawed. The Evaluator explicitly enforces that the generated lesson correctly sequences RAG (Encoding -> Retrieval -> Augmentation -> Generation) and forbids claiming RAG is perfectly reliable, ensuring high technical fidelity.

---

## ⚙️ Setup & Installation

**Prerequisites:** Python 3.8+

1. **Clone the repository:**
   ```bash
   git clone https://github.com/nitishanaga/rag-assessment
   cd rag-assessment
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Create a `.env` file in the project root and add your Groq API key:
   ```env
   GROQ_API_KEY=your_api_key_here
   ```

---

## 🚀 Execution Modes

### Mode 1: Normal Production Run
Attempts to generate a passing lesson on Attempt 1 using optimized default instructions.
```bash
python agent.py
```

### Mode 2: Demonstration Run (Self-Healing Loop)
Intentionally injects a bad prompt (commanding jargon-heavy academic output) to trigger the Evaluator's failure state, update memory, and showcase the Optimizer rewriting the prompt. The loop can use up to two retries.
```bash
python agent.py --demo
```

Generated files are stored relative to the project folder, even when the script is launched from another working directory.

## 📂 Project Structure

* `agent.py`: Generator, evaluator, prompt optimizer, and bounded retry loop.
* `requirements.txt`: Python dependencies.
* `output/final_lesson.txt`: Lesson accepted by the evaluator in the latest successful run.
* `logs/run_log.txt`: Latest run's prompts, rubric results, and outcome.
* `state/memory.json`: Persistent store of recent distilled feedback.
* `.env`: Local API key configuration; excluded from Git.
* `.gitignore`: Excludes secrets, virtual environments, and Python cache files.