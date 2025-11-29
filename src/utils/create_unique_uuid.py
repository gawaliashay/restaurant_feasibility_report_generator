# src\utils\create_unique_uuid.py

"""
UUID generation utilities for the research report system.
Provides various formats of unique identifiers for workflow threads and other needs.
"""

import uuid
from datetime import datetime
from typing import Literal, Optional


def generate_unique_id(
    style: Literal["uuid", "timestamp", "mixed", "sequential"] = "mixed",
    prefix: Optional[str] = None,
    suffix: Optional[str] = None,
    delimiter: str = "_"
) -> str:
    """
    Generate unique identifiers in various formats.
    
    Args:
        style: Format style for the ID
            - "uuid": Pure UUID (e.g., "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
            - "timestamp": Readable timestamp (e.g., "report_20241215_143022")
            - "mixed": Timestamp + short UUID (e.g., "report_20241215_143022_a1b2c3d4")
            - "sequential": Timestamp + counter (requires external counter management)
        prefix: Optional prefix for the ID (e.g., "report", "analyst", "workflow")
        suffix: Optional suffix for the ID
        delimiter: Delimiter between parts of the ID
        
    Returns:
        Unique identifier string
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Set default prefix based on style if not provided
    if prefix is None:
        prefix = "id"
    
    if style == "uuid":
        return str(uuid.uuid4())
    
    elif style == "timestamp":
        parts = [prefix, timestamp]
        if suffix:
            parts.append(suffix)
        return delimiter.join(parts)
    
    elif style == "mixed":
        short_uuid = uuid.uuid4().hex[:8]  # First 8 characters of UUID
        parts = [prefix, timestamp, short_uuid]
        if suffix:
            parts.append(suffix)
        return delimiter.join(parts)
    
    elif style == "sequential":
        # Note: For true sequential IDs, you'd need a counter service/database
        # This is a pseudo-sequential based on microsecond
        microsecond = datetime.now().strftime("%f")[:4]
        parts = [prefix, timestamp, microsecond]
        if suffix:
            parts.append(suffix)
        return delimiter.join(parts)
    
    else:
        return str(uuid.uuid4())


def generate_thread_id(prefix: str = "thread") -> str:
    """
    Generate a thread ID specifically for LangGraph workflows.
    
    Args:
        prefix: Prefix for the thread ID
        
    Returns:
        Thread ID suitable for LangGraph checkpointer
    """
    return generate_unique_id(style="mixed", prefix=prefix)


def generate_report_id() -> str:
    """
    Generate a report-specific ID.
    
    Returns:
        Report ID string
    """
    return generate_unique_id(style="mixed", prefix="report")


def generate_analyst_id() -> str:
    """
    Generate an analyst-specific ID.
    
    Returns:
        Analyst ID string
    """
    return generate_unique_id(style="mixed", prefix="analyst")


def is_valid_uuid(uuid_string: str) -> bool:
    """
    Validate if a string is a valid UUID.
    
    Args:
        uuid_string: String to validate
        
    Returns:
        True if valid UUID, False otherwise
    """
    try:
        uuid.UUID(uuid_string)
        return True
    except (ValueError, AttributeError):
        return False


# Example usage and testing
if __name__ == "__main__":
    # Demo the different ID formats
    print("=== UUID Generation Demo ===")
    print(f"Pure UUID: {generate_unique_id('uuid')}")
    print(f"Timestamp: {generate_unique_id('timestamp', 'report')}")
    print(f"Mixed: {generate_unique_id('mixed', 'workflow')}")
    print(f"Custom: {generate_unique_id('mixed', 'analyst', 'research')}")
    
    print(f"\nThread ID: {generate_thread_id()}")
    print(f"Report ID: {generate_report_id()}")
    print(f"Analyst ID: {generate_analyst_id()}")
    
    # Validation test
    test_uuid = generate_unique_id('uuid')
    print(f"\nValidation test: '{test_uuid}' is valid: {is_valid_uuid(test_uuid)}")
    print(f"Validation test: 'invalid' is valid: {is_valid_uuid('invalid')}")