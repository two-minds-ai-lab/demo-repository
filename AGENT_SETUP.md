# Bill Manager agent setup

The Bill Manager uses two deterministic tools:

- `get_bill_due_dates` returns upcoming and later-this-month bills.
- `get_bill_change_analysis` returns monthly totals and bill anomalies.

## Install

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Public OpenAI

```powershell
$env:BILL_AGENT_PROVIDER="openai"
$env:OPENAI_API_KEY="your-api-key"
$env:OPENAI_MODEL="gpt-4.1-mini"
python bill_agent.py "Give me a complete bill summary."
```

## Azure OpenAI

Create a model deployment in Microsoft Foundry, then configure:

```powershell
$env:BILL_AGENT_PROVIDER="azure"
$env:AZURE_OPENAI_API_KEY="your-azure-key"
$env:AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
$env:AZURE_OPENAI_DEPLOYMENT="your-deployment-name"
$env:AZURE_OPENAI_API="responses"
python bill_agent.py "Give me a complete bill summary."
```

Set `AZURE_OPENAI_API` to `chat_completions` if the deployment does not
support the Responses API.

## Local Microsoft Phi-4

Install [Ollama](https://ollama.com/), then run:

```powershell
ollama pull phi4-mini
$env:BILL_AGENT_PROVIDER="phi4"
python bill_agent.py "Give me a complete bill summary."
```

Phi-4 runs locally without a cloud API key. The selected model must support
tool calling. The local adapter also handles Phi-4 Mini versions that emit
tool requests as JSON text instead of native OpenAI-compatible `tool_calls`.
If a local model omits tool metadata, the adapter safely runs both read-only
bill tools. Because small local models can distort dates or totals while
rewriting tool output, Phi-4 answers use the deterministic Python formatter
after tool selection.

The `--provider` option overrides `BILL_AGENT_PROVIDER` for one command:

```powershell
python bill_agent.py --provider azure "Which bills are due soon?"
```

## Local semantic-search experiment

Install the dedicated embedding model:

```powershell
ollama pull qwen3-embedding:4b
python bill_embeddings.py "Find my power bill"
```

The embedding search covers the existing six structured bills. The Bill
Manager exposes hybrid retrieval through its read-only `search_bill_records`
tool.

Compare retrieval modes:

```powershell
python bill_retrieval.py --mode bm25 "Chase Visa"
python bill_retrieval.py --mode semantic "Find my power bill"
python bill_retrieval.py --mode hybrid "Find my power bill"
```

Hybrid retrieval combines BM25 and Qwen3 rankings with Reciprocal Rank Fusion.
Raw BM25 and cosine scores are not mixed because they use different scales.

Run retrieval through the agent:

```powershell
$env:BILL_AGENT_PROVIDER="phi4"
python bill_agent.py "Find my power bill"
python bill_agent.py "Which bill is 142.50?"
python bill_agent.py "Find my power bill and tell me whether it changed."
```
