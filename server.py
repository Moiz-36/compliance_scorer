# server.py
import os
import threading
import uuid
import tempfile

from flask import Flask, request, jsonify, send_from_directory

from ingestion.pdf_loader import PDFLoader
from ingestion.raw_text_loader import RawTextLoader
from ingestion.url_loader import URLLoader, PolicyNotFoundError
from storage.vector_store import ChromaVectorStore
from engine.compliance_evaluator import CrossEncoderComplianceEvaluator
from engine.scorer import ComplianceScorer
from core.gdpr_requirements import GDPR_REQUIREMENTS

app = Flask(__name__, static_folder="static", static_url_path="")

# Loaded once at startup -- these are the expensive objects (models, DB connection)
pdf_loader = PDFLoader()
text_loader = RawTextLoader()
url_loader = URLLoader()
vector_store = ChromaVectorStore()
evaluator = CrossEncoderComplianceEvaluator()
scorer = ComplianceScorer()

# In-memory job store -- fine for a single-user local prototype.
# For multi-user/production use you'd swap this for Redis or a DB.
jobs = {}
jobs_lock = threading.Lock()

TOTAL_REQUIREMENTS = sum(len(reqs) for reqs in GDPR_REQUIREMENTS.values())


def _report_to_dict(report):
    # Works whether the project has pydantic v1 or v2 installed
    return report.model_dump() if hasattr(report, "model_dump") else report.dict()


def _run_evaluation(job_id: str, chunks):
    try:
        with jobs_lock:
            jobs[job_id].update(status="processing", completed=0, total=TOTAL_REQUIREMENTS)

        vector_store.clear_namespace("user_policy")
        vector_store.add_chunks(chunks, namespace="user_policy")

        evaluations_by_cat = {}
        for category, rules in GDPR_REQUIREMENTS.items():
            evaluations_by_cat[category] = []
            for req_id, req_desc in rules:
                candidates = vector_store.similarity_search(
                    query=req_desc, namespace="user_policy", k=3
                )
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


def _start_job(chunks) -> str:
    job_id = str(uuid.uuid4())
    with jobs_lock:
        jobs[job_id] = {"status": "queued", "completed": 0, "total": TOTAL_REQUIREMENTS}
    threading.Thread(target=_run_evaluation, args=(job_id, chunks), daemon=True).start()
    return job_id


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/evaluate/text", methods=["POST"])
def evaluate_text():
    data = request.get_json(force=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    chunks = text_loader.load(file_path=text, source_name="pasted_policy")
    if not chunks:
        return jsonify({"error": "Couldn't extract any content from that text"}), 400

    return jsonify({"job_id": _start_job(chunks)})


@app.route("/api/evaluate/url", methods=["POST"])
def evaluate_url():
    data = request.get_json(force=True) or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        chunks = url_loader.load(url)
    except PolicyNotFoundError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Couldn't fetch that URL: {e}"}), 400

    return jsonify({"job_id": _start_job(chunks)})


@app.route("/api/evaluate/pdf", methods=["POST"])
def evaluate_pdf():
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
    vector_store.clear_namespace("user_policy")
    return jsonify({"status": "reset"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)