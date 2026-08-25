# Restaurant Market Feasibility Pipeline

An evidence-first LangGraph system that produces a **restaurant feasibility report** (Markdown and JSON) for a given concept, location, and investment.

Someone considering a site needs more than a chat essay. This project **collects local evidence with tools first**, then asks a language model to write each section from that packet, then **assembles the document without a further model call**.

Diagrams of the graphs, `run_tool`, and RAG ingest/retrieve: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

---

## Problem

Opening a restaurant commits capital. A useful brief answers, for **this cuisine in this neighbourhood**:

- Is there demand, and how stable does interest look?
- Who already competes, at what prices and ratings?
- Can customers reach the site (roads, transit, anchors, congestion)?
- Who lives nearby, and what does that imply for hours and menu?
- Which licenses and operating rules apply?
- What are the main risks, and is the recommendation GO, CONDITIONAL GO, or NO GO?

A single LLM call cannot see Google Maps, Trends, or the FSSAI / Shops Act text. A pile of search links is not a lender-ready document. The gap is **local, sourced, sectioned analysis** — not another generic “food industry is growing” paragraph.

---

## Solution

The pipeline is three stages.

**1. Research (no chat LLM).**  
Five sections run in parallel: market, competitive, location, demographics, compliance. Each section’s tools and queries live in `configs.yaml`. Tavily, Google Maps, Google Trends, and a RAG retrieve call return raw results. Those results are normalized into `EvidenceItem` records (source, title, content, Maps rating/reviews when present), deduplicated, and capped so the next stage has a bounded packet.

**2. Report (chat LLM per section).**  
A second LangGraph DAG writes Markdown from Insights only. Market through compliance can run together. **Risk** waits until those drafts exist. **Strategy** waits on risk. Risk and strategy do not re-query Maps; they read the section reports.

**3. Compile (no LLM).**  
The compiler stacks successful sections in YAML order, adds an executive summary from first paragraphs, and copies the strategy verdict and first actions into the conclusion. Export is `reports/report_*.md` and `.json`.

RAG is **one tool**, not the whole product. A compliance corpus (local PDF, fetched website, remote PDF) is ingested into Qdrant. Licenses and hours come from that store. Live market and competitor facts stay on Tavily and Maps.

The operator sets `business_case.default` (concept, area, city, investment) and reruns. The same graphs produced both a Baner momo brief and a Kothrud Italian brief by changing config, not code.

---

## How it works

```
Concept + location + investment
              │
              ▼
     Research graph          parallel · tools only · no chat LLM
     Tavily · Maps · Trends · RAG
              │
              ▼
     Report graph            LLM per section · DAG
     evidence sections → risk → strategy
              │
              ▼
     Compiler                no LLM · Markdown + JSON
```

| Stage | Chat LLM | Responsibility |
|--------|----------|----------------|
| Research | No | Fan-out per YAML section; validate and cap evidence |
| Report | Yes (default OpenAI `gpt-4o-mini`) | One prompt per section; risk/strategy use other drafts |
| Compile | No | Headings, executive summary, GO/NO GO + next steps |

LangGraph state is a `TypedDict` with reducers so parallel nodes merge. Pydantic (`EvidenceItem`, `ResearchSectionResult`, `ReportSectionResult`) validates payloads at node boundaries.

YAML **names** tools; `src/common/tools/tool_registry.py` **maps** names to functions. Adding a source is a config line plus a registry entry, not a graph rewrite.

---

## What the report includes

Configured under `report.sections` in `src/configuration/configs.yaml`.

| Section | Question it answers | Evidence |
|---------|---------------------|----------|
| Market analysis | Is there demand for this format? | Trends + web search |
| Competitive analysis | Who operates nearby, and at what price? | Maps + web search |
| Location analysis | Is the locality workable as a site? | Maps + web search |
| Customer demographics | Who lives here? | Web search |
| Compliance | What must the owner obtain and obey? | RAG corpus |
| Risk assessment | What can go wrong, with evidence? | The five drafts above |
| Strategic recommendations | Positioning, action plan, GO / CONDITIONAL GO / NO GO | Drafts including risk |

Competitor tables use **Google Maps** ratings and review counts (rows with **20 or more** Maps reviews). Citations are inline (`*Sources: …*`). Prompts instruct the model to stay on Insights (no invented market sizes or placeholder `N/A` cells).

---

## Tools

| Name | Provider | Role |
|------|----------|------|
| `tavily_search` | Tavily | Market, location, and demographic web results |
| `google_maps` | SerpAPI (`google_local`) | Competitors and nearby anchors |
| `google_trends` | SerpAPI | Interest over time |
| `rag` | Qdrant retrieve | Licenses, hours, penalties |

Compliance ingest (`python -m src.rag.ingest_all`) loads `rag_sources`: local PDFs, websites, and PDFs fetched by URL. At runtime the RAG tool **retrieves** only (`top_k`, score threshold, chunk length). Execution path: [ARCHITECTURE.md](ARCHITECTURE.md#tool-pipeline) and [RAG pipeline](ARCHITECTURE.md#rag-pipeline).

---

## Quick start

Python **3.13+**. API keys: OpenAI (or switch `defaults.analysis_llm`), Tavily, SerpAPI, Qdrant. LangSmith is optional.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set in `.env`: `OPENAI_API_KEY`, `TAVILY_API_KEY`, `SERPAPI_API_KEY`, `SERPAPI_ENDPOINT`, `SERPAPI_TIMEOUT`, `QDRANT_URL`, `QDRANT_API_KEY`. Do not commit `.env`.

```bash
python -m src.rag.ingest_all
python -m src.pipeline_runners.pipeline
pytest tests/ -q
```

| Flag | Effect |
|------|--------|
| *(none)* | Research, report, compile, export |
| `--research-file PATH` | Reuse saved research JSON, then report |
| `--latest-research` | Newest file under `reports/processed_evidence/` |

Outputs: `reports/report_YYYYMMDD_HHMMSS.md` and `.json`. Throughput: `resource_limits.mode` (`fast` / `balanced` / `quality`).

HTTP API (same workflows): `python -m app.run_api` — [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

---

## Layout

```
.
├── README.md                          # what this project is and how to run it
├── ARCHITECTURE.md                    # graphs, tool pipeline, RAG wiring
├── requirements.txt                   # Python packages
├── pyproject.toml                     # project metadata / uv
├── .env.example                       # copy to .env and fill API keys
├── app/                               # HTTP API (same pipeline as CLI)
│   ├── main.py                        # FastAPI routes
│   ├── run_api.py                     # start the API server
│   └── api_tester.py                  # manual API checks
├── src/                               # pipeline code
│   ├── configuration/                 # YAML the operator edits
│   │   ├── configs.yaml               # concept, location, tools, models, limits
│   │   ├── prompts.yaml               # how each report section is written
│   │   ├── config_loader.py           # loads configs.yaml
│   │   └── prompts_loader.py          # loads prompts.yaml
│   ├── graph_states/                  # TypedDict shared across graphs
│   │   └── workflow_states.py         # shared LangGraph state
│   ├── pipeline_runners/              # CLI entry points
│   │   ├── pipeline.py                # research → report → compile → save
│   │   ├── research_pipeline_runner.py  # research only
│   │   ├── report_pipeline_runner.py    # report from saved research
│   │   └── tool_pipeline_runner.py      # call one tool (debug)
│   ├── workflow/
│   │   ├── research/                  # tools only; no chat LLM
│   │   │   ├── research_workflow.py   # parallel graph, one node per section
│   │   │   └── research_section_runner.py  # run tools → evidence
│   │   └── report/                    # chat LLM, then assemble
│   │       ├── report_workflow.py     # DAG: sections → risk → strategy
│   │       ├── report_section_runner.py  # prompt + LLM → Markdown
│   │       ├── report_compiler.py     # stack sections (no LLM)
│   │       └── report_exporter.py     # write reports/*.md and *.json
│   ├── common/                        # shared types, LLM, tools
│   │   ├── schemas.py                 # Pydantic evidence and section types
│   │   ├── model_loader.py            # chat LLM for the report stage
│   │   └── tools/                     # registry, run_tool, clients
│   │       ├── tool_registry.py       # YAML name → function
│   │       ├── tool_pipeline.py       # run_tool: validate, call, return
│   │       ├── evidence_processor.py  # raw API output → EvidenceItem
│   │       └── clients/               # Tavily, SerpAPI, RAG
│   │           ├── tavily_client.py   # web search
│   │           ├── serpapi_client.py  # Google Maps and Trends
│   │           └── rag_client.py      # RAG retrieve
│   ├── rag/                           # compliance corpus in Qdrant
│   │   ├── ingest_all.py              # load local/remote PDFs and websites
│   │   ├── rag_pipeline.py            # retrieve-only; no chat LLM
│   │   ├── model_schema.py            # chunk and retrieve types
│   │   ├── parser/
│   │   │   └── parser.py              # read PDFs and web pages
│   │   ├── ingestion/
│   │   │   └── ingestion_pipeline.py  # parse → split → embed → store
│   │   ├── vector_store/
│   │   │   └── vector_store.py        # Qdrant write and search
│   │   └── retriever/
│   │       └── retriever.py           # search and truncate chunks
│   ├── logging_exception/
│   │   ├── logging/
│   │   │   └── logger.py              # logging
│   │   └── exception/
│   │       └── custom_exception.py    # app exceptions
│   └── utils/
│       └── create_unique_uuid.py      # IDs for jobs / records
├── tests/                             # unit tests
└── reports/                           # generated Markdown and JSON
```

---

Third-party APIs and source documents remain subject to their own terms.
