# GDPR Policy Compliance Checker

Paste a privacy policy (PDF, plain text, or a company's URL) and get an
automated GDPR compliance score with a category breakdown and a findings
ledger showing exactly which requirements are met, partially met, or missing.

## How it works

1. **Ingestion** — the policy is loaded (PDF parsing, pasted text, or fetched
   from a URL with automatic privacy-policy link discovery) and split into
   chunks.
2. **Semantic retrieval** — each chunk is embedded and stored in a Chroma
   vector database. For every GDPR requirement, the most relevant chunks are
   retrieved via similarity search.
3. **NLI evaluation** — a cross-encoder (`nli-deberta-v3-base`) checks
   whether the retrieved text actually *entails* the requirement, not just
   whether the words overlap -- this is what lets it catch paraphrased
   language like "we keep your data" satisfying "data retention period
   disclosed."
4. **Scoring** — results are aggregated into a weighted overall score and a
   per-category breakdown.

## Architecture

Built with SOLID principles throughout: matching/evaluation strategies are
pluggable interfaces (`BaseComplianceEvaluator`, `BaseDocumentLoader`,
`BaseVectorStore`), so extending this to a new regulation (e.g. DORA) is
adding one new requirements file and passing new category weights into
`ComplianceScorer` -- no changes to existing evaluation logic.

## Stack
Flask · ChromaDB · sentence-transformers · cross-encoder NLI · vanilla
HTML/CSS/JS frontend

## Running locally
\`\`\`bash
pip install -r requirements.txt
python server.py
\`\`\`
Then open `http://localhost:5000`.

## Known limitations
- Checklist covers ~16 core GDPR obligations across 4 categories, not the
  full regulation
- Semantic matching can misfire on unusually-worded policies
- Single-user local prototype (in-memory job queue, no auth)

## What I'd add with more time
- DORA support (architecture is already built for this)
- Live deployment
- Export report as PDF
