# main.py
from ingestion.pdf_loader import PDFLoader
from storage.vector_store import ChromaVectorStore
from engine.compliance_evaluator import CrossEncoderComplianceEvaluator
from engine.scorer import ComplianceScorer

# Initialize modular components
loader = PDFLoader()
vector_store = ChromaVectorStore()
evaluator = CrossEncoderComplianceEvaluator()
scorer = ComplianceScorer()

# Step 1: Ingest standard rules to test
sample_requirements = {
    "Data Subject Rights": [
        ("GDPR-15", "Users have the right to request access to their personal data."),
        ("GDPR-17", "Users have the explicit right to request deletion of their data (Right to be Forgotten)."),
    ],
    "Transparency & Legal Basis": [
        ("GDPR-13", "The privacy policy specifies contact information for the Data Protection Officer or Controller."),
    ]
}

# Step 2: Query candidate policy chunks from VectorDB & run Cross-Encoder
evaluations_by_cat = {}

for category, rules in sample_requirements.items():
    evaluations_by_cat[category] = []
    for req_id, req_desc in rules:
        # VectorDB retrieves top-3 candidates
        candidates = vector_store.similarity_search(query=req_desc, namespace="user_policy", k=3)
        
        # Cross-Encoder verifies semantics
        result = evaluator.evaluate(req_id, req_desc, candidates)
        evaluations_by_cat[category].append(result)

# Step 3: Compute final scores
report = scorer.calculate_report("GDPR Standard Compliance", evaluations_by_cat)

print(f"Overall Compliance Score: {report.overall_score}%")
print(f"Category Breakdown: {report.category_scores}")