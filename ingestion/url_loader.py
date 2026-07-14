# ingestion/url_loader.py
import re
import uuid
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from core.interfaces import BaseDocumentLoader
from core.models import DocumentChunk


POLICY_SIGNAL_PHRASES = [
    "privacy policy", "personal data", "data controller", "gdpr",
    "data protection officer", "right to access", "right to erasure",
    "right to be forgotten", "data subject", "your rights",
    "processing of your data", "cookies", "third parties",
    "data retention", "opt out",
]

POLICY_LINK_KEYWORDS = [
    "privacy policy", "privacy-policy", "privacy_policy",
    "data protection", "privacy notice", "/privacy",
]

MIN_SIGNAL_MATCHES = 3
MIN_CHUNKS = 5


class PolicyNotFoundError(Exception):
    """Raised when a URL doesn't contain, or lead to, a privacy policy."""
    pass


class URLLoader(BaseDocumentLoader):
    """
    Fetches a web page and converts its visible text into DocumentChunks.
    If the given page doesn't look like a privacy policy, it searches that
    page's links for one and follows it automatically before giving up.
    """

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def load(self, file_path: str) -> List[DocumentChunk]:
        url = file_path
        soup, text = self._fetch(url)

        if self._looks_like_policy(text):
            chunks = self._extract_chunks(soup, url)
            if len(chunks) >= MIN_CHUNKS:
                return chunks

        policy_url = self._find_policy_link(soup, base_url=url)
        if policy_url:
            policy_soup, policy_text = self._fetch(policy_url)
            if self._looks_like_policy(policy_text):
                chunks = self._extract_chunks(policy_soup, policy_url)
                if len(chunks) >= MIN_CHUNKS:
                    return chunks

        raise PolicyNotFoundError(
            "This doesn't look like a privacy policy, and no privacy policy "
            "link could be found on this page."
        )

    def _fetch(self, url: str):
        response = requests.get(
            url, timeout=self.timeout,
            headers={"User-Agent": "Mozilla/5.0 (compliance-scorer research tool)"},
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ").lower()
        return soup, text

    def _looks_like_policy(self, lowercase_text: str) -> bool:
        matches = sum(1 for phrase in POLICY_SIGNAL_PHRASES if phrase in lowercase_text)
        return matches >= MIN_SIGNAL_MATCHES

    def _find_policy_link(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        for a in soup.find_all("a", href=True):
            text = (a.get_text() or "").strip().lower()
            href = a["href"].lower()
            if any(kw in text or kw in href for kw in POLICY_LINK_KEYWORDS):
                return urljoin(base_url, a["href"])
        return None

    def _extract_chunks(self, soup: BeautifulSoup, source_url: str) -> List[DocumentChunk]:
        raw_text = soup.get_text(separator="\n")
        paragraphs = [
            re.sub(r"\s+", " ", p).strip()
            for p in raw_text.split("\n")
            if len(p.strip()) > 40
        ]
        return [
            DocumentChunk(
                chunk_id=f"url_chunk_{i+1}_{uuid.uuid4().hex[:6]}",
                content=paragraph,
                metadata={"source": source_url, "section_index": i + 1},
            )
            for i, paragraph in enumerate(paragraphs)
        ]