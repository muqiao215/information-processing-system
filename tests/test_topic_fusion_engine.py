"""
Unit tests for the Cross-Source Semantic Deduplication & Topic Fusion Engine
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from tools.knowledge_pipeline.fusion.fingerprint import (
    extract_entities,
    are_items_semantically_related,
    tokenize_text,
    cosine_similarity,
    compute_tf_vector,
)
from tools.knowledge_pipeline.fusion.engine import (
    TopicFusionEngine,
    categorize_topic,
    synthesize_cluster_layers,
)
from tools.knowledge_pipeline.fusion.models import (
    ConsolidatedDailyBrief,
    TopicCluster,
)


def test_extract_entities():
    sample = "Meta released Llama-3.3-70B on github.com/meta-llama/llama3 and published arXiv 2404.12345 using LoRA."
    entities = extract_entities(sample)
    
    assert any("meta-llama/llama3" in e for e in entities)
    assert any("Llama-3.3-70B" in e for e in entities)
    assert any("2404.12345" in e for e in entities)


def test_semantic_relatedness_shared_github():
    item1 = {
        "title": "vLLM: Easy, fast, and cheap LLM serving for everyone",
        "url": "https://github.com/vllm-project/vllm",
        "summary": "High-throughput and memory-efficient LLM serving engine using PagedAttention."
    }
    item2 = {
        "title": "Discussion: Why vLLM PagedAttention changed open source serving",
        "url": "https://github.com/vllm-project/vllm/releases/tag/v0.6.0",
        "summary": "Benchmarking vLLM against TGI and TensorRT-LLM."
    }
    related, score, reason = are_items_semantically_related(item1, item2)
    assert related is True
    assert "github::vllm-project/vllm" in reason


def test_semantic_relatedness_cross_source_same_subject():
    # ArXiv paper
    paper = {
        "source_id": "arxiv-llm-memory",
        "title": "DeepSeek-V3 Technical Report: Multi-head Latent Attention and DeepSeekMoE Architecture",
        "url": "https://arxiv.org/abs/2412.19437",
        "summary": "We present DeepSeek-V3, a strong Mixture-of-Experts (MoE) language model with 671B total parameters."
    }
    # News / Hacker News item about the exact same model
    news = {
        "source_id": "newsnow-ai",
        "title": "DeepSeek-V3 open sourced with 671B MoE model and incredible cost efficiency",
        "url": "https://news.ycombinator.com/item?id=123456",
        "summary": "DeepSeek has officially open sourced DeepSeek-V3, sparking massive community discussion on Multi-head Latent Attention."
    }
    related, score, reason = are_items_semantically_related(paper, news)
    assert related is True
    assert score > 0.5


def test_dissimilar_items_not_clustered():
    robot_arm = {
        "title": "SO-ARM100: Standard Open Arm 100 Desktop Robot",
        "url": "https://github.com/TheRobotStudio/SO-ARM100",
        "summary": "3D printed robot arm with Feetech STS3215 servos."
    }
    nlp_paper = {
        "title": "Self-Rewarding Language Models with DPO Optimization",
        "url": "https://arxiv.org/abs/2401.10020",
        "summary": "We train language models to provide their own rewards during RLHF."
    }
    related, score, reason = are_items_semantically_related(robot_arm, nlp_paper)
    assert related is False


def test_topic_fusion_engine_flow():
    items = [
        {
            "source_id": "arxiv-llm-memory",
            "title": "DeepSeek-V3 Technical Report: Architecture & Benchmarks",
            "url": "https://arxiv.org/abs/2412.19437",
            "summary": "Detailed technical report on DeepSeek-V3 with FP8 mixed precision training.",
            "tags": ["moe", "deepseek"]
        },
        {
            "source_id": "builderpulse",
            "title": "deepseek-ai/DeepSeek-V3 official GitHub repository",
            "url": "https://github.com/deepseek-ai/DeepSeek-V3",
            "summary": "Inference code and checkpoints for DeepSeek-V3 671B MoE.",
            "tags": ["github", "opensource"]
        },
        {
            "source_id": "newsnow-ai",
            "title": "DeepSeek-V3 takes AI world by storm with shocking cost numbers",
            "url": "https://example.com/news/deepseek-v3-shock",
            "summary": "The global AI community reacts to DeepSeek-V3 training budget under $6 million.",
            "selected_reason": "High viral score on Twitter/X.",
            "tags": ["trending", "news"]
        },
        {
            "source_id": "builderpulse",
            "title": "SO-ARM100 3D Printed Robot Arm",
            "url": "https://github.com/TheRobotStudio/SO-ARM100",
            "summary": "Standard Open Arm 100 hardware files.",
            "tags": ["robotics"]
        }
    ]
    
    engine = TopicFusionEngine(similarity_threshold=0.45)
    brief = engine.fuse(items, date_str="2026-09-15")
    
    assert brief.total_raw_items == 4
    # DeepSeek 3 items should be clustered into 1, SO-ARM100 is 1 -> total 2 topics
    assert brief.total_topics == 2
    
    deepseek_topic = next((t for t in brief.topics if "DeepSeek" in t.topic_title), None)
    assert deepseek_topic is not None
    assert len(deepseek_topic.observed_sources) >= 2
    assert len(deepseek_topic.citations) == 3
    assert len(deepseek_topic.technical_details) >= 1
    assert len(deepseek_topic.community_discussion) >= 1
    
    # Check Markdown rendering
    md = engine.render_markdown(brief)
    assert "# 每日情报高密度聚类总报 (2026-09-15)" in md
    assert "【关键突破】" in md
    assert "【技术细节与架构】" in md
    assert "【社区反响与产业影响】" in md
