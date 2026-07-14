import tempfile
import streamlit as st

from ingestion.pdf_loader import PDFLoader
from ingestion.raw_text_loader import RawTextLoader
from storage.vector_store import ChromaVectorStore
from engine.compliance_evaluator import CrossEncoderComplianceEvaluator
from engine.scorer import ComplianceScorer
from core.gdpr_requirements import GDPR_REQUIREMENTS


@st.cache_resource
def get_vector_store():
    return ChromaVectorStore()

@st.cache_resource
def get_evaluator():
    return CrossEncoderComplianceEvaluator()

pdf_loader = PDFLoader()
text_loader = RawTextLoader()
vector_store = get_vector_store()
evaluator = get_evaluator()
scorer = ComplianceScorer()

# Persist across reruns -- this is the fix
if "policy_chunks" not in st.session_state:
    st.session_state.policy_chunks = []

st.title("🛡️ GDPR Policy Compliance Checker")
st.write("Analyze any privacy policy for GDPR compliance using AI.")
if st.button("🔄 Reset for New Policy"):
    vector_store.clear_namespace("user_policy")
    st.session_state.policy_chunks = []
    st.session_state.pop("report", None)
    st.rerun()

tab1, tab2, tab3 = st.tabs(["📄 Upload PDF File", "✏️ Paste Policy Text", "🔗 Paste Policy Link"])

with tab1:
    uploaded_pdf = st.file_uploader("Choose a Privacy Policy PDF", type=["pdf"])
    if uploaded_pdf is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_pdf.getvalue())
            pdf_path = tmp.name
        st.session_state.policy_chunks = pdf_loader.load(pdf_path)
        st.success(f"Successfully loaded PDF! Extracted {len(st.session_state.policy_chunks)} sections.")

with tab2:
    pasted_text = st.text_area(
        "Paste the Privacy Policy text here:", height=300,
        placeholder="Paste full terms & privacy policy text...",
    )
    if st.button("Process Pasted Text"):
        if pasted_text.strip():
            st.session_state.policy_chunks = text_loader.load(file_path=pasted_text, source_name="pasted_policy")
            st.success(f"Successfully parsed text! Created {len(st.session_state.policy_chunks)} paragraph chunks.")
        else:
            st.warning("Please paste some text first.")
with tab3:
    from ingestion.url_loader import URLLoader
    url_loader = URLLoader()
    policy_url = st.text_input("Paste the privacy policy page URL:", placeholder="https://example.com/privacy")
    if st.button("Fetch & Process URL"):
        if policy_url.strip():
            with st.spinner("Fetching page..."):
                try:
                    st.session_state.policy_chunks = url_loader.load(policy_url.strip())
                    st.success(f"Fetched page! Extracted {len(st.session_state.policy_chunks)} sections.")
                except Exception as e:
                    st.error(f"Couldn't fetch that URL: {e}")
        else:
            st.warning("Please paste a URL first.")

policy_chunks = st.session_state.policy_chunks

if policy_chunks:
    st.info(f"Ready to evaluate {len(policy_chunks)} chunks against GDPR rules!")

    if st.button("🔍 Evaluate GDPR Compliance", type="primary"):
        with st.spinner("Indexing policy and evaluating against GDPR requirements..."):
            vector_store.add_chunks(policy_chunks, namespace="user_policy")

            evaluations_by_cat = {}
            for category, rules in GDPR_REQUIREMENTS.items():
                evaluations_by_cat[category] = []
                for req_id, req_desc in rules:
                    candidates = vector_store.similarity_search(
                        query=req_desc, namespace="user_policy", k=3
                    )
                    result = evaluator.evaluate(req_id, req_desc, candidates)
                    evaluations_by_cat[category].append(result)

            report = scorer.calculate_report("GDPR Compliance Check", evaluations_by_cat)
            st.session_state["report"] = report

if "report" in st.session_state:
    report = st.session_state["report"]
    st.divider()
    st.header("📊 Compliance Report")

    st.metric("Overall GDPR Compliance Score", f"{report.overall_score}%")

    cols = st.columns(len(report.category_scores))
    for col, (category, score) in zip(cols, report.category_scores.items()):
        with col:
            st.metric(category, f"{score}%")
            st.progress(score / 100)

    st.subheader("🚩 Findings & Gaps")
    status_icon = {"SATISFIED": "✅", "PARTIAL": "⚠️", "MISSING": "❌"}
    for e in report.evaluations:
        with st.expander(f"{status_icon[e.status]} [{e.requirement_id}] {e.requirement_desc}"):
            st.write(f"**Status:** {e.status}  |  **Confidence:** {e.confidence_score}")
            if e.evidence_text:
                st.write(f"**Evidence found:** _{e.evidence_text[:300]}..._")
            else:
                st.write("No matching evidence found in the policy.")