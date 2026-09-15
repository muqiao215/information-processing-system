"""
CLI 命令行入口：运行跨源语义去重与主题聚类融合
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.knowledge_pipeline.fusion.engine import TopicFusionEngine
from tools.knowledge_pipeline.fs_utils import atomic_write_text


def resolve_workspace_root(repo_root: Path) -> Path:
    if repo_root.parent.name == "repos":
        return repo_root.parent.parent
    return repo_root.parent


WORKSPACE = Path(os.environ.get("WORKSPACE_ROOT", resolve_workspace_root(REPO_ROOT)))
DEFAULT_INPUT = WORKSPACE / "output_to_user" / "knowledge_pack_latest.json"
DEFAULT_OUTPUT_JSON = WORKSPACE / "output_to_user" / "consolidated_daily_brief.json"
DEFAULT_OUTPUT_MD = WORKSPACE / "output_to_user" / "consolidated_daily_brief.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Cross-Source Semantic Deduplication & Topic Fusion Engine."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to input knowledge_pack JSON or raw items manifest.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=DEFAULT_OUTPUT_JSON,
        help="Path to output consolidated_daily_brief.json.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=DEFAULT_OUTPUT_MD,
        help="Path to output consolidated_daily_brief.md.",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.45,
        help="Semantic similarity threshold for clustering (default: 0.45).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    
    if not args.input.exists():
        print(f"[fusion][error] 输入文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)
        
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # 支持直接输入 knowledge_pack (包含 .items 数组) 或纯数组
    if isinstance(data, dict) and "items" in data:
        items = data["items"]
    elif isinstance(data, list):
        items = data
    else:
        print("[fusion][error] 输入 JSON 格式不识别（需包含 items 列表或直接为列表）", file=sys.stderr)
        sys.exit(1)
        
    print(f"[fusion] 读取输入条目: {len(items)} 条，正在启动语义去重与主题聚类融合...")
    engine = TopicFusionEngine(similarity_threshold=args.similarity_threshold)
    brief = engine.fuse(items)
    
    # 写入 JSON
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    brief_json_str = brief.to_json(indent=2)
    atomic_write_text(args.output_json, brief_json_str)
    print(f"[fusion] 结构化简报已生成: {args.output_json}")
    
    # 写入 Markdown
    brief_md_str = engine.render_markdown(brief)
    atomic_write_text(args.output_md, brief_md_str)
    print(f"[fusion] Markdown 简报已生成: {args.output_md}")
    print(f"[fusion] 原始条目: {brief.total_raw_items} -> 融合主题: {brief.total_topics} (压缩降噪率: {brief.compression_ratio})")


if __name__ == "__main__":
    main()
