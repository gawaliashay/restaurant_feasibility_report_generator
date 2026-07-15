import re
from src.utils.create_unique_uuid import generate_uuid


class MetadataExtractor:

    @staticmethod
    def extract(
                text: str,
                document_name: str,
                chunk_index: int | None,
            ) -> dict:

        return {
            "section": MetadataExtractor._extract_section(
                text=text,
                chunk_index=chunk_index,
            ),
            "jurisdiction": MetadataExtractor._detect_jurisdiction(
                text=text,
                document_name=document_name,
            ),
            "topic": MetadataExtractor._detect_topic(
                text=text,
            ),
        }

    @staticmethod
    def _extract_section(
        text: str,
        chunk_index: int | None,
    ) -> str:

        patterns = [
            r"(?:Section|Sec|§)\s*(\d+(?:\.\d+)*)",
            r"(?:Chapter|Ch)\s*(\d+(?:\.\d+)*)",
            r"(?:Regulation|Reg)\s*(\d+(?:\.\d+)*)",
            r"(?:Rule|R)\s*(\d+(?:\.\d+)*)",
            r"(?:Article|Art)\s*(\d+(?:\.\d+)*)",
            r"(\d+(?:\.\d+)*)\s+(?:of|under|as per)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        if chunk_index is not None and chunk_index > 0:
            return f"Chunk {chunk_index}"

        return ""

    @staticmethod
    def _detect_jurisdiction(
        text: str,
        document_name: str,
    ) -> str:

        states = [
            "Maharashtra",
            "Karnataka",
            "Delhi",
            "Tamil Nadu",
            "Gujarat",
            "West Bengal",
            "Telangana",
        ]

        text_lower = text.lower()
        doc_lower = document_name.lower()

        for state in states:
            if state.lower() in text_lower:
                return state

            if state.lower() in doc_lower:
                return state

        if any(
            indicator in text_lower
            for indicator in [
                "central",
                "government of india",
                "ministry of",
                "fssai",
            ]
        ):
            return "Central"

        return "Unknown"

    @staticmethod
    def _detect_topic(text: str) -> str:

        topics = {
            "Licensing": ["license", "permit", "registration"],
            "FSSAI": ["fssai", "food safety"],
            "Municipal": ["municipal", "trade license"],
            "Fire Safety": ["fire", "noc"],
            "Pollution": ["pollution", "waste"],
            "Labour": ["labour", "employee"],
            "Tax": ["gst", "tax"],
            "Excise": ["excise", "liquor"],
        }

        text_lower = text.lower()

        for topic, keywords in topics.items():
            if any(keyword in text_lower for keyword in keywords):
                return topic

        return "General"
    
    @staticmethod
    def build_metadata(chunk: dict) -> dict:

        original_metadata = chunk.get("metadata", {})

        chunk_index = chunk.get("chunk_index")
        chunk_id = chunk.get("chunk_id", generate_uuid)
        document_name = original_metadata.get("document_name", "")

        extracted = MetadataExtractor.extract(
            text=chunk["text"],
            document_name=document_name,
            chunk_index=chunk_index,
        )

        return {
            "chunk_id": chunk_id,
            "chunk_index": chunk_index,
            **original_metadata,
            **extracted,
        }