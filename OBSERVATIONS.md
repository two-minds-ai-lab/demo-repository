# Bill Manager test observations

Use this file as the single place to record testing before adding the next
feature.

## Quick status

- Current decision: `NOT TESTED`
- Tested by:
- Date:
- Branch or commit:
- Provider: `phi4`
- Model: `phi4-mini`
- Embedding model: `qwen3-embedding:4b`

Decision values:

- `GO` - ready for the next stage
- `FIX` - issue found; do not continue
- `NOT TESTED` - testing is incomplete

## Five-minute check

Run these commands in PowerShell:

```powershell
cd C:\twominds
ollama --version
ollama list
python -m pytest -q
python bill_embeddings.py "Find my power bill"
$env:BILL_AGENT_PROVIDER="phi4"
python bill_agent.py "Give me a complete bill summary."
```

Check the output:

- [ ] Ollama is running.
- [ ] `phi4-mini` is installed.
- [ ] `qwen3-embedding:4b` is installed.
- [ ] All tests pass.
- [ ] “Find my power bill” ranks PSE Electricity first.
- [ ] BM25 ranks “Chase Visa” and “142.50” correctly.
- [ ] Hybrid search ranks semantic synonyms correctly.
- [ ] Unmatched exact amounts return no results instead of partial matches.
- [ ] As-of date is August 4, 2026.
- [ ] Due within seven days is $507.90.
- [ ] Current-month total is $762.90.
- [ ] No dates or bill names were invented.

## Test checklist

### Data and calculations

- [ ] Exactly six bills load from `data/bills.json`.
- [ ] Paid bills are excluded from upcoming bills.
- [ ] Missing history does not crash the program.
- [ ] Dates are calculated from data, not model assumptions.
- [ ] Totals and percentages match the expected values.

### Agent and tools

- [ ] A due-date question runs `get_bill_due_dates`.
- [ ] A comparison question runs `get_bill_change_analysis`.
- [ ] A complete-summary question runs both tools.
- [ ] A find/search question runs `search_bill_records`.
- [ ] A combined search-and-comparison question runs both required tools.
- [ ] Retrieval-only questions suppress due-date and comparison tools.
- [ ] Follow-up due/change details apply only to retrieval rank 1.
- [ ] Text-based Phi-4 tool requests are recognized.
- [ ] Missing tool metadata triggers only the read-only fallback.
- [ ] The final answer uses deterministic formatting.

### Reliability

- [ ] The complete-summary question was run at least five times.
- [ ] Every run returned the same dates and totals.
- [ ] No run crashed or hung.
- [ ] Fallback behavior was visible and understood.
- [ ] GitHub Actions passed.

### Safety

- [ ] No API key is committed.
- [ ] `.env` and `.venv` are ignored.
- [ ] No tool changes data or sends messages.
- [ ] Future write tools will fail closed and require confirmation.

## Repeat-run evidence

Run this five times:

```powershell
1..5 | ForEach-Object {
    Write-Output "`n--- RUN $_ ---"
    python bill_agent.py "Give me a complete bill summary."
}
```

Record only differences:

- Run 1:
- Run 2:
- Run 3:
- Run 4:
- Run 5:

If there were no differences, write: `All five runs matched.`

## Observation log

Copy this block for each test session:

```text
### YYYY-MM-DD - Short test name

Status: PASS / FAIL / BLOCKED
Provider and model:
Command:

Expected:

Observed:

Evidence:
- Test output:
- Tool calls:
- Final totals:
- Screenshot or Actions link:

Fallback triggered: YES / NO
Issue or risk:
Next action:
Owner:
```

## Current session

### 2026-08-08 - Qwen3 embedding smoke test

Status: PASS
Provider and model: Ollama / qwen3-embedding:4b
Command: `python bill_embeddings.py "<query>"`

Expected:

- “Find my power bill” ranks PSE Electricity first.
- “Find my phone service” ranks T-Mobile first.
- “Find my home internet bill” ranks Xfinity Broadband first.

Observed:

- PSE Electricity ranked first with score `0.7223`.
- T-Mobile ranked first with score `0.5804`.
- Xfinity Broadband ranked first with score `0.6360`.

Evidence:
- Test output: 26 tests passed.
- Vector dimensions: 2,560.
- Tool calls: Not applicable; standalone retrieval experiment.
- Final totals: Not applicable.
- Screenshot or Actions link:

Fallback triggered: NO
Issue or risk: This is a three-query smoke test, not a BM25 comparison.
Next action: Build a fixed retrieval evaluation set and BM25 baseline.
Owner:

### 2026-08-08 - BM25 and hybrid retrieval smoke test

Status: PASS
Provider and model: SQLite FTS5/BM25 + Ollama/qwen3-embedding:4b
Command: `python bill_retrieval.py --mode <mode> "<query>"`

Expected:

- Exact provider and amount queries rank the matching bill first.
- Semantic synonyms still rank the correct bill first.
- Hybrid results show both component ranks when both methods match.

Observed:

- BM25 ranked Chase Visa first for `Chase Visa`.
- BM25 ranked PSE Electricity first for `142.50`.
- Hybrid ranked PSE Electricity first for `power bill`.
- Hybrid ranked Xfinity Broadband first for `home internet bill`.
- `Chase Visa` and `electricity payment` both received BM25 rank 1 and
  semantic rank 1.

Evidence:
- Test output: 31 tests passed.
- Retrieval fusion: Reciprocal Rank Fusion with rank constant 60.
- Fallback triggered: Semantic-only ranking when BM25 had no synonym match.

Issue or risk: The corpus has only six synthetic structured bill documents.
Next action: Evaluate on real bill emails before adding an agent tool.
Owner:

### 2026-08-08 - Exact amount tokenizer regression

Status: PASS AFTER FIX
Provider and model: SQLite FTS5/BM25
Command: `python bill_retrieval.py --mode bm25 "142.40"`

Expected:

- No result because no bill has an exact amount of $142.40.

Observed before fix:

- PSE matched token `142`.
- Chase and Citi matched token `40`.
- SQLite FTS split the decimal and the OR query produced false positives.

Fix:

- Detect two-decimal amounts and ISO dates before FTS tokenization.
- Apply them as exact structured filters.
- Prevent hybrid semantic search from approximating unmatched exact values.

Evidence after fix:

- `142.40`: no matching bills.
- `142.50`: exact PSE Electricity match.
- `2026-08-10`: exact Citi Mastercard match.
- Test output: 34 tests passed.

Next action: Add exact account-number handling when account identifiers enter
the source data.
Owner:

### 2026-08-08 - Hybrid retrieval agent integration

Status: PASS
Provider and model: Ollama / phi4-mini + qwen3-embedding:4b
Command: `python bill_agent.py "<question>"`

Expected:

- Search questions use `search_bill_records`.
- Exact financial values remain exact.
- Compound search-and-change questions use retrieval and comparison.

Observed:

- `Find my power bill` ranked PSE Electricity first.
- `Which bill is 142.50?` returned only PSE Electricity.
- `Which bill is 142.40?` returned no match.
- `Find my power bill and tell me whether it changed` returned PSE retrieval
  evidence and the deterministic monthly comparison.

Evidence:
- Bill Manager tool count: three read-only tools.
- Test output: 38 tests passed.
- Retrieval output included BM25 and semantic component ranks.
- Final values remained deterministic.

Fallback triggered: Phi-4 coverage rules enforce retrieval when required.
Issue or risk: Retrieval still searches structured sample bills, not emails.
Next action: Add representative email documents and a fixed evaluation set.
Owner:

### 2026-08-08 - Phi-4 tool over-selection

Status: PASS AFTER FIX
Provider and model: Ollama / phi4-mini
Command: `python bill_agent.py "which bill is power bill"`

Observed before fix:

- Phi-4 selected retrieval, due-date, and comparison tools.
- The answer contained correct but unrelated monthly information.

Fix:

- Explicit intent now defines the allowed tool set.
- “Which bill” and “what bill” are recognized as retrieval intent.
- Unrelated model-selected tools are suppressed.

Evidence after fix:

- Retrieval-only question returned only search results.
- Search-and-change question returned retrieval plus comparison.
- Difference formatting changed from `$+29.40` to `+$29.40`.
- Test output: 40 tests passed.

Next action: Expand intent tests with real user phrasing collected during use.
Owner:

### 2026-08-08 - Retrieval follow-up joined every bill

Status: PASS AFTER FIX
Provider and model: Ollama / phi4-mini + hybrid retrieval
Command: `python bill_agent.py "which bill is power bill and how much is due only for power bill ranked 1"`

Observed before fix:

- Retrieval ranked PSE first.
- The due-date section still listed Chase, PSE, and Citi.
- The total represented every upcoming bill instead of the retrieved match.

Fix:

- “Rank 1,” “top result,” and “only for” limit displayed retrieval results.
- Due-date and change follow-ups join to the top retrieved bill ID.
- No-match retrieval does not expose unrelated bill details.

Evidence after fix:

- Only PSE Electricity was displayed.
- Matched due amount was `$142.50`.
- Targeted change was `+$47.50 (+50.0%)`.
- Test output: 43 tests passed.

Next action: Add explicit multi-select language before supporting follow-ups for
more than one retrieved bill.
Owner:

### YYYY-MM-DD - Initial Phi-4 validation

Status: NOT TESTED
Provider and model: Ollama / phi4-mini
Command:

Expected:

Observed:

Evidence:
- Test output:
- Tool calls:
- Final totals:
- Screenshot or Actions link:

Fallback triggered:
Issue or risk:
Next action:
Owner:

## Stop or go

Choose `GO` only when:

- [ ] Every required checklist item passes.
- [ ] Five repeated runs have correct facts.
- [ ] CI passes.
- [ ] Known issues have an owner and next action.
- [ ] No unresolved financial-data or safety risk remains.

Final decision:

```text
Decision: NOT TESTED
Reason:
Approved by:
Date:
```
