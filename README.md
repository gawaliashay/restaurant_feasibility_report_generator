# Restaurant Feasibility Report

A founder putting money into a site needs a **local** answer: this cuisine, this neighbourhood, this budget — not a national “F&B is growing” essay.

This project writes one **report** (Markdown and JSON) for that decision: demand, competitors, access, who lives nearby, licenses, risks, and a **GO / CONDITIONAL GO / NO GO** with next steps.

---

## The real problem

Opening a restaurant is a capital decision made **before** the first cover. The expensive mistakes are usually not recipes. They are:

- Choosing a **format the neighbourhood will not support** (wrong prices, wrong hours, wrong cuisine for who actually lives and works there).
- Underestimating **who already owns the street** — nearby kitchens, prices, and whether they are established enough to matter.
- Signing a lease on a **site customers cannot reach easily** (access, landmarks, traffic) and discovering **licenses and operating rules** only after rent starts.
- Paying for a consultant deck that takes weeks, or asking a chatbot that has **no Maps listings, no Trends data, and no FSSAI / Shops Act text**.

City blogs and “food industry TAM” slides do not tell an owner whether **this** corner can carry **this** concept. What they need is a **report they can read and act on**.

---

## The solution

The output is a **single feasibility report** (`reports/report_*.md`), not a chat window.

You set concept, neighbourhood, city, and investment. The document answers, in order:

1. Is there demand for this format here, and is interest stable?
2. Who competes nearby, at what prices and ratings?
3. Is the locality workable as a site (reach, anchors, friction)?
4. Who lives and works nearby, and what does that imply for menu and hours?
5. What must the owner obtain and obey (licenses, hours, penalties)?
6. What can go wrong, with evidence?
7. Positioning, first actions, and a **GO / CONDITIONAL GO / NO GO**.

**What real data the owner gets, and why it helps**

| In the report | Real data | Why it helps the owner |
|---------------|-----------|------------------------|
| Market | Search + Google Trends for this cuisine / this city | See if interest is real and steady, not a national “F&B is growing” claim |
| Competitors | Google Maps: nearby kitchens, ratings, review counts, prices | See who already owns the street before you copy a menu or a ticket |
| Location | Maps + local search: access, landmarks, traffic | Check whether customers can actually reach the site |
| Demographics | Local population and spend signals from web sources | Match hours and menu to who lives and works nearby |
| Compliance | Official FSSAI / shops text from the RAG store | Know licenses, hours, and penalties before rent starts |
| Risk + strategy | Built from the sections above | Plain list of what can fail, then GO / CONDITIONAL GO / NO GO |

Change concept or location and run again. Same report shape — for example a Baner momo report and a Kothrud Italian report — without rewriting the product.

How the graphs, tools, and RAG are wired: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

---

## How it is built

Evidence first, then writing, then a document. RAG is **one tool** (compliance retrieve), not the whole product.

**1. Research (no chat LLM).** Five sections in parallel: market, competitive, location, demographics, compliance. Tools and queries live in `configs.yaml`. Tavily, Google Maps, Google Trends, and RAG return raw results, then `EvidenceItem` records (source, title, content, Maps rating/reviews), deduped and capped.

**2. Report (chat LLM per section).** A LangGraph DAG writes Markdown from Insights only. Market through compliance can run together. **Risk** waits on those drafts. **Strategy** waits on risk. Risk and strategy do not re-query Maps.

**3. Compile (no LLM).** Stack successful sections in YAML order, executive summary from first paragraphs, conclusion from the strategy verdict and first actions. Export: `reports/report_*.md` and `.json`.

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

No CLI flags on the product run. `pipeline` is research → report → compile → save.

| Command | What it does |
|---------|----------------|
| `python -m src.pipeline_runners.pipeline` | Full run. Writes `reports/report_*.md` and `.json` (does not save research JSON) |
| `python -m src.pipeline_runners.research_pipeline_runner` | Research graph only. Writes `reports/processed_evidence/research_results_*.json` |
| `python -m src.pipeline_runners.report_pipeline_runner` | Report + compile from the **newest** saved research JSON. Writes `reports/report_*.md` and `.json` |

RAG ingest is not a pipeline stage: `python -m src.rag.ingest_all` fills Qdrant. Retrieve runs inside research (compliance).

Throughput: `resource_limits.mode` (`fast` / `balanced` / `quality`).

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
│   ├── pipeline_runners/              # how you start a run
│   │   ├── pipeline.py                 # full run: research → report → compile → save json/md
│   │   ├── research_pipeline_runner.py # research only: save evidence JSON
│   │   └── report_pipeline_runner.py   # report + compile from saved research JSON
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
└── reports/                           # report_*.md/.json and processed_evidence/
```

---

Third-party APIs and source documents remain subject to their own terms.