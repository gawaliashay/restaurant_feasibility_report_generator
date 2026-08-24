This is a **small, interview-sized cleanup**, not a rewrite. The architecture is already the right story. We only fix places that are hard to defend, or that currently contradict “config-driven / validated / grounded.”

Out of scope on purpose: rerankers, HyDE, eval harness, checkpoints, HITL, Redis, converting all of `WorkflowState` to Pydantic, `with_structured_output` that changes the report into JSON.

---

## 1. Problems in the pipeline

**P1. Report nodes do not actually use section config**  
`run()` already has the section dict, but `_build_prompt()` ignores it. Cross-section vs evidence-section is hardcoded prompt names. Evidence lookup reverse-finds `research_section` by prompt name, so a rename in YAML can silently break a section.

**P2. Node inputs/outputs are untyped dicts**  
Research returns `{"status", "evidence"}`. Report returns `{"status", "report"}`. Nothing validates shape. That is the gap vs “I use Pydantic.” LangGraph state can stay a `TypedDict`; validation belongs at node boundaries.

**P3. Evidence ranking is duplicated and non-standard**  
Dedupe / bubble-sort / char-limit live in `ResearchSectionRunner`. Sort is copied again in `ReportSectionRunner`. Bubble sort is a classic generated-code tell in interviews.

**P4. Tool failures disappear**  
Failed Tavily/Maps/RAG calls are logged and `continue`. `state.errors` exists (`operator.add`) but is never written. The LLM then writes “Data Limitations” from imagination, not from real failures.

**P5. Grounding is prompt-only**  
Prompts say “use only evidence / cite sources.” The system never attaches the source list it actually retrieved. Interviewers will ask: “How do you know the model didn’t invent a license or a competitor?”

**P6. Compiler uses fragile text heuristics**  
`report_compiler.py` matches phrases like `"the google trends data"` and `"notable competitors"` to build an executive summary. That is not explainable as design.

**P7. Dead config and leftover noise**  
`evaluation.*` points at modules that do not exist. `workflow.approval_mode: manual` has no human node. `final_compilation` is disabled, but the runner still special-cases it. RAG truncates in both `Retriever` and `RAGPipeline`. Tools use a different logger than the rest of `src/`. YAML still has `# ← Add this` comments.

**P8. The repo is hard to walk in 2 minutes**  
`README.md` is empty. Interviewers often start there.

---

## 2. Solution for each problem

| Problem | Solution | Interview one-liner |
|---|---|---|
| P1 | Pass the section config into prompt building. `research_section is None` means cross-section. Use YAML mapping, not prompt-name string replace. | “The graph topology and evidence routing both come from YAML.” |
| P2 | Add 3 small Pydantic models. Validate, then `model_dump()` into LangGraph state. | “TypedDict for reducers; Pydantic at node boundaries.” |
| P3 | Move sort / dedupe / limit onto `EvidenceProcessor`. Use `sorted()`. | “Evidence hygiene is one module, used by research and report.” |
| P4 | Collect failed tools into `errors` and merge into state. Pass a short limitations string into the prompt. | “Partial failure is data, not a crash.” |
| P5 | System-attach `sources` from the evidence we sent. Soft-check the LLM `*Sources:*` line. Do not fail the section. | “Citations are produced by the pipeline, then the model is checked against them.” |
| P6 | Compiler only stacks successful sections + header. First paragraph for summary, no phrase lists. | “Compilation is deterministic. No extra LLM, no NLP heuristics.” |
| P7 | Delete dead YAML. Truncate RAG in one place. Use the project logger in `tool_pipeline`. Remove the `final_compilation` special case from the runner (pipeline already compiles). | “Config that isn’t wired is worse than missing config.” |
| P8 | Short README: problem, two-phase flow, how to run, what RAG is for. | You can draw the diagram from the README. |

---

## 3. Code changes (purpose only — no extra machinery)

### New file: `src/common/schemas.py`

**Purpose:** One place for pipeline contracts. Keep RAG dataclasses in `src/rag/model_schema.py` (retrieval layer). This file is for research/report payloads.

```python
class EvidenceItem(BaseModel):
    tool: str
    query: str
    source: str = ""
    title: str = ""
    url: str = ""
    content: str
    extra: dict[str, Any] = {}

class ResearchSectionResult(BaseModel):
    section: str
    status: Literal["success", "failed", "skipped"]
    evidence: list[EvidenceItem] = []
    sources: list[str] = []
    errors: list[dict[str, Any]] = []
    error: str | None = None

class ReportSectionResult(BaseModel):
    section: str
    status: Literal["success", "failed", "skipped"]
    report: str = ""
    sources: list[str] = []
    error: str | None = None
```

Do **not** turn `WorkflowState` into a Pydantic model. LangGraph reducers (`operator.or_`, `operator.add`) stay on the TypedDict.

---

### `src/common/tools/evidence_processor.py`

**Purpose:** Evidence hygiene in one class.

Add:

- After building each dict, `EvidenceItem.model_validate(...).model_dump()` so bad tool payloads fail clearly.
- `dedupe(evidence)` — unique `source + title` (same rule as today).
- `sort_by_score(evidence)` — `sorted(..., key=score, reverse=True)`, items without score last.
- `limit_by_chars(evidence, max_chars)` — move existing logic here.
- `collect_sources(evidence)` — unique `source` or `tool`, skip empties.

Do **not** add scoring models, embeddings, or a new `evidence_service.py`.

---

### `src/workflow/research/research_section_runner.py`

**Purpose:** This node only orchestrates tools. It does not rank evidence itself.

- On tool failure: append `{"section", "tool", "query", "error"}` to a local `errors` list. Do not crash.
- After tools: `dedupe → sort_by_score → limit_by_chars`.
- Return `ResearchSectionResult(...).model_dump()` including `sources` and `errors`.

Delete `_remove_duplicates`, `_sort_by_score`, `_limit_evidence_by_chars` from this file.

---

### `src/workflow/research/research_workflow.py`

**Purpose:** Failed tools must reach `state.errors` (the reducer already supports this).

Node return becomes:

```python
return {
    "research_results": {section_name: result},
    "errors": result.get("errors", []),
}
```

No other graph changes. Do not add checkpoints or a supervisor node.

---

### `src/workflow/report/report_section_runner.py`

**Purpose:** Config drives routing; LLM only writes prose; sources are system-owned.

- Change `_build_prompt(prompt_name, state)` → `_build_prompt(section_name, section, state)`.
- If `section.get("research_section") is None`: cross-section (use other reports). Else: load that research bucket.
- Use `EvidenceProcessor.sort_by_score`, drop local bubble sort.
- After LLM text: `sources = collect_sources(evidence_used)`.
- Soft check: if the report contains `*Sources: ...*`, log sources that were not in `evidence_used`. Still return success.
- Return `ReportSectionResult(...).model_dump()`.
- Delete `_sort_by_score`.
- Delete the `final_compilation` special case. Compilation stays in `pipeline.py` (deterministic, not a graph node).

Keep retry as it is. Keep markdown output. Do not switch to structured JSON reports.

For `_extract_insights`: keep “trim to N chars at a sentence boundary.” That is token control, not NLP.

---

### `src/workflow/report/report_compiler.py`

**Purpose:** Assemble a document. No interpretation.

Keep: header, section stack, risk, recommendations.  
Change: executive summary = first non-heading paragraph of each successful section (or first ~200 chars).  
Delete: `skip_starts`, `"notable competitors"`, `"this trend indicates"` matching.  
Optional: append a `## Sources` block from each section’s `sources` field.

---

### `src/rag/rag_pipeline.py`

**Purpose:** One truncation point.

Remove the chunk-text loop here. `Retriever` already truncates with `max_chars_per_chunk`. `RAGPipeline.retrieve` should only call the retriever and return.

---

### `src/common/tools/tool_pipeline.py`

**Purpose:** One logging style in `src/`.

Replace `logging.getLogger(__name__)` with `from src.logging_exception.logging.logger import logger`. No behavior change.

---

### `src/configuration/configs.yaml`

**Purpose:** YAML must match running code.

Delete:

- entire `evaluation:` block
- `workflow.approval_mode`
- comments like `# ← Add this`

Keep `research_section:` keys — they become the real routing switch.  
Keep `final_compilation.enabled: false` — pipeline compiles after the graph.  
Optional one-line comment under `rag_retrieval.score_threshold`: “LangChain Qdrant cosine similarity; higher is better; we keep score >= threshold.” Verify that once when you run retrieval; do not write a score-adapter class.

---

### `src/graph_states/workflow_states.py`

**Purpose:** Tiny comment only, if needed.

```python
# errors: tool/section failures merged with operator.add
# research_results / section_reports: validated with Pydantic, stored as dicts
```

No new fields unless you add `sources` at state root (you should not — keep sources on each section result).

---

### `README.md`

**Purpose:** 40–60 lines, interview script.

Include: what it does, research vs report vs RAG-as-tool, how to ingest / run research / run full pipeline, that RAG is for compliance docs only. No essay.

---

### Tests (only if they break)

Update mocks to the new result shape (`sources`, `errors`). Add **two** small tests:

- `sort_by_score` orders high score first  
- `EvidenceItem` rejects empty content  

Do not turn `test_pipeline_integration.py` into a live API test.

---

### Explicitly do **not** change

- `tavily_client.py` / `serpapi_client.py` / `rag_client.py` (clients are fine)
- Vector store / ingestion (no hybrid search)
- FastAPI (`app/main.py`) for this pass
- Merging the three pipeline runners
- `pyproject.toml` unused deps (optional later; not needed to explain the pipeline)
- Logger internals (`inspect.stack` is ugly but not interview-critical)

---

## 4. Step-by-step plan (one file at a time)

Your workspace rule: **one file per step, wait for approval.**

| Step | File | What you should be able to say after it |
|---|---|---|
| 1 | **Create** `src/common/schemas.py` | “These are the contracts between tools, research, and report.” |
| 2 | `src/common/tools/evidence_processor.py` | “Raw tool JSON becomes `EvidenceItem`, then we dedupe, rank, and cap tokens.” |
| 3 | `src/workflow/research/research_section_runner.py` | “This node runs tools and returns validated evidence + errors.” |
| 4 | `src/workflow/research/research_workflow.py` | “Parallel sections merge evidence with `or_` and errors with `add`.” |
| 5 | `src/workflow/report/report_section_runner.py` | “YAML `research_section` chooses evidence vs cross-section. Sources are attached by code.” |
| 6 | `src/workflow/report/report_compiler.py` | “No LLM. Stack sections. Summary is the first paragraph.” |
| 7 | `src/rag/rag_pipeline.py` | “Retrieval-only. Truncation lives in the retriever.” |
| 8 | `src/common/tools/tool_pipeline.py` | “Same logger as the rest of the app.” |
| 9 | `src/configuration/configs.yaml` | “If it isn’t used, it isn’t in the file.” |
| 10 | `src/graph_states/workflow_states.py` | Comment only, if still useful. |
| 11 | `README.md` | Walk the system from the README in 2 minutes. |
| 12 | Tests **only if step 2–5 break them** | Contracts have tests; we didn’t pad coverage. |

After step 5 the pipeline is already more explainable. Steps 6–11 are cleanup so the story stays consistent.

---

## How you will explain the finished design

Draw this, nothing more:

```
Input (restaurant + location)
        │
        ▼
Research graph (parallel, no LLM)
  tools → EvidenceItem → dedupe/sort/limit
  failures → state.errors
        │
        ▼
Report graph (LLM)
  research_section set  → that evidence
  research_section null → other section reports
  system attaches sources
        │
        ▼
Compiler (no LLM) → markdown/json
```

If they ask “why not structured output for the whole report?”: “The deliverable is a narrative memo. I validate the **payloads** (evidence, status, sources), not the prose. That’s the 80/20 for this product.”

---

I’m in **Ask mode**, so I cannot apply these edits. When you switch to Agent mode, say **“start at step 1”** and we’ll do `src/common/schemas.py` only, then stop.