# src\utils\report_exporter.py

import json
import os
from typing import Dict, Any
from datetime import datetime

def save_json_generic(data, path):
    """Reliable JSON export."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path

def save_markdown_generic(data, path):
    """Reliable Markdown export - handles both dict and string data."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(data, dict):
                lines = []
                for key, value in data.items():
                    lines.append(f"## {key}")
                    lines.append(str(value))
                    lines.append("")
                f.write("\n".join(lines))
            else:
                # Handle string data directly
                f.write(str(data))
        return path
    except Exception as e:
        print(f"❌ Markdown export failed: {str(e)}")
        return None