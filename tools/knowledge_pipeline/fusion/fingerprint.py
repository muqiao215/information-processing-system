"""
语义指纹提取与相似度计算 (Semantic Fingerprinting & Entity Matcher)
纯 Python 标准库实现，零笨重依赖，极速稳定。
"""
from __future__ import annotations

import re
import math
import hashlib
from typing import Any, Set, List, Dict
from collections import Counter
from urllib.parse import urlparse


# 常见科技/开源实体正则模式 (模型名、框架、工具、GitHub 仓库等)
ENTITY_PATTERNS = [
    # 显式 GitHub 仓库路径 (如 github.com/meta-llama/llama3)
    re.compile(r'(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_\-\.]+/[a-zA-Z0-9_\-\.]+)'),
    # 独立 GitHub 仓库格式 (如 meta-llama/llama3, vllm-project/vllm)
    re.compile(r'(?<![a-zA-Z0-9_\-\./])([a-zA-Z0-9_\-\.]+/[a-zA-Z0-9_\-\.]+)(?![a-zA-Z0-9_\-\./])'),
    # 典型 AI 模型命名 (如 Llama-3, GPT-4o, Claude-3.5, DeepSeek-V3, Qwen-2.5, SDXL, Mistral-7B)
    re.compile(r'\b([A-Z][a-zA-Z0-9]*(?:[-_][a-zA-Z0-9\.]+)+)\b'),
    # ArXiv ID (如 2404.12345)
    re.compile(r'\b(\d{4}\.\d{4,5}(?:v\d+)?)\b'),
    # 首字母大写的代表性技术专有名词 (如 Transformer, LoRA, MoE, LangChain, Kubernetes)
    re.compile(r'\b([A-Z][a-z]{2,}(?:[A-Z][a-z]+)+)\b'),
    # 大写首字母缩写 (如 RAG, Agent, LLM, MLLM, RLHF, DPO, MCP)
    re.compile(r'\b([A-Z]{3,6})\b'),
]

# 常见停用词 (用于纯文本相似度过滤)
STOP_WORDS: Set[str] = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with", "by", "from",
    "is", "are", "was", "were", "be", "been", "have", "has", "had", "do", "does", "did",
    "can", "could", "will", "would", "should", "of", "it", "this", "that", "these", "those",
    "i", "you", "he", "she", "we", "they", "its", "our", "their", "new", "using", "based",
    "via", "into", "about", "more", "how", "what", "which", "who", "when", "where", "why",
    "的", "了", "和", "是", "就", "都", "而", "及", "与", "着", "或", "一个", "没有", "我们",
    "你们", "他们", "基于", "使用", "通过", "进行", "对于", "关于"
}


def extract_entities(text: str) -> List[str]:
    """从标题和正文中抽取高判别度实体与专有名词"""
    if not text:
        return []
    
    found: Set[str] = set()
    for pattern in ENTITY_PATTERNS:
        matches = pattern.findall(text)
        for m in matches:
            cleaned = m.strip("._-/")
            # 排除常见通用词
            if len(cleaned) >= 3 and cleaned.lower() not in STOP_WORDS:
                found.add(cleaned)
                
    return sorted(found)


def tokenize_text(text: str) -> List[str]:
    """混合分词：支持中文字元 2-gram 与英文单词"""
    if not text:
        return []
        
    text_lower = text.lower()
    # 提取英文字词
    en_words = re.findall(r'[a-z0-9_\-\.]+', text_lower)
    tokens = [w for w in en_words if len(w) > 1 and w not in STOP_WORDS]
    
    # 提取中文字符串并生成 2-gram
    cjk_text = "".join(re.findall(r'[\u4e00-\u9fff]', text_lower))
    for i in range(len(cjk_text) - 1):
        bigram = cjk_text[i:i+2]
        if bigram not in STOP_WORDS:
            tokens.append(bigram)
            
    return tokens


def compute_tf_vector(tokens: List[str]) -> Dict[str, float]:
    """计算词频向量并进行 L2 归一化"""
    counts = Counter(tokens)
    total = len(tokens)
    if total == 0:
        return {}
    
    vector = {k: v / total for k, v in counts.items()}
    norm = math.sqrt(sum(v * v for v in vector.values()))
    if norm > 0:
        return {k: v / norm for k, v in vector.items()}
    return vector


def cosine_similarity(v1: Dict[str, float], v2: Dict[str, float]) -> float:
    """计算两个稀疏向量的余弦相似度"""
    if not v1 or not v2:
        return 0.0
    common = set(v1.keys()) & set(v2.keys())
    return sum(v1[k] * v2[k] for k in common)


def extract_url_key(url: str | None) -> str:
    """提取 URL 中的核心资产身份 (如 github.com/owner/repo 或 arxiv.org/abs/xxx)"""
    if not url:
        return ""
    parsed = urlparse(url.lower().strip())
    netloc = parsed.netloc
    path = parsed.path.strip("/")
    
    if "github.com" in netloc:
        parts = path.split("/")
        if len(parts) >= 2:
            return f"github::{parts[0]}/{parts[1]}"
    elif "arxiv.org" in netloc:
        parts = path.split("/")
        if parts:
            return f"arxiv::{parts[-1]}"
    return f"{netloc}/{path}"


def are_items_semantically_related(
    item1: Dict[str, Any],
    item2: Dict[str, Any],
    sim_threshold: float = 0.45
) -> tuple[bool, float, str]:
    """
    多重判据综合评估两则信息是否属于同一突发事件/开源主题/技术发布：
    1. 强判据：指向相同 GitHub 仓库或同一 arXiv 论文
    2. 实体判据：存在 2 个以上相同专有实体 (如同一模型代号、项目名)
    3. 语义判据：标题与摘要文本 TF-IDF 余弦相似度高于阈值
    """
    # 1. 强判据：URL 核心身份
    url1_key = extract_url_key(item1.get("url"))
    url2_key = extract_url_key(item2.get("url"))
    if url1_key and url2_key and url1_key == url2_key:
        return True, 1.0, f"shared_asset_key:{url1_key}"
        
    t1 = item1.get("title", "")
    t2 = item2.get("title", "")
    s1 = item1.get("summary", "") or item1.get("raw_text", "")
    s2 = item2.get("summary", "") or item2.get("raw_text", "")
    
    text1 = f"{t1}\n{s1}"
    text2 = f"{t2}\n{s2}"
    
    # 2. 实体判据
    e1 = set(extract_entities(text1))
    e2 = set(extract_entities(text2))
    shared_entities = e1 & e2
    # 过滤掉过于宽泛的缩写词
    meaningful_shared = {e for e in shared_entities if len(e) > 3 or e in {"MoE", "LoRA", "MCP", "RL"}}
    
    if len(meaningful_shared) >= 2:
        return True, 0.85, f"shared_entities:{','.join(meaningful_shared)}"
    
    # 若仅有一个非常独特的长实体（如 "deepseek-v3" 或 "llama-3.3-70b"）
    for ent in meaningful_shared:
        if ("-" in ent or "_" in ent) and len(ent) >= 6:
            # 标题必须同时提及或语义有一定相关
            tokens1 = tokenize_text(t1)
            tokens2 = tokenize_text(t2)
            if cosine_similarity(compute_tf_vector(tokens1), compute_tf_vector(tokens2)) > 0.2:
                return True, 0.75, f"unique_entity:{ent}"

    # 3. 标题与正文语义相似度
    title_tokens1 = tokenize_text(t1)
    title_tokens2 = tokenize_text(t2)
    title_sim = cosine_similarity(compute_tf_vector(title_tokens1), compute_tf_vector(title_tokens2))
    
    # 标题极其相似（>= 0.65）
    if title_sim >= 0.65:
        return True, title_sim, "high_title_similarity"

    full_tokens1 = tokenize_text(text1)
    full_tokens2 = tokenize_text(text2)
    full_sim = cosine_similarity(compute_tf_vector(full_tokens1), compute_tf_vector(full_tokens2))
    
    combined_score = 0.6 * title_sim + 0.4 * full_sim
    if combined_score >= sim_threshold:
        return True, combined_score, f"semantic_score:{combined_score:.2f}"
        
    return False, combined_score, "dissimilar"
