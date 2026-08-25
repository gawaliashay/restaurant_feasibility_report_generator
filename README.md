# Restaurant Market Feasibility Pipeline

An evidence-first LangGraph system that produces a restaurant feasibility report (Markdown and JSON) for a given concept, location, and investment.

Research gathers facts from external tools with **no LLM**. An LLM then writes each report section from that evidence. A compiler assembles the document **without a further model call**.

---

## Problem

Opening a restaurant is a capital decision. A founder needs a local picture: whether demand exists for this cuisine, who already operates nearby, how the site is reached, who lives in the catchment, which licenses apply, and what can go wrong — tied to a specific neighbourhood and budget.

A single chat-model answer cannot supply that. It has no Maps pins, no Trends series, and no copy of the FSSAI or Shops Act. It also tends to blend national anecdotes with local advice. Generic web search without structure dumps links instead of a sectioned brief a lender or partner can read.

The job is therefore: **collect locality-specific evidence first, then write a structured feasibility report from that evidence only.**

---

## Solution

This project is a two-phase pipeline.

**Collect.** Independent research sections run in parallel. Tavily, Google Maps, Google Trends, and a compliance RAG tool return facts. Results are normalized into `EvidenceItem` records (source, title, content, Maps extras such as rating and review count). Failed tools are recorded; remaining evidence still proceeds.

**Write, then assemble.** A second graph asks the LLM to draft one section at a time from those Insights. Risk and strategy run after the evidence sections, using the drafts rather than raw APIs. A compiler with no LLM concatenates YAML-ordered sections, builds an executive summary, and copies the GO / CONDITIONAL GO / NO GO verdict and next steps from strategy.

RAG holds a **compliance corpus** (local PDF, fetched website, remote PDF) so licenses and hours come from ingested law and guidance. Live market and competitor data stay on search and Maps so the vector store is not used as a general web index.

The operator changes concept and location in `configs.yaml` and reruns. Output is Markdown plus JSON under `reports/`.

---

## How it works

```
Input (concept, location, investment)
        │
        ▼
   Research graph          parallel sections · tools only · no LLM
   Tavily · Maps · Trends · RAG
        │
        ▼
   Report graph            LLM per section · DAG (risk and strategy last)
        │
        ▼
   Compiler                no LLM · Markdown + JSON
```

| Stage | Model | What happens |
|--------|--------|----------------|
| Research | None | YAML-defined sections run in parallel. Tools return raw results. Evidence is normalized, deduplicated, and capped. |
| Report | Chat LLM (default: OpenAI `gpt-4o-mini`) | Each section is prompted from Insights. Risk and strategy read the other section drafts. |
| Compile | None | Sections are stacked in YAML order. The executive summary and conclusion are derived from those drafts. |

LangGraph state is a `TypedDict` with reducers. Pydantic models (`EvidenceItem`, `ResearchSectionResult`, `ReportSectionResult`) validate data at node boundaries.

---

## Report contents

Configured in `src/configuration/configs.yaml` under `report.sections`:

| Section | Evidence |
|---------|----------|
| Market analysis | Trends + web search |
| Competitive analysis | Google Maps + web search |
| Location analysis | Maps + web search |
| Customer demographics | Web search |
| Compliance | RAG (ingested legal corpus) |
| Risk assessment | Prior section reports |
| Strategic recommendations | Prior sections, including risk |

Set concept and location in `business_case.default`. Query templates interpolate `{restaurant_concept}`, `{local_area}`, `{city}`, and related fields.

Competitor tables use Google Maps ratings and review counts (rows with 20 or more Maps reviews). Citations appear inline on each section.

---

## Tools

YAML names the tools; `src/common/tools/tool_registry.py` binds names to functions.

| Name | Provider | Used for |
|------|----------|----------|
| `tavily_search` | Tavily | Market, location, and demographic web results |
| `google_maps` | SerpAPI (Google Local) | Competitors and nearby anchors |
| `google_trends` | SerpAPI | Interest over time |
| `rag` | Qdrant | Licenses, operating rules, penalties |

### Compliance corpus

`src/rag/ingest_all.py` loads `rag_sources` from config:

- Local PDFs (for example a restaurant legal handbook)
- Web pages (for example Maharashtra Shops and Establishments)
- Remote PDFs (for example the FSSAI Act)

Documents are parsed, chunked, embedded, and stored in Qdrant (`restaurant_compliance-rag`). At query time the RAG tool **retrieves** only (`top_k`, score threshold, per-chunk length).

---

## Quick start

**Python 3.13+.** Keys: OpenAI (or another LLM in `defaults.analysis_llm`), Tavily, SerpAPI, Qdrant. LangSmith and Groq are optional.

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env`:

```env
OPENAI_API_KEY=
TAVILY_API_KEY=
SERPAPI_API_KEY=
SERPAPI_ENDPOINT=https://serpapi.com/search
SERPAPI_TIMEOUT=30
QDRANT_URL=
QDRANT_API_KEY=
```

Keep `.env` out of version control.

**1. Ingest the compliance corpus** (once per environment):

```bash
python -m src.rag.ingest_all
```

**2. Run the pipeline** from the project root:

```bash
python -m src.pipeline_runners.pipeline
```

| Flag | Effect |
|------|--------|
| *(none)* | Research, report, compile, export |
| `--research-file PATH` | Reuse saved research JSON, then report |
| `--latest-research` | Reuse the newest file under `reports/processed_evidence/` |

Outputs: `reports/report_YYYYMMDD_HHMMSS.md` and `.json`.

Throughput is controlled by `resource_limits.mode` (`fast`, `balanced`, `quality`).

**Tests**

```bash
pytest tests/ -q
```

**HTTP API** (same workflows as the CLI):

```bash
python -m app.run_api
```

OpenAPI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

---

## Project structure

```
app/                          FastAPI entry
src/
  configuration/              configs.yaml, prompts.yaml, loaders
  common/
    schemas.py                Pydantic contracts
    tools/                    registry, clients, evidence processor
    model_loader.py
  workflow/
    research/                 parallel evidence graph
    report/                   DAG, compiler, exporter
  rag/                        ingest, parse, retrieve
  graph_states/               WorkflowState
  pipeline_runners/           CLI
tests/
reports/                      generated reports
```

Prompt keys in `prompts.yaml` match `report.sections.*.prompt` in `configs.yaml`.

---

## Configuration

| File | Role |
|------|------|
| `src/configuration/configs.yaml` | Business case, tools and queries, models, RAG sources, limits |
| `src/configuration/prompts.yaml` | Section-writing instructions |
| `.env` | API keys and SerpAPI endpoint |

---

## Engineering

- **Separation of concerns.** Research never calls a chat model. The compiler never calls a chat model. The LLM writes sections only.
- **Config-driven tools.** Adding a tool is a YAML name plus a registry function, not a graph rewrite.
- **RAG as a tool.** The vector store holds the compliance corpus. Live market and Maps data stay on search APIs.
- **Contracts.** Evidence and section results are validated with Pydantic before they enter LangGraph state.
- **Bounded context.** Evidence is mixed across tools, capped by character limits, and filtered for empty queries and unknown tool names. Failed tool calls are recorded; remaining evidence still reaches the section.
- **Resilient reporting.** LLM calls use retry with backoff. The compiler includes only successful sections and builds the conclusion from the strategy verdict and action plan.

---

Third-party APIs, maps data, and source documents remain subject to their own terms of use.
