"""
跨源语义去重与主题聚类融合引擎核心实现 (Topic Fusion Engine)
"""
from __future__ import annotations

import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Any, List, Dict, Tuple

from .models import (
    SourceCitation,
    TopicCluster,
    ConsolidatedDailyBrief,
)
from .fingerprint import (
    extract_entities,
    are_items_semantically_related,
)


def categorize_topic(topic_title: str, tags: List[str], entities: List[str]) -> str:
    """自动判断主题分类"""
    lower_text = f"{topic_title} {' '.join(tags)} {' '.join(entities)}".lower()
    
    if any(k in lower_text for k in ["robot", "arm", "slam", "ros2", "nav2", "hardware", "firmware", "lidar"]):
        return "Robotics & Embodied AI"
    elif any(k in lower_text for k in ["agent", "harness", "reasoning", "orchestrat", "mcp", "tool"]):
        return "AI Agents & Tooling"
    elif any(k in lower_text for k in ["model", "llm", "transformer", "arxiv", "paper", "dataset", "benchmark"]):
        return "Foundational Models & Research"
    elif any(k in lower_text for k in ["browser", "web", "automation", "scraping"]):
        return "Browser & Web Automation"
    elif any(k in lower_text for k in ["system", "network", "proxy", "routing", "security", "infra"]):
        return "Systems & Infrastructure"
    return "AI & Technology Breakthroughs"


def synthesize_cluster_layers(items: List[Dict[str, Any]]) -> Tuple[str, List[str], List[str]]:
    """
    分层提取并合成：
    1. 【关键突破】(Key Breakthrough)
    2. 【技术细节】(Technical Details)
    3. 【社区与产业讨论】(Community & Industry Discussion)
    """
    # 按照信源类型划分信息
    arxiv_items = [it for it in items if "arxiv" in it.get("source_id", "").lower()]
    github_items = [it for it in items if "builderpulse" in it.get("source_id", "").lower() or "github" in it.get("source_id", "").lower()]
    news_items = [it for it in items if it not in arxiv_items and it not in github_items]
    
    # 1. 关键突破：以最具代表性的标题和摘要为核心
    primary_item = items[0]
    # 优先选 news 或 builders 里的宏观描述
    if news_items:
        primary_item = news_items[0]
    elif github_items:
        primary_item = github_items[0]
        
    lead_title = primary_item.get("title", "").strip()
    lead_summary = (primary_item.get("summary") or primary_item.get("raw_text") or "").strip()
    # 截取一句话摘要
    first_sentence = lead_summary.split("\n")[0] if lead_summary else lead_title
    if len(first_sentence) > 200:
        first_sentence = first_sentence[:197] + "..."
    key_breakthrough = f"{lead_title}：{first_sentence}"

    # 2. 技术细节：从论文、GitHub 仓库或技术摘要中提取
    tech_details: List[str] = []
    
    for it in arxiv_items:
        title = it.get("title", "")
        summary = (it.get("summary") or it.get("raw_text") or "").strip()
        short_summary = summary.replace("\n", " ")[:240]
        tech_details.append(f"【学术论文/理论】《{title}》：{short_summary}...")
        
    for it in github_items:
        title = it.get("title", "")
        desc = (it.get("summary") or it.get("raw_text") or "").strip()
        url = it.get("url", "")
        tech_details.append(f"【代码仓库/架构实现】{title} ({url})：{desc[:200]}")
        
    # 若无专门的技术源，则从通用摘要中提取非空要点
    if not tech_details:
        for it in items[:2]:
            s = it.get("summary", "")
            if s and s != first_sentence:
                tech_details.append(s[:220])

    # 3. 社区与产业讨论：从资讯、BuilderPulse 评价或新闻中提取
    community_notes: List[str] = []
    for it in news_items:
        source_name = it.get("source_id", "资讯")
        title = it.get("title", "")
        selected_reason = it.get("selected_reason", "")
        if selected_reason:
            community_notes.append(f"[{source_name}] 采选动因与背景：{selected_reason}")
        else:
            community_notes.append(f"[{source_name}] 报道聚焦：{title}")
            
    if len(items) > 1:
        sources_list = ", ".join(sorted({it.get("source_id", "unknown") for it in items}))
        community_notes.append(f"本事件同时被多源关注报道 ({sources_list})，呈现跨界协同讨论趋势。")
        
    return key_breakthrough, tech_details, community_notes


class TopicFusionEngine:
    """跨源语义去重与主题聚类引擎"""
    
    def __init__(self, similarity_threshold: float = 0.45):
        self.similarity_threshold = similarity_threshold

    def cluster_items(self, items: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """将原始条目聚集为无冗余的主题团簇 (基于图连通分量/贪心聚合)"""
        if not items:
            return []
            
        n = len(items)
        # 并查集 (Union-Find)
        parent = list(range(n))
        
        def find(i: int) -> int:
            if parent[i] == i:
                return i
            parent[i] = find(parent[i])
            return parent[i]
            
        def union(i: int, j: int):
            root_i = find(i)
            root_j = find(j)
            if root_i != root_j:
                parent[root_i] = root_j

        # 两两比对计算语义相关度
        for i in range(n):
            for j in range(i + 1, n):
                related, score, reason = are_items_semantically_related(
                    items[i], items[j], sim_threshold=self.similarity_threshold
                )
                if related:
                    union(i, j)

        # 整理团簇
        clusters_map: Dict[int, List[Dict[str, Any]]] = {}
        for i in range(n):
            root = find(i)
            clusters_map.setdefault(root, []).append(items[i])
            
        return list(clusters_map.values())

    def fuse(self, raw_items: List[Dict[str, Any]], date_str: str | None = None) -> ConsolidatedDailyBrief:
        """执行完整聚类融合管线，产出结构化的高密度日报数据"""
        if not date_str:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
        clusters = self.cluster_items(raw_items)
        topic_clusters: List[TopicCluster] = []
        
        for cluster in clusters:
            # 确定主题标题：选择最长、最具描述力的标题
            primary_title = max([it.get("title", "") for it in cluster], key=lambda t: len(t.strip()))
            
            # 聚合所有实体
            all_text = "\n".join([f"{it.get('title', '')}\n{it.get('summary', '')}" for it in cluster])
            entities = extract_entities(all_text)
            
            # 聚合标签与信源
            tags = sorted({t for it in cluster for t in it.get("tags", []) if t})
            observed_sources = sorted({it.get("source_id", "unknown") for it in cluster})
            
            # 三层分层合成
            key_breakthrough, tech_details, community_disc = synthesize_cluster_layers(cluster)
            
            # 收集溯源引用
            citations: List[SourceCitation] = []
            seen_urls = set()
            for it in cluster:
                url = it.get("url")
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                citations.append(SourceCitation(
                    source_id=it.get("source_id", "unknown"),
                    title=it.get("title", "Untitled"),
                    url=url,
                    canonical_url=it.get("metadata", {}).get("canonical_url"),
                    snippet=it.get("summary", "")[:180],
                    published_at=it.get("freshness", {}).get("published_at")
                ))

            # 稳定主题 ID (基于实体与标题哈希)
            id_seed = f"{entities[:3]}_{primary_title[:30]}"
            topic_id = "topic_" + hashlib.sha256(id_seed.encode("utf-8")).hexdigest()[:12]

            category = categorize_topic(primary_title, tags, entities)

            topic_clusters.append(TopicCluster(
                topic_id=topic_id,
                topic_title=primary_title,
                primary_category=category,
                entities=entities[:10],
                key_breakthrough=key_breakthrough,
                technical_details=tech_details,
                community_discussion=community_disc,
                observed_sources=observed_sources,
                citations=citations,
                tags=tags,
                raw_item_count=len(cluster)
            ))

        total_raw = len(raw_items)
        total_fused = len(topic_clusters)
        reduction = ((total_raw - total_fused) / total_raw * 100) if total_raw > 0 else 0.0
        
        return ConsolidatedDailyBrief(
            date=date_str,
            total_raw_items=total_raw,
            total_topics=total_fused,
            compression_ratio=f"{reduction:.1f}% 去重与聚合",
            topics=topic_clusters
        )

    def render_markdown(self, brief: ConsolidatedDailyBrief) -> str:
        """将结构化高密度简报渲染为适合 NotebookLM 和阅读的优雅 Markdown"""
        lines = [
            f"# 每日情报高密度聚类总报 ({brief.date})",
            "",
            "> **跨源语义融合层产出**：通过实体识别与语义相似度网络，合并 ArXiv、GitHub、News 等多源重复采集，提炼高密度深度情报。",
            "",
            f"- **原始情报输入**: {brief.total_raw_items} 条",
            f"- **融合深度主题**: {brief.total_topics} 项",
            f"- **去重降噪压缩率**: {brief.compression_ratio}",
            f"- **生成时间**: `{brief.generated_at}`",
            "",
            "---",
            ""
        ]
        
        # 按分类对主题进行分组
        by_category: Dict[str, List[TopicCluster]] = {}
        for top in brief.topics:
            by_category.setdefault(top.primary_category, []).append(top)
            
        for cat, topics in by_category.items():
            lines.append(f"## 📌 领域板块：{cat}")
            lines.append("")
            
            for t in topics:
                cross_source_badge = f" [多源交叉验证: {', '.join(t.observed_sources)}]" if len(t.observed_sources) > 1 else f" [{t.observed_sources[0]}]"
                lines.append(f"### 🔥 {t.topic_title}{cross_source_badge}")
                if t.entities:
                    lines.append(f"**核心实体**: `{ '` · `'.join(t.entities) }`")
                lines.append("")
                
                # 1. 关键突破
                lines.append(f"**💡 【关键突破】**: {t.key_breakthrough}")
                lines.append("")
                
                # 2. 技术细节
                if t.technical_details:
                    lines.append("**⚙️ 【技术细节与架构】**:")
                    for td in t.technical_details:
                        lines.append(f"- {td}")
                    lines.append("")
                    
                # 3. 社区与产业讨论
                if t.community_discussion:
                    lines.append("**💬 【社区反响与产业影响】**:")
                    for cd in t.community_discussion:
                        lines.append(f"- {cd}")
                    lines.append("")
                    
                # 溯源清单
                if t.citations:
                    lines.append("**🔗 溯源凭据与原文链接**:")
                    for cit in t.citations:
                        url_str = f"({cit.url})" if cit.url else ""
                        lines.append(f"  - [{cit.source_id}] {cit.title} {url_str}")
                    lines.append("")
                    
                lines.append("---")
                lines.append("")
                
        return "\n".join(lines)
