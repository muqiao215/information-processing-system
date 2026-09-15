"""
Cross-Source Semantic Deduplication & Topic Fusion Engine
"""
from .models import (
    SourceCitation,
    TopicCluster,
    ConsolidatedDailyBrief,
)
from .fingerprint import (
    extract_entities,
    are_items_semantically_related,
)
from .engine import TopicFusionEngine

__all__ = [
    "SourceCitation",
    "TopicCluster",
    "ConsolidatedDailyBrief",
    "TopicFusionEngine",
    "extract_entities",
    "are_items_semantically_related",
]
