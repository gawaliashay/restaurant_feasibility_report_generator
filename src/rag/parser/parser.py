"""
Generic document parser for RAG.

Converts documents into text/Markdown.
Supports: PDF, DOCX, HTML, TXT, Markdown, Websites
"""

from pathlib import Path
from typing import Any
from io import BytesIO

from src.logging_exception.logging.logger import logger
from src.rag.model_schema import ParsedDocument


class UniversalDocumentParser:
    """Parse different document types into text."""

    SUPPORTED_EXTENSIONS = {
        ".pdf": "pdf",
        ".docx": "docx",
        ".html": "html",
        ".htm": "html",
        ".txt": "text",
        ".md": "text",
        ".markdown": "text",
    }

    def __init__(self, max_pages: int | None = None):
        self.max_pages = max_pages

    def parse(self, file_path: str | Path) -> ParsedDocument:
        """Parse a local file."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        doc_type = self.SUPPORTED_EXTENSIONS.get(file_path.suffix.lower())
        if not doc_type:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

        logger.info(f"Parsing: {file_path.name}")

        if doc_type == "pdf":
            content, metadata = self._parse_pdf(file_path)
        elif doc_type == "docx":
            content, metadata = self._parse_docx(file_path)
        elif doc_type == "html":
            content, metadata = self._parse_html(file_path)
        else:
            content, metadata = self._parse_text(file_path)

        return ParsedDocument(
            content=self._clean_content(content),
            metadata=metadata,
            file_name=file_path.name,
        )

    def parse_from_url(self, url: str) -> ParsedDocument:
        """Parse a website URL."""
        import requests
        from bs4 import BeautifulSoup

        logger.info(f"Parsing URL: {url}")

        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove scripts and styles
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        title = soup.title.get_text(strip=True) if soup.title else url
        text = soup.get_text(separator="\n", strip=True)

        return ParsedDocument(
            content=self._clean_content(text),
            metadata={"parser": "beautifulsoup", "url": url, "title": title},
            file_name=title[:50] + "...",
        )

    def parse_from_bytes(self, content: bytes, file_name: str = "document.pdf") -> ParsedDocument:
        """Parse PDF from bytes (for online PDFs)."""
        from io import BytesIO
        text = ""
        pages = 0

        # Try pymupdf first (handles tables, columns better)
        try:
            import fitz
            doc = fitz.open(stream=content, filetype="pdf")
            for page in doc:  # type: ignore
                text += page.get_text()  # type: ignore
            pages = len(doc)
            doc.close()

            if text and len(text.strip()) > 100:
                return ParsedDocument(
                    content=self._clean_content(text),
                    metadata={"parser": "pymupdf", "pages": pages},
                    file_name=file_name,
                )
        except Exception as exc:
            logger.debug(f"pymupdf bytes failed: {exc}")

        # Fallback to pypdf
        try:
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(content))
            all_pages = reader.pages
            pages_to_use = all_pages[:self.max_pages] if self.max_pages else all_pages
            pages = len(pages_to_use)
            text = "\n\n".join(page.extract_text() or "" for page in pages_to_use)
        except Exception as exc:
            logger.debug(f"pypdf bytes failed: {exc}")

        return ParsedDocument(
            content=self._clean_content(text),
            metadata={"parser": "pypdf", "pages": pages},
            file_name=file_name,
        )

    def _parse_pdf(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """Parse PDF - tries pymupdf first, falls back to pypdf."""
        
        # Try pymupdf first (better for tables, columns)
        try:
            import fitz
            doc = fitz.open(str(file_path))
            text = ""
            pages = doc
            if self.max_pages:
                pages = doc[:self.max_pages]
            
            for page in pages:  # type: ignore
                text += page.get_text()  # type: ignore
            doc.close()

            if text and len(text.strip()) > 100:
                return text, {"parser": "pymupdf", "pages": len(pages)}
        except Exception as exc:
            logger.debug(f"pymupdf failed: {exc}")

        # Fallback to pypdf
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(file_path))
            all_pages = reader.pages
            pages = all_pages[:self.max_pages] if self.max_pages else all_pages
            text = "\n\n".join(page.extract_text() or "" for page in pages)

            if text and len(text.strip()) > 100:
                return text, {"parser": "pypdf", "pages": len(pages)}
        except Exception as exc:
            logger.debug(f"pypdf failed: {exc}")

        logger.warning(f"No text extracted: {file_path.name}")
        return "", {"parser": "failed"}

    def _parse_docx(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """Parse DOCX files."""
        from docx import Document

        doc = Document(str(file_path))
        parts = []

        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                parts.append(paragraph.text.strip())

        for table in doc.tables:
            rows = []
            for row in table.rows:
                cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                rows.append("| " + " | ".join(cells) + " |")
            
            if len(rows) > 1:
                separator = "| " + " | ".join(["---"] * len(table.rows[0].cells)) + " |"
                rows.insert(1, separator)
            
            parts.append("### Table\n\n" + "\n".join(rows))

        return "\n\n".join(parts), {"parser": "python-docx"}

    def _parse_html(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """Parse HTML files."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(file_path.read_text(encoding="utf-8"), "html.parser")

        for element in soup(["script", "style"]):
            element.decompose()

        title = soup.title.get_text(strip=True) if soup.title else ""
        text = soup.get_text(separator="\n", strip=True)

        if title:
            text = f"# {title}\n\n{text}"

        return text, {"parser": "beautifulsoup", "title": title}

    def _parse_text(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """Parse plain text files."""
        return file_path.read_text(encoding="utf-8"), {"parser": "text"}

    def _clean_content(self, content: str) -> str:
        """Clean up text."""
        if not content:
            return ""

        import re
        content = content.replace("\r\n", "\n")
        content = re.sub(r"\n{3,}", "\n\n", content)
        return content.strip()

    def parse_multiple(self, file_paths: list[str | Path]) -> list[ParsedDocument]:
        """Parse multiple files."""
        results = []
        for path in file_paths:
            try:
                results.append(self.parse(path))
            except Exception as exc:
                logger.error(f"Failed to parse {Path(path).name}: {exc}")
        return results