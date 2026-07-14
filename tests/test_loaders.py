# tests/test_loaders.py
from unittest.mock import MagicMock, patch
from ingestion.pdf_loader import PDFLoader
from ingestion.raw_text_loader import RawTextLoader


def test_raw_text_loader_splits_paragraphs():
    # Arrange
    loader = RawTextLoader()
    raw_text = "Paragraph 1: We collect email addresses.\n\nParagraph 2: We use cookies for telemetry."

    # Act
    chunks = loader.load(file_path=raw_text, source_name="test_source")

    # Assert
    assert len(chunks) == 2
    assert chunks[0].content == "Paragraph 1: We collect email addresses."
    assert chunks[1].content == "Paragraph 2: We use cookies for telemetry."
    assert chunks[0].metadata["source"] == "test_source"
    assert chunks[0].metadata["section_index"] == 1


@patch("ingestion.pdf_loader.pypdf.PdfReader")
def test_pdf_loader_extracts_pages(mock_pdf_reader):
    # Arrange: Mock PDF Reader with 2 fake pages
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = "Page 1 content: Data Controller details."
    mock_page2 = MagicMock()
    mock_page2.extract_text.return_value = "Page 2 content: Retention policy."

    mock_pdf_reader.return_value.pages = [mock_page1, mock_page2]

    loader = PDFLoader()

    # Act
    chunks = loader.load("fake_path.pdf")

    # Assert
    assert len(chunks) == 2
    assert chunks[0].content == "Page 1 content: Data Controller details."
    assert chunks[0].metadata["page"] == 1
    assert chunks[1].metadata["page"] == 2
