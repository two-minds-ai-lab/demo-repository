<p align="center">
  <img src="assets/banner.svg" alt="Two Minds AI Lab — two minds, learning in public." width="100%">
</p>

<p align="center">
  <a href="https://github.com/two-minds-ai-lab/demo-repository/actions/workflows/proof-html.yml"><img src="https://github.com/two-minds-ai-lab/demo-repository/actions/workflows/proof-html.yml/badge.svg" alt="Proof HTML"></a>
  <img src="https://img.shields.io/badge/license-MIT-191c18" alt="MIT licensed">
  <img src="https://img.shields.io/badge/javascript-none-a4560c" alt="No JavaScript">
</p>

# Two Minds AI Lab

One person and one model, working things out together. What we learn goes here as we learn
it — the working-out included, not only the parts that came out clean.

Almost everything written about working with AI arrives as a finished result with the
learning taken out. The result is the least useful part of it. So we keep the rest, and we
publish it as we go.

**→ [two-minds-ai-lab.github.io/demo-repository](https://two-minds-ai-lab.github.io/demo-repository/)**

## Three rules

**Show the working-out.** The notes, the dead ends, and the draft that did not work,
alongside whatever finally did.

**Claim nothing unshipped.** Nothing here describes work that does not exist yet. That is
why this repository is small.

**Correct it in the open.** When we get something wrong, the correction lands here too, and
the history keeps both.

## What's here

| Path | What it is |
| --- | --- |
| `index.html` | The whole page — markup and styles in one file, no script |
| `assets/banner.svg` | The banner above |
| `bill_analysis.py` | Deterministic recurring-bill analysis and report formatting |
| `bill_agent.py` | Bill Manager agent and its two function tools |
| `bill_agent_provider.py` | OpenAI, Azure OpenAI, and local Phi-4 configuration |
| `bill_agent_tools.py` | Adapters from agent tools to deterministic bill calculations |
| `data/bills.json` | Six-bill sample dataset with current and previous statements |
| `tests/` | Baseline pytest coverage for the bill analysis |
| `.github/workflows/` | Checks the rendered HTML, and assigns an owner to new issues |
| `docs/superpowers/specs/` | The design spec, including the direction that was abandoned |

## Run it

No build step, no dependencies. Any static server works:

```bash
git clone https://github.com/two-minds-ai-lab/demo-repository.git
cd demo-repository
python3 -m http.server 8000
```

Then open <http://localhost:8000>.

## Run the bill analysis

The Stage 0 bill analyzer uses only Python's standard library:

```bash
python bill_analysis.py
```

Run its tests with:

```bash
python -m pytest
```

## Run the Bill Manager agent

Install the OpenAI Agents SDK dependency:

```powershell
python -m pip install -r requirements.txt
```

Select a model provider with `BILL_AGENT_PROVIDER`:

| Value | Backend |
| --- | --- |
| `openai` | Public OpenAI API |
| `azure` | Azure OpenAI deployment using Azure credits |
| `phi4` | Local Microsoft Phi-4 model through Ollama |

Example using Azure OpenAI:

```powershell
$env:BILL_AGENT_PROVIDER="azure"
$env:AZURE_OPENAI_API_KEY="your-azure-key"
$env:AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
$env:AZURE_OPENAI_DEPLOYMENT="your-deployment-name"
python bill_agent.py "Give me a complete bill summary."
```

See [`AGENT_SETUP.md`](AGENT_SETUP.md) for every provider option.

## How the agent loop works

`Runner.run_sync()` owns the loop; the application does not need a manual
`while` loop:

```text
User question
    |
    v
Bill Manager receives its instructions and tool schemas
    |
    v
Model chooses one or more tools
    |
    +--> get_bill_due_dates
    |        |
    |        +--> bills.json --> deterministic Python calculations
    |
    +--> get_bill_change_analysis
    |        |
    |        +--> bills.json --> deterministic Python calculations
    |
    +--> search_bill_records
             |
             +--> BM25 + Qwen3 embeddings --> ranked bill evidence
    |
    v
Tool results return to the application
    |
    v
Deterministic validation and formatting
    |
    v
Final answer
```

The model decides which information is needed. Python remains responsible for
retrieval safety, bill dates, totals, anomaly calculations, and factual output.
For local Phi-4 Mini, the adapter accepts both native tool calls and the
model's JSON-text tool-call format. If Phi-4 omits tool metadata, the adapter
uses intent-coverage rules to select the required read-only tools. Phi-4 uses
deterministic Python formatters so a small local model cannot alter retrieved
evidence, dates, or totals.

## Current mental model

```text
User language
     |
     v
Phi-4: understand intent and propose tools
     |
     v
Python intent coverage: enforce required read-only tools
     |
     +--> Due-date tool ------> bills.json ------> date and total logic
     |
     +--> Comparison tool ----> bills.json ------> anomaly logic
     |
     +--> Retrieval tool
             |
             +--> BM25 ----------------> exact words and identifiers
             |
             +--> Qwen3 Embedding -----> meaning and synonyms
                           |
                           v
                 Reciprocal Rank Fusion
     |
     v
Exact-value validation and deterministic formatting
     |
     v
Factual response
```

Responsibilities stay deliberately separate:

| Component | Responsibility |
| --- | --- |
| Phi-4 Mini | Understand the question and suggest tools |
| Python coverage rules | Run required tools and suppress unrelated selections |
| BM25 | Match exact providers, amounts, dates, and identifiers |
| Qwen3 Embedding | Match concepts such as “power bill” and “home internet” |
| Reciprocal Rank Fusion | Combine independent rankings without mixing scores |
| Bill analysis code | Calculate dates, totals, changes, and classifications |
| Deterministic formatter | Produce the final factual response |

## Local Phi-4 lessons

The local Phi-4 integration exposed several differences between advertised
tool support and reliable application behavior.

**Quick takeaway:** use Phi-4 to understand intent, but let Python control which
tools are allowed and how financial facts are rendered.

### Pitfalls observed

**OpenAI compatibility did not guarantee OpenAI tool-call semantics.** Ollama's
OpenAI-compatible endpoint accepted the tool schemas, but Phi-4 Mini sometimes
returned the requested calls as JSON inside ordinary assistant text instead of
populating the structured `tool_calls` field. The standard Agents SDK loop
therefore treated the response as a final answer and did not execute the tools.

**Tool selection varied between identical runs.** For the same question,
Phi-4 sometimes selected every required tool, sometimes selected only one, and
sometimes selected no tool. A prompt saying which tools to use was helpful but
was not a dependable contract.

**Phi-4 sometimes selected too many tools.** For “which bill is power bill,”
the model selected retrieval, due-date, and comparison tools. The facts were
correct, but the answer contained unrelated information. Explicit intent now
defines the allowed tool set, so retrieval-only questions suppress due-date
and comparison tools.

**Correct tool data did not guarantee correct final prose.** When the model was
asked to rewrite authoritative JSON, it invented dates, changed billing
periods, and confused current and previous amounts. This is unacceptable for
financial information even when the underlying calculations are correct.

**The model supplied its own unrelated time context.** Before receiving tool
results, one run claimed the current date was in March even though
`bills.json` specified August 4, 2026. Dates must come from application data,
not model memory or assumptions.

**The local endpoint still required an API-key value.** Ollama does not validate
a cloud key, but the OpenAI client requires a non-empty `api_key` parameter.
The adapter uses the harmless local placeholder `ollama`.

**Model and runtime versions matter.** This project uses `phi4-mini`, not the
larger `phi4`, because Phi-4 Mini has the appropriate Ollama tool-calling
template. Ollama must be running and new enough to support the model.

### Safeguards implemented

1. The provider adapter isolates Phi-4 behavior from OpenAI and Azure OpenAI.
2. The parser accepts native `tool_calls` and JSON-text tool requests.
3. Intent coverage enforces required tools and suppresses unrelated tools.
4. If Phi-4 omits tool metadata, only intent-required read-only tools run.
5. Python owns loading, date handling, totals, comparisons, and classifications.
6. Phi-4 tool results use deterministic formatting instead of model rewriting.
7. Tests assert known dates, totals, tool coverage, and provider configuration.

The read-only fallback is safe for this project because neither tool changes
state. Do not automatically execute missing or ambiguous tool calls for tools
that send email, update bills, move money, delete data, or perform any other
write. Those tools require explicit structured selection, validation, and
usually user confirmation.

### Checklist for future integrations

**Treat prompts as guidance, not enforcement.** Enforce required tool coverage
in code and validate the tool result before using it.

**Keep deterministic work outside the model.** Dates, money, thresholds,
sorting, status transitions, and identifiers belong in typed application code.
Use the model for intent recognition and explanation only where variation is
safe.

**Test the raw provider response first.** Before connecting an agent framework,
send one request directly to the provider with tool schemas and inspect whether
calls appear in `tool_calls`, plain text, or another provider-specific field.

**Test repeated runs, not one successful demo.** Local small models may choose
different tools for identical prompts. Run the same routing test several times
and test partial, missing, malformed, and duplicate calls.

**Define a fallback policy per tool.** Read-only lookup tools may allow a safe,
bounded fallback. Any side-effecting tool should fail closed rather than guess.

**Validate final answers against tool output.** For high-stakes domains,
prefer templates or structured rendering. If model-written prose is required,
add schema validation and fact checks before displaying it.

**Keep provider configuration explicit.** Pin dependency versions, document the
model name and endpoint, and provide a health check such as:

```powershell
ollama --version
ollama list
Invoke-RestMethod http://localhost:11434/api/tags
```

This design lets the cloud providers use the standard Agents SDK loop while
the local provider applies only the compatibility safeguards it needs.

## Where the agent adds value

The agent is primarily a natural-language router and conversation layer. It:

- understands different ways of asking the same billing question;
- chooses due-date, comparison, retrieval, or combined tool paths;
- supports follow-up questions without requiring command-specific syntax;
- combines multiple tool results into one user-facing response; and
- provides a path for adding Gmail ingestion, reminders, updates, and other
  tools without building a separate command for every request.

The agent is deliberately not the source of truth. Deterministic Python owns:

- reading `bills.json`;
- date-window and payment-status logic;
- money calculations;
- monthly comparisons and anomaly thresholds; and
- reliable formatting where model rewriting could alter facts.

For the current small set of fixed questions, an agent is optional. A normal
CLI with explicit commands could produce the same calculations more cheaply
and predictably. The agent becomes worthwhile when users ask varied questions,
need conversational follow-ups, or when the system has enough tools that
intent-based routing is simpler than exposing every operation directly.

The design rule is:

> The model decides what information is needed; deterministic code decides
> what is true.

## Semantic-search experiment

The project uses `qwen3-embedding:4b` as its free local embedding model:

```powershell
ollama pull qwen3-embedding:4b
python bill_embeddings.py "Find my power bill"
```

`bill_embeddings.py` converts each structured bill into searchable text,
generates 2,560-dimensional vectors through Ollama, and ranks bills using
cosine similarity. Phi-4 remains responsible for language and routing;
Qwen3 Embedding is responsible only for semantic similarity.

The embedding CLI remains useful for isolated evaluation. Production agent
search uses it only through hybrid retrieval, alongside the BM25 baseline.

### BM25 and hybrid retrieval

`bill_retrieval.py` provides three comparable modes:

```powershell
python bill_retrieval.py --mode bm25 "Chase Visa"
python bill_retrieval.py --mode semantic "Find my power bill"
python bill_retrieval.py --mode hybrid "Find my power bill"
```

BM25 runs through an in-memory SQLite FTS5 index and handles exact names,
amounts, dates, and identifiers. Semantic retrieval handles synonyms and
natural-language descriptions. Hybrid retrieval combines their ranked lists
with Reciprocal Rank Fusion rather than mixing incompatible raw score scales.

Amounts such as `142.40` and ISO dates such as `2026-08-10` are handled as
exact structured filters before token search. This prevents the FTS tokenizer
from splitting a decimal into broad matches such as `142` and `40`. Hybrid
search also fails closed for an unmatched exact amount or date instead of
returning a semantically similar but financially incorrect result.

Hybrid retrieval is exposed to the Bill Manager as the read-only
`search_bill_records` tool. Phi-4 routing enforces this tool for find, search,
source, exact amount, and exact date questions. The retrieval layer still
fails closed when an exact financial value has no match.

### Retrieval pitfalls and improvements

| Pitfall observed | Improvement made |
| --- | --- |
| BM25 misses synonyms such as “power bill” for PSE Electricity | Added Qwen3 semantic embeddings |
| Embeddings may weaken exact names, amounts, or dates | Kept BM25 and structured exact filters |
| BM25 and cosine scores use unrelated scales | Combined ranks with Reciprocal Rank Fusion |
| SQLite split `142.40` into `142` and `40` | Detect amounts before tokenization and match exact decimals |
| Semantic search could return a close result for a nonexistent amount | Hybrid search fails closed for unmatched exact values |
| Phi-4 may omit or partially select retrieval tools | Added deterministic intent-coverage rules |
| Phi-4 may select unrelated extra tools | Explicit intent defines and limits the allowed tool set |
| Follow-up tools returned facts for every bill instead of the retrieved match | Compound questions join due/change details to retrieval rank 1 |
| Phi-4 may rewrite correct evidence incorrectly | Added deterministic retrieval formatting |
| One successful query can hide unstable ranking | Added regression tests and `OBSERVATIONS.md` evidence |

### Improvements still needed

- Replace the six synthetic search documents with representative bill emails
  and statements.
- Add a fixed query-evaluation set with Recall@3, MRR, latency, and failure
  categories.
- Persist the FTS and vector indexes when the document collection grows.
- Add source IDs and citations before retrieving Gmail messages.
- Define explicit approval boundaries before introducing any write-capable
  email, reminder, or bill-update tool.

The current implementation proves the routing and ranking architecture. It
does not yet prove retrieval quality over a realistic bill-document corpus.

### Cross-tool joins

A multi-tool answer is not correct merely because each individual tool is
correct. Tool results must be connected to the same entity.

The issue appeared with this question:

```text
Which bill is the power bill, and how much is due only for rank 1?
```

Before the fix:

```text
Retrieval tool → PSE Electricity ranked first
Due-date tool  → Chase, PSE, and Citi
Final answer   → all three due bills and the $507.90 total
```

The due-date output was valid by itself, but it did not answer the follow-up
about the retrieved bill.

The fixed flow is:

```text
Hybrid retrieval
    ↓
Rank 1 bill_id: pse_electricity
    ↓
Join calculated details by bill_id
    ├─ Amount due: $142.50
    ├─ Due date: 2026-08-09
    └─ Change: +$47.50 (+50.0%)
    ↓
Targeted deterministic response
```

Cross-tool join rules:

1. Use stable IDs such as `bill_id`; never join on generated names or prose.
2. Treat retrieval rank as selection only when the question requests it.
3. Apply due-date or comparison details only to the selected IDs.
4. If retrieval has no match, do not expose unrelated tool results.
5. Keep formatting deterministic after the join.
6. Add regression tests for wrong names, no matches, and extra tool data.

## Notes on the build

Kept here because they are part of the working-out.

**The page is a sheet with a margin.** One rule runs its whole length. The text sits to the
right of it and the annotations hang to the left, the way notes get added to a page after
it was written. Two hands annotate — a person and a model — and each keeps its own colour.

**The drafts stay on the page.** What the site used to say is struck through rather than
deleted, with the reason kept beside it. Those are this page's real revisions, not
illustrations of the idea. It is the first rule applied to the page itself.

**No JavaScript.** An earlier version needed a script for a pointer-tracked effect in the
hero. A document does not need one, so there isn't one.

**One file, no build step.** GitHub Pages serves these files as they are, so `index.html`
inlines its own styles and makes zero external requests. A bundler or a CDN would not
survive the trip.

**System typefaces only.** A serif for reading and a monospace for the margin. No webfonts
means no network round-trip and no layout shift.

**What degrades.** Below 900px the margin cannot hold a column, so annotations drop in
beneath what they annotate and keep their coloured edge on the left.

## License

[MIT](LICENSE) © Two Minds AI Lab
