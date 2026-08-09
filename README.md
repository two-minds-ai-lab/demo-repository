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
Model chooses one or both tools
    |
    +--> get_bill_due_dates
    |        |
    |        +--> bills.json --> deterministic Python calculations
    |
    +--> get_bill_change_analysis
             |
             +--> bills.json --> deterministic Python calculations
    |
    v
Tool results return to the model as JSON
    |
    v
Model either requests another tool or writes the final answer
```

The model decides which tools to call and how to explain the result. Python
remains responsible for all bill dates, totals, and anomaly calculations.
For local Phi-4 Mini, the adapter accepts both native tool calls and the
model's JSON-text tool-call format. If Phi-4 omits tool metadata, the adapter
runs both read-only bill tools. Phi-4 uses the deterministic Python formatter
for the final response so a small local model cannot alter dates or totals.

## Partner engineering guidance for local Phi-4

The local Phi-4 integration exposed several differences between advertised
tool support and reliable application behavior. Keep these lessons in mind
when adding another local model or tool-calling workflow.

### Pitfalls observed

**OpenAI compatibility did not guarantee OpenAI tool-call semantics.** Ollama's
OpenAI-compatible endpoint accepted the tool schemas, but Phi-4 Mini sometimes
returned the requested calls as JSON inside ordinary assistant text instead of
populating the structured `tool_calls` field. The standard Agents SDK loop
therefore treated the response as a final answer and did not execute the tools.

**Tool selection varied between identical runs.** For the same complete-summary
question, Phi-4 sometimes selected both tools, sometimes selected only the
due-date tool, and sometimes selected no tool. A prompt saying "use both tools"
was helpful but was not a dependable contract.

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
3. Intent coverage ensures a complete summary always runs both bill tools.
4. If Phi-4 omits tool metadata, both read-only tools run as a safe fallback.
5. Python owns loading, date handling, totals, comparisons, and classifications.
6. Phi-4 tool results use deterministic formatting instead of model rewriting.
7. Tests assert known dates, totals, tool coverage, and provider configuration.

The read-only fallback is safe for this project because neither tool changes
state. Do not automatically execute missing or ambiguous tool calls for tools
that send email, update bills, move money, delete data, or perform any other
write. Those tools require explicit structured selection, validation, and
usually user confirmation.

### Guidance for the next integration

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
- chooses the due-date tool, comparison tool, or both;
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
