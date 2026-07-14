# core/gdpr_requirements.py
"""
Structured GDPR compliance checklist. Each requirement is a (id, description)
pair, grouped by category. Categories match ComplianceScorer.CATEGORY_WEIGHTS
so every category contributes to the weighted overall score.
"""

GDPR_REQUIREMENTS = {
    "Data Subject Rights": [
        ("GDPR-15", "Users have the right to request access to a copy of their personal data."),
        ("GDPR-16", "Users have the right to request correction of inaccurate personal data."),
        ("GDPR-17", "Users have the explicit right to request deletion of their data (Right to be Forgotten)."),
        ("GDPR-18", "Users have the right to request that processing of their data be restricted."),
        ("GDPR-20", "Users have the right to receive their personal data in a portable, machine-readable format."),
        ("GDPR-21", "Users have the right to object to their personal data being processed."),
        ("GDPR-7-3", "Users have the right to withdraw their consent to data processing at any time."),
    ],
    "Transparency & Legal Basis": [
        ("GDPR-13-1a", "The privacy policy identifies the data controller and provides their contact details."),
        ("GDPR-13-1b", "The privacy policy provides contact information for a Data Protection Officer, where applicable."),
        ("GDPR-13-1c", "The privacy policy states the legal basis relied on for processing personal data."),
        ("GDPR-13-1c2", "The privacy policy explains the specific purposes for which personal data is collected."),
        ("GDPR-13-1d", "The privacy policy lists the categories of personal data collected."),
    ],
    "Data Retention": [
        ("GDPR-13-2a", "The privacy policy specifies how long personal data will be retained."),
        ("GDPR-13-2a2", "The privacy policy describes the process for deleting or disposing of personal data once it is no longer needed."),
    ],
    "International Transfers": [
        ("GDPR-44", "The privacy policy discloses whether personal data is transferred outside the EU/EEA and what safeguards apply."),
        ("GDPR-13-1e", "The privacy policy discloses whether personal data is shared with third parties or subprocessors."),
    ],
}