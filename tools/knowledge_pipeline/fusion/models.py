"""
跨源语义去重与主题聚类融合层 (Cross-Source Semantic Deduplication & Topic Fusion Engine)
数据模型定义 (纯 Python 标准库 dataclasses，零外部依赖)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, List, Optional


@dataclass
class SourceCitation:
    source_id: str
    title: str
    url: Optional[str] = None
    canonical_url: Optional[str] = None
    snippet: Optional[str] = None
    published_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TopicCluster:
    topic_id: str
    topic_title: str
    primary_category: str = "AI & Technology"
    entities: List[str] = field(default_factory=list)
    
    # 三层高密度提炼架构
    key_breakthrough: str = ""
    technical_details: List[str] = field(default_factory=list)
    community_discussion: List[str] = field(default_factory=list)
    
    # 溯源元数据
    observed_sources: List[str] = field(default_factory=list)
    citations: List[SourceCitation] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    raw_item_count: int = 1

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["citations"] = [c.to_dict() if isinstance(c, SourceCitation) else c for c in self.citations]
        return d


@dataclass
class ConsolidatedDailyBrief:
    date: str
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    total_raw_items: int = 0
    total_topics: int = 0
    compression_ratio: str = "0%"
    topics: List[TopicCluster] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "generated_at": self.generated_at,
            "total_raw_items": self.total_raw_items,
            "total_topics": self.total_topics,
            "compression_ratio": self.compression_ratio,
            "topics": [t.to_dict() for t in self.topics]
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
