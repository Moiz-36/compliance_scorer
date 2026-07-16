# server.py
import os
import re
import threading
import uuid
import tempfile

from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="static", static_url_path="")

# --- Lazy model loading -----------------------------------------------------
# Cloud Run requires the container to start listening on its port quickly.
# Loading ML models before Flask starts was pushing past that startup window.
# Instead: Flask binds the port immediately, heavy models load in a
# background thread, and requests made before loading finishes get a clear
# 503 instead of the container failing to start at all.

pdf_loader = None
text_loader = None
url_loader = None
vector_store = None
evaluator = None
scorer = None
GDPR_REQUIREMENTS = None
TOTAL_REQUIREMENTS = 0
PolicyNotFoundError = Exception  # placeholder, replaced once loaded

models_ready = threading.Event()
models_loading_error = None


def _load_models():
    global pdf_loader, text_loader, url_loader, vector_store, evaluator, scorer
    global GDPR_REQUIREMENTS, TOTAL_REQUIREMENTS, models_loading_error, PolicyNotFoundError
    try:
        from ingestion.pdf_loader import PDFLoader
        from ingestion.raw_text_loader import RawTextLoader
        from ingestion.url_loader import URLLoader, PolicyNotFoundError as PNF
        from storage.vector_store import ChromaVectorStore
        from engine.compliance_evaluator import CrossEncoderComplianceEvaluator
        from engine.scorer import ComplianceScorer
        from core.gdpr_requirements import GDPR_REQUIREMENTS as REQS

        pdf_loader = PDFLoader()
        text_loader = RawTextLoader()
        url_loader = URLLoader()
        vector_store = ChromaVectorStore()
        evaluator = CrossEncoderComplianceEvaluator(model_name="cross-encoder/nli-deberta-v3-xsmall")
        scorer = ComplianceScorer()
        GDPR_REQUIREMENTS = REQS
        TOTAL_REQUIREMENTS = sum(len(reqs) for reqs in REQS.values())
        PolicyNotFoundError = PNF

        models_ready.set()
    except Exception as e:
        models_loading_error = str(e)
        models_ready.set()  # still set, so requests get a clear error instead of hanging


threading.Thread(target=_load_models, daemon=True).start()


def _not_ready_response():
    if not models_ready.is_set():
        return jsonify({"error": "Server is warming up, please try again in a few seconds."}), 503
    if models_loading_error:
        return jsonify({"error": f"Server failed to initialize: {models_loading_error}"}), 500
    return None


# --- Validation --------------------------------------------------------------

POLICY_SIGNAL_PHRASES = [
    "privacy policy", "personal data", "personal information", "data controller",
    "data protection", "your rights", "data subject", "processing of your data",
    "third parties", "data retention", "opt out", "cookies", "gdpr",
    "right to access", "right to erasure", "right to be forgotten",
    "datenschutz", "verarbeitung",
]
MIN_SIGNAL_MATCHES = 3


def _is_valid_policy_text(text: str) -> bool:
    if re.match(r'^https?://\S+$', text.strip(), re.IGNORECASE):
        return False
    if len(text) < 150:
        return False
    lowered = text.lower()
    matches = sum(1 for phrase in POLICY_SIGNAL_PHRASES if phrase in lowered)
    return matches >= MIN_SIGNAL_MATCHES


def _report_to_dict(report):
    return report.model_dump() if hasattr(report, "model_dump") else report.dict()


# --- Job handling --------------------------------------------------------------

jobs = {}
jobs_lock = threading.Lock()


def _run_evaluation(job_id: str, chunks):
    namespace = f"policy_{job_id}"
    try:
        with jobs_lock:
            jobs[job_id].update(status="processing", completed=0, total=TOTAL_REQUIREMENTS)

        vector_store.add_chunks(chunks, namespace=namespace)

        evaluations_by_cat = {}
        for category, rules in GDPR_REQUIREMENTS.items():
            evaluations_by_cat[category] = []
            for req_id, req_desc in rules:
                candidates = vector_store.similarity_search(query=req_desc, namespace=namespace, k=3)
                result = evaluator.evaluate(req_id, req_desc, candidates)
                evaluations_by_cat[category].append(result)
                with jobs_lock:
                    jobs[job_id]["completed"] += 1

        report = scorer.calculate_report("GDPR Compliance Check", evaluations_by_cat)
        with jobs_lock:
            jobs[job_id].update(status="done", report=_report_to_dict(report))

    except Exception as e:
        with jobs_lock:
            jobs[job_id].update(status="error", error=str(e))

    finally:
        vector_store.clear_namespace(namespace)


def _start_job(chunks) -> str:
    job_id = str(uuid.uuid4())
    with jobs_lock:
        jobs[job_id] = {"status": "queued", "completed": 0, "total": TOTAL_REQUIREMENTS}
    threading.Thread(target=_run_evaluation, args=(job_id, chunks), daemon=True).start()
    return job_id


# --- Routes --------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/health")
def health():
    return jsonify({"ready": models_ready.is_set() and not models_loading_error})


@app.route("/api/evaluate/text", methods=["POST"])
def evaluate_text():
    not_ready = _not_ready_response()
    if not_ready:
        return not_ready

    data = request.get_json(force=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    if not _is_valid_policy_text(text):
        return jsonify({
            "error": "This doesn't look like a privacy policy. Paste the full policy text, not a URL or a short snippet."
        }), 400

    chunks = text_loader.load(file_path=text, source_name="pasted_policy")
    if not chunks:
        return jsonify({"error": "Couldn't extract any content from that text"}), 400

    return jsonify({"job_id": _start_job(chunks)})


@app.route("/api/evaluate/url", methods=["POST"])
def evaluate_url():
    not_ready = _not_ready_response()
    if not_ready:
        return not_ready

    data = request.get_json(force=True) or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        chunks = url_loader.load(url)
    except PolicyNotFoundError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({
            "error": f"Couldn't fetch that URL ({e}). Some sites block automated "
                     f"requests — try the 'Paste Text' tab instead if this persists."
        }), 400

    return jsonify({"job_id": _start_job(chunks)})


@app.route("/api/evaluate/pdf", methods=["POST"])
def evaluate_pdf():
    not_ready = _not_ready_response()
    if not_ready:
        return not_ready

    if "file" not in request.files or request.files["file"].filename == "":
        return jsonify({"error": "No file uploaded"}), 400

    uploaded = request.files["file"]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        uploaded.save(tmp.name)
        pdf_path = tmp.name

    try:
        chunks = pdf_loader.load(pdf_path)
    finally:
        os.remove(pdf_path)

    if not chunks:
        return jsonify({"error": "Couldn't extract any text from that PDF"}), 400

    return jsonify({"job_id": _start_job(chunks)})


@app.route("/api/evaluate/status/<job_id>", methods=["GET"])
def evaluate_status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            return jsonify({"error": "Unknown job_id"}), 404
        return jsonify(dict(job))


@app.route("/api/reset", methods=["POST"])
def reset():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)