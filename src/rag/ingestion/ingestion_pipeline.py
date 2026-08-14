"""
Document ingestion pipeline.
Flow: Parse -> Chunk -> Store
"""

from pathlib import Path
from typing import Any, Dict, List
import requests

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.configuration.config_loader import config_loader
from src.logging_exception.logging.logger import logger
from src.rag.model_schema import DocumentChunk
from src.rag.parser.parser import UniversalDocumentParser
from src.rag.vector_store.vector_store import get_vector_store


class IngestionPipeline:
    """
    Parse documents, split into chunks and store them.
    """

    def __init__(self):
        splitting = config_loader.get("rag_splitting", {})
        strategy_name = splitting.get("default_strategy", "recursive_character")
        strategy = splitting.get(strategy_name, {})

        self.parser = UniversalDocumentParser()
        self.vector_store = get_vector_store()

        self.chunker = RecursiveCharacterTextSplitter(
            chunk_size=strategy.get("chunk_size", 512),
            chunk_overlap=strategy.get("chunk_overlap", 50),
            separators=strategy.get("separators", ["\n\n", "\n", ". ", " ", ""]),
        )

        logger.info("IngestionPipeline initialized")

    def ingest_files(self, file_paths: List[Path]) -> Dict[str, Any]:
        """Ingest local files (PDF, DOCX, TXT, etc)."""
        total_chunks = 0
        results = []

        for file_path in file_paths:
            try:
                parsed_document = self.parser.parse(file_path)

                if not parsed_document.content or len(parsed_document.content.strip()) < 100:
                    logger.warning(f"Skipping {file_path.name}")
                    results.append({"file": file_path.name, "status": "skipped"})
                    continue

                chunks = self._create_chunks(parsed_document)

                if chunks:
                    self.vector_store.add_chunks([chunk.to_dict() for chunk in chunks])

                total_chunks += len(chunks)
                results.append({"file": file_path.name, "status": "success", "chunks": len(chunks)})

            except Exception as exc:
                logger.exception(exc)
                results.append({"file": file_path.name, "status": "failed", "error": str(exc)})

        return {"total_files": len(file_paths), "total_chunks": total_chunks, "results": results}

    def ingest_website(self, url: str) -> Dict[str, Any]:
        """Ingest content from a website URL."""
        try:
            parsed = self.parser.parse_from_url(url)
            chunks = self._create_chunks(parsed)
            if chunks:
                self.vector_store.add_chunks([chunk.to_dict() for chunk in chunks])
            return {"url": url, "status": "success", "chunks": len(chunks)}
        except Exception as exc:
            logger.exception(f"Website ingestion failed: {exc}")
            return {"url": url, "status": "failed", "error": str(exc)}

    def ingest_online_pdf(self, url: str) -> Dict[str, Any]:
        """Ingest a PDF from a URL."""
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            parsed = self.parser.parse_from_bytes(response.content, url.split('/')[-1])
            chunks = self._create_chunks(parsed)
            if chunks:
                self.vector_store.add_chunks([chunk.to_dict() for chunk in chunks])
            return {"url": url, "status": "success", "chunks": len(chunks)}
        except Exception as exc:
            logger.exception(f"Online PDF ingestion failed: {exc}")
            return {"url": url, "status": "failed", "error": str(exc)}

    def ingest_directory(self, directory: Path) -> Dict[str, Any]:
        """Ingest all supported files in a directory."""
        files = []
        for extension in ["*.pdf", "*.docx", "*.txt", "*.md", "*.html"]:
            files.extend(directory.rglob(extension))
        return self.ingest_files(files)

    def _create_chunks(self, parsed_document) -> List[DocumentChunk]:
        """Split document content into chunks."""
        texts = self.chunker.split_text(parsed_document.content)
        chunks = []
        for index, text in enumerate(texts):
            if not text.strip():
                continue
            chunks.append(
                DocumentChunk(
                    text=text,
                    metadata={
                        "document_name": parsed_document.file_name,
                        "chunk_index": index,
                        **parsed_document.metadata,
                    },
                )
            )
        return chunks