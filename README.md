# 🛡️ GDPR Policy Compliance Checker

**[Try it live →](https://gdpr-compliance-checker-618337916902.us-central1.run.app)**

Paste a privacy policy — as a PDF, pasted text, or just a company's URL — and get an automated GDPR compliance score with a category breakdown and a detailed findings ledger showing exactly which requirements are satisfied, partially met, or missing.

> Note: this runs on a free-tier cloud instance that spins down after periods of inactivity. The first request after a while may take up to a minute to wake up — that's expected, not a bug.

---

## What it does

1. **Ingest a policy** three ways:
   - Upload a PDF
   - Paste raw text
   - Paste a company URL — if that page isn't the policy itself, the tool automatically searches the page's links for one and follows it
2. **Semantic evaluation** — every chunk of the policy is embedded and stored in a vector database. For each GDPR requirement, the most relevant chunks are retrieved and checked with a natural language inference (NLI) model — not keyword matching, so paraphrased language (e.g. "we keep your data for two years" satisfying "data retention period disclosed") is correctly recognized.
3. **Scoring** — results are aggregated into a weighted overall compliance score and a per-category breakdown (Data Subject Rights, Transparency & Legal Basis, Data Retention, International Transfers).
4. **Findings ledger** — every requirement is listed with its status (✓ satisfied / ~ partial / ✕ missing), the actual evidence text found in the policy, and a confidence score.

---

## Architecture

Built around SOLID principles throughout, not just as a checkbox — the design choices actually pay off in this codebase:

- **Pluggable evaluation strategy** — `BaseComplianceEvaluator` is an abstract interface; the current implementation uses a cross-encoder NLI model, but a different evaluation approach could be swapped in without touching any other code.
- **Pluggable document loaders** — `PDFLoader`, `RawTextLoader`, and `URLLoader` all implement the same `BaseDocumentLoader` interface, so ingestion source is interchangeable everywhere else in the pipeline.
- **Extensible scoring** — `ComplianceScorer` accepts `category_weights` in its constructor rather than hardcoding GDPR's categories. Adding support for a new regulation (e.g. DORA) is: write a new requirements checklist file, pass its category weights into the scorer — zero changes to existing evaluation or scoring logic.
- **Async job handling** — the backend runs evaluation as a background job with a polling endpoint (`/api/evaluate/status/<job_id>`) rather than a blocking request, so the frontend can show live progress ("reviewing requirement 6 of 16...") during the several-second evaluation.

## Stack

- **Backend**: Flask, running as a background job queue with polling
- **Embeddings & retrieval**: `sentence-transformers` (`all-MiniLM-L6-v2`) + ChromaDB for vector storage/similarity search
- **Compliance evaluation**: `cross-encoder/nli-deberta-v3-xsmall` for natural language inference
- **Ingestion**: `pypdf` (PDF), `BeautifulSoup` + `requests` (URL fetching + auto-discovery)
- **Frontend**: vanilla HTML/CSS/JS — no framework, calls the Flask API directly
- **Deployment**: Docker container on Google Cloud Run

## Running locally

```bash
pip install -r requirements.txt
python server.py
```
Then open `http://localhost:5000` (or whatever port your environment sets).

## Known limitations

- The requirements checklist covers ~16 core GDPR obligations across 4 categories — a meaningful, correctly-scored subset, not full regulatory coverage of GDPR's ~99 articles
- Semantic matching can misfire on unusually structured or very informally worded policies
- Single-instance deployment — the in-memory job queue assumes one running container (deliberately capped via `--max-instances 1`), fine for a low-traffic demo, not for production scale
- URL fetching only works on server-rendered pages — JavaScript-rendered privacy policy pages won't be readable


## What I'd add with more time

- A second regulation (DORA) to prove out the extensible scoring architecture end-to-end
- Export the compliance report as a downloadable PDF
- A labeled evaluation set to measure precision/recall of the matching pipeline quantitatively, rather than spot-checking known-good/known-bad policies
- Persistent per-user history instead of a stateless single-check flow