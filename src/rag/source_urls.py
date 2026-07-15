# ssrc\rag\source_urls.py

from typing import List

WEB_SOURCES = [

    # {
    #     "name": "Licensing and Registration Regulations",
    #     "url": "https://www.fssai.gov.in/upload/uploadfiles/files/Compendium_Licensing_Regulations_04_08_2021.pdf",
    #     "authority": "FSSAI",
    #     "jurisdiction": "central",
    #     "priority": 1
    # },

    {
        "name": "GST on Hotel and Restaurant Services",
        "url": "https://gstcouncil.gov.in/sites/default/files/2024-04/restaurantservices_vns-i.pdf",
        "authority": "GST Council",
        "jurisdiction": "central",
        "priority": 1
    },

    ]
    
def get_sources() -> list[dict]:
    return WEB_SOURCES


def get_source_urls(jurisdiction: str | None = None) -> List[str]:
    sources = WEB_SOURCES
    if jurisdiction:
        sources = [s for s in sources if s["jurisdiction"] == jurisdiction]
    return [s["url"] for s in sources]


def get_priority_sources(max_priority: int = 1) -> list[dict]:
    """Get sources by priority level (default: only priority 1)."""
    return [s for s in WEB_SOURCES if s["priority"] <= max_priority]