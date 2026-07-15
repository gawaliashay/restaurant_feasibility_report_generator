# src\rag\parser.py

"""
Document Parser - Convert PDF, DOCX, HTML, TXT to Markdown
Simple, reliable, works with tables and scanned documents
"""

from pathlib import Path
from typing import Dict, Any, Optional, Union, List
import mimetypes

from src.logging_exception.logging.logger import logger


class UniversalDocumentParser:
    """
    Parse any document to markdown text.
    
    Supports:
    - PDF (digital + scanned with OCR)
    - DOCX (Microsoft Word)
    - HTML / HTM
    - TXT / Markdown
    
    Tables are extracted as markdown tables.
    """
    
    SUPPORTED_EXTENSIONS = {
        '.pdf': 'pdf',
        '.docx': 'docx',
        '.html': 'html',
        '.htm': 'html',
        '.txt': 'txt',
        '.md': 'markdown',
        '.markdown': 'markdown',
    }
    
    def __init__(
        self,
        enable_ocr: bool = True,
        enable_table_structure: bool = True,
        max_pages: Optional[int] = None,
    ):
        """
        Args:
            enable_ocr: Enable OCR for scanned PDFs
            enable_table_structure: Extract tables as structured data
            max_pages: Maximum pages to process (None = all)
        """
        self.enable_ocr = enable_ocr
        self.enable_table_structure = enable_table_structure
        self.max_pages = max_pages
        
        self._pdf_parser = None
        self._docx_parser = None
        
        logger.info(f"UniversalDocumentParser initialized | OCR: {enable_ocr} | Tables: {enable_table_structure}")
    
    def parse(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Parse document to markdown.
        
        Returns:
            Dict with 'content' (markdown string) and 'metadata'
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        ext = file_path.suffix.lower()
        doc_type = self.SUPPORTED_EXTENSIONS.get(ext)
        
        if not doc_type:
            raise ValueError(f"Unsupported file type: {ext}. Supported: {list(self.SUPPORTED_EXTENSIONS.keys())}")
        
        logger.info(f"Parsing: {file_path.name} ({doc_type})")
        
        if doc_type == 'pdf':
            content, metadata = self._parse_pdf(file_path)
        elif doc_type == 'docx':
            content, metadata = self._parse_docx(file_path)
        elif doc_type == 'html':
            content, metadata = self._parse_html(file_path)
        else:  # txt or markdown
            content, metadata = self._parse_text(file_path)
        
        # Clean up content
        content = self._clean_content(content)
        
        return {
            'content': content,
            'metadata': metadata,
            'file_name': file_path.name,
            'file_size_kb': file_path.stat().st_size / 1024,
        }
    
    def _parse_pdf(self, file_path: Path) -> tuple[str, dict]:
        """Parse PDF using multiple strategies."""
        
        # Strategy 1: Try pypdf (fast, for digital PDFs)
        content = self._try_pypdf(file_path)
        if content and len(content) > 500:
            logger.info(f"  ✓ pypdf extracted {len(content)} chars")
            return content, {'method': 'pypdf', 'pages': self._get_page_count(file_path)}
        
        # Strategy 2: Try docling with OCR (for scanned PDFs)
        if self.enable_ocr:
            content = self._try_docling(file_path)
            if content and len(content) > 500:
                logger.info(f"  ✓ docling+OCR extracted {len(content)} chars")
                return content, {'method': 'docling_ocr', 'pages': self._get_page_count(file_path)}
        
        # Strategy 3: Try pdfplumber (good for tables)
        content = self._try_pdfplumber(file_path)
        if content and len(content) > 500:
            logger.info(f"  ✓ pdfplumber extracted {len(content)} chars")
            return content, {'method': 'pdfplumber', 'pages': self._get_page_count(file_path)}
        
        # Strategy 4: Last resort - simple text extraction
        content = self._try_simple_pdf(file_path)
        if content:
            logger.info(f"  ✓ simple extraction: {len(content)} chars")
            return content, {'method': 'simple', 'pages': self._get_page_count(file_path)}
        
        logger.warning(f"  ✗ No text extracted from PDF")
        return "", {'method': 'failed', 'pages': 0}
    
    def _try_pypdf(self, file_path: Path) -> str:
        """Extract text using pypdf."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(file_path))
            
            text_parts = []
            pages = len(reader.pages)
            
            if self.max_pages:
                pages = min(pages, self.max_pages)
            
            for i in range(pages):
                page = reader.pages[i]
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"\n\n## Page {i+1}\n\n{page_text}")
            
            return '\n'.join(text_parts)
        except Exception as e:
            logger.debug(f"pypdf failed: {e}")
            return ""
    
    def _try_docling(self, file_path: Path) -> str:
        """Extract text using docling with OCR."""
        try:
            from docling.document_converter import DocumentConverter
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
            
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = True
            pipeline_options.do_table_structure = self.enable_table_structure
            
            if self.enable_ocr:
                pipeline_options.ocr_options = EasyOcrOptions(use_gpu=False)
            
            converter = DocumentConverter()
            result = converter.convert(str(file_path))
            return result.document.export_to_markdown()
        except ImportError:
            logger.debug("docling not installed")
            return ""
        except Exception as e:
            logger.debug(f"docling failed: {e}")
            return ""
    
    def _try_pdfplumber(self, file_path: Path) -> str:
        """Extract text using pdfplumber (good for tables)."""
        try:
            import pdfplumber
            
            text_parts = []
            with pdfplumber.open(str(file_path)) as pdf:
                pages = len(pdf.pages)
                if self.max_pages:
                    pages = min(pages, self.max_pages)
                
                for i in range(pages):
                    page = pdf.pages[i]
                    
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"\n\n## Page {i+1}\n\n{page_text}")
                    
                    # Extract tables
                    if self.enable_table_structure:
                        tables = page.extract_tables()
                        for table in tables:
                            if table and len(table) > 1:
                                table_md = self._table_to_markdown(table)
                                text_parts.append(f"\n\n### Table\n\n{table_md}")
            
            return '\n'.join(text_parts)
        except ImportError:
            logger.debug("pdfplumber not installed")
            return ""
        except Exception as e:
            logger.debug(f"pdfplumber failed: {e}")
            return ""
    
    def _try_simple_pdf(self, file_path: Path) -> str:
        """Simple text extraction as last resort."""
        try:
            import subprocess
            import tempfile
            
            # Try pdftotext (poppler-utils)
            with tempfile.NamedTemporaryFile(mode='r+', suffix='.txt') as tmp:
                result = subprocess.run(
                    ['pdftotext', str(file_path), tmp.name],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    tmp.seek(0)
                    return tmp.read()
        except Exception:
            pass
        
        return ""
    
    def _get_page_count(self, file_path: Path) -> int:
        """Get PDF page count."""
        try:
            from pypdf import PdfReader
            return len(PdfReader(str(file_path)).pages)
        except:
            return 0
    
    def _parse_docx(self, file_path: Path) -> tuple[str, dict]:
        """Parse DOCX file."""
        try:
            from docx import Document
            
            # FIX: Convert Path to string
            doc = Document(str(file_path))  # ← Added str() here
            
            text_parts = []
            
            # Extract paragraphs
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)
            
            # Extract tables
            if self.enable_table_structure:
                for table in doc.tables:
                    table_md = self._extract_word_table(table)
                    if table_md:
                        text_parts.append(f"\n\n### Table\n\n{table_md}")
            
            content = '\n\n'.join(text_parts)
            return content, {'paragraphs': len(doc.paragraphs), 'tables': len(doc.tables)}
            
        except ImportError:
            logger.error("python-docx not installed. Run: pip install python-docx")
            return "", {'error': 'python-docx missing'}
        except Exception as e:
            logger.error(f"DOCX parsing failed: {e}")
            return "", {'error': str(e)}
    
    def _extract_word_table(self, table) -> str:
        """Extract table from python-docx to markdown."""
        rows = []
        for row in table.rows:
            cells = [cell.text.strip().replace('\n', ' ') for cell in row.cells]
            rows.append('| ' + ' | '.join(cells) + ' |')
        
        if len(rows) > 1:
            # Add header separator
            col_count = len(table.rows[0].cells)
            rows.insert(1, '| ' + ' | '.join(['---'] * col_count) + ' |')
        
        return '\n'.join(rows)
    
    def _parse_html(self, file_path: Path) -> tuple[str, dict]:
        """Parse HTML file."""
        try:
            from bs4 import BeautifulSoup
            
            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            
            # Remove script and style
            for script in soup(['script', 'style']):
                script.decompose()
            
            # Extract title
            title = soup.title.string if soup.title else file_path.stem
            
            # Convert tables to markdown
            for table in soup.find_all('table'):
                table_md = self._extract_html_table(table)
                table.replace_with(BeautifulSoup(table_md, 'html.parser'))
            
            # Get text
            text = soup.get_text()
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            content = f"# {title}\n\n" + '\n\n'.join(lines)
            
            return content, {'title': title, 'lines': len(lines)}
            
        except ImportError:
            logger.error("beautifulsoup4 not installed. Run: pip install beautifulsoup4")
            return "", {'error': 'beautifulsoup4 missing'}
        except Exception as e:
            logger.error(f"HTML parsing failed: {e}")
            return "", {'error': str(e)}
    
    def _extract_html_table(self, table) -> str:
        """Extract HTML table to markdown."""
        rows = []
        for row in table.find_all('tr'):
            cells = [cell.get_text().strip().replace('\n', ' ') for cell in row.find_all(['td', 'th'])]
            if cells:
                rows.append('| ' + ' | '.join(cells) + ' |')
        
        if len(rows) > 1:
            col_count = len(table.find_all('tr')[0].find_all(['td', 'th']))
            rows.insert(1, '| ' + ' | '.join(['---'] * col_count) + ' |')
        
        return '\n'.join(rows)
    
    def _parse_text(self, file_path: Path) -> tuple[str, dict]:
        """Parse plain text or markdown."""
        content = file_path.read_text(encoding='utf-8')
        lines = len(content.splitlines())
        return content, {'lines': lines, 'chars': len(content)}
    
    def _table_to_markdown(self, table: List[List]) -> str:
        """Convert extracted table to markdown."""
        if not table or len(table) < 1:
            return ""
        
        rows = []
        for row in table:
            cells = [str(cell).strip().replace('\n', ' ') if cell else '' for cell in row]
            rows.append('| ' + ' | '.join(cells) + ' |')
        
        if len(rows) > 1:
            col_count = len(table[0]) if table[0] else 1
            rows.insert(1, '| ' + ' | '.join(['---'] * col_count) + ' |')
        
        return '\n'.join(rows)
    
    def _clean_content(self, content: str) -> str:
        """Clean up extracted content."""
        if not content:
            return ""
        
        # Remove excessive newlines
        import re
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Remove empty markdown tables
        content = re.sub(r'\|\s*---\s*\|\s*\n\|\s*---\s*\|', '', content)
        
        return content.strip()
    
    def parse_multiple(self, file_paths: List[Path]) -> List[Dict[str, Any]]:
        """Parse multiple documents."""
        results = []
        for file_path in file_paths:
            try:
                results.append(self.parse(file_path))
            except Exception as e:
                logger.error(f"Failed to parse {file_path.name}: {e}")
                results.append({
                    'file_name': file_path.name,
                    'error': str(e),
                    'content': '',
                    'metadata': {}
                })
        return results


# Convenience function
def parse_document(file_path: Union[str, Path], **kwargs) -> Dict[str, Any]:
    """Quick parse a single document."""
    parser = UniversalDocumentParser(**kwargs)
    return parser.parse(file_path)


if __name__ == "__main__":
    # Test the parser
    import sys
    
    parser = UniversalDocumentParser(enable_ocr=True, enable_table_structure=True)
    
    test_files = [
        Path("data/raw/base_docs/Legal_&_Regulatory_Handbook_for_Restaurants_and_Cafés.pdf"),
    ]
    
    for test_file in test_files:
        if test_file.exists():
            print(f"\n{'='*50}")
            print(f"Testing: {test_file.name}")
            try:
                result = parser.parse(test_file)
                print(f"✓ Content length: {len(result['content'])} chars")
                print(f"✓ Method: {result['metadata'].get('method', 'unknown')}")
                if result['content']:
                    print(f"\nPreview (first 500 chars):\n{result['content'][:500]}")
                else:
                    print("⚠ No content extracted!")
            except Exception as e:
                print(f"✗ Failed: {e}")