# Technical Design: Article Tag Extraction & Graph Matching

> Deep research covering the core matching algorithm: Article → Tags → Graph → User Relevance

**Created**: 2026-03-09
**Status**: Research Complete — Ready for Implementation

---

## Table of Contents

1. [Tag Extraction Strategy (Step 2)](#1-tag-extraction-strategy)
2. [Prompt Engineering for Tag Extraction](#2-prompt-engineering)
3. [Handling the 1,110 Node Vocabulary](#3-handling-the-vocabulary)
4. [Embedding-Based Matching](#4-embedding-based-matching)
5. [Handling Indirect/Implicit Effects](#5-indirect-effects)
6. [Graph Traversal Algorithms (Step 3)](#6-graph-traversal)
7. [Scoring the Match](#7-scoring)
8. [Performance at Scale](#8-performance)
9. [Dealing with Noise](#9-noise-reduction)
10. [Existing Systems to Study](#10-existing-systems)
11. [Final Architecture Recommendation](#11-final-architecture)

---

## 1. Tag Extraction Strategy

### The Core Question: Open vs Closed Vocabulary

There are three viable approaches. Research strongly favors **Option C: Hybrid**.

#### Option A: Open Vocabulary (Free-form tags → fuzzy match)

```
Article → LLM extracts free-form tags → fuzzy match against graph node aliases
```

**Pros:**
- Handles novel concepts not in your graph
- Simpler prompt (no vocabulary to include)
- LLM operates in its strongest mode (free generation)

**Cons:**
- Fuzzy matching is lossy — "Indian IT industry" might not match "it_services_sector"
- Requires maintaining a robust alias index
- Many false negatives from vocabulary mismatch

**When it works:** When the graph vocabulary is small or when you expect many out-of-vocabulary concepts.

#### Option B: Closed Vocabulary (Give LLM the full node list)

```
Article → LLM selects from provided node IDs → exact match against graph
```

**Pros:**
- Zero vocabulary mismatch — perfect precision
- LLM constrained decoding can enforce valid IDs only
- No fuzzy matching layer needed

**Cons:**
- 1,110 nodes × ~4 aliases each = ~15K-20K tokens just for the vocabulary (see Section 3)
- LLM accuracy degrades with large label spaces (research shows >50% accuracy drop beyond 200 classes in a single prompt)
- Can't detect concepts not in the graph
- Expensive — every article pays the full vocabulary token cost

**When it works:** When vocabulary is <200 nodes and context window is not a concern.

#### Option C: Hybrid Two-Stage (RECOMMENDED)

```
Stage 1: Article → LLM extracts open tags + identifies domain(s)
Stage 2: Open tags → embedding similarity match against graph nodes
Stage 2b (optional): Top-K candidates → LLM confirms/rejects
```

**Why this wins:**
- Stage 1 is cheap (no vocabulary in prompt) and handles novel concepts
- Stage 2 uses embeddings for high-recall retrieval against all 1,110 nodes
- Optional Stage 2b uses LLM for precision on borderline matches
- Naturally handles out-of-vocabulary concepts (Stage 1 flags them)
- Aligns with Mercari's proven approach: they solved categorization of billions of items into 1,000+ categories using exactly this pattern

**Research backing:**
- Mercari Engineering (2024): Two-stage pipeline for large-scale categorization — embedding retrieval + LLM refinement
- TELEClass (ACL 2024): Taxonomy enrichment + LLM-enhanced hierarchical classification
- HierLabelNet (2025): Two-stage LLM framework with data augmentation and label selection

### Recommendation

**Use the Hybrid Two-Stage approach.** Specifically:

```python
# Stage 1: Open extraction (cheap, ~200 tokens output)
stage1_result = llm_extract_tags(article_text)
# Returns: { "tags": ["El Nino", "monsoon forecast", "Indian agriculture"],
#            "domains": ["climate", "food"],
#            "entities": ["IMD", "India"],
#            "is_novel": false }

# Stage 2: Embedding match (fast, local, no LLM cost)
candidates = embedding_match(
    query_texts=stage1_result["tags"],
    node_embeddings=precomputed_node_embeddings,
    top_k=20,
    threshold=0.65
)
# Returns: [("monsoon", 0.92), ("india_rice_production", 0.78), ...]

# Stage 2b (optional): LLM confirmation for borderline matches
if any(0.55 < score < 0.75 for _, score in candidates):
    confirmed = llm_confirm_matches(article_text, borderline_candidates)
```

---

## 2. Prompt Engineering for Tag Extraction

### Optimal Prompt Structure for Stage 1

The Stage 1 prompt must extract: (a) what topics the article covers, (b) what real-world things it affects, and (c) which domain(s) it falls into.

```
SYSTEM:
You are a news analyst. Given a news article, extract what real-world
things this article AFFECTS — not just what it mentions, but what will
change as a consequence.

Think step by step:
1. What is the core event?
2. What are the DIRECT effects? (1st order)
3. What are the INDIRECT effects? (2nd order, things not mentioned but affected)
4. What domains of daily life does this touch?

OUTPUT FORMAT (JSON):
{
  "core_event": "short description of what happened",
  "tags": ["list", "of", "affected", "concepts"],
  "indirect_tags": ["things", "not mentioned", "but affected"],
  "domains": ["food", "energy", "employment", "financial", "governance"],
  "entities": ["named entities: orgs, people, places"],
  "severity": "low|medium|high|critical"
}

USER:
HEADLINE: {headline}
SUMMARY: {summary}
SOURCE: {source}
```

### Key Prompt Design Decisions

**1. Chain-of-Thought for indirect effects:** The "think step by step" instruction is critical. Without it, LLMs extract only explicitly mentioned concepts. With CoT, they reason about 2nd-order effects (El Nino → monsoon → crops → food prices).

**2. Separate `tags` vs `indirect_tags`:** This separation lets you weight them differently in scoring. Direct tags get higher confidence (0.9), indirect tags get lower (0.6).

**3. Domain list as enum:** Providing the exact domain names (`food`, `energy`, `employment`, `financial`, `governance`) as a closed set for the `domains` field. This is a tiny closed vocabulary (5 values) that LLMs handle perfectly, and it enables Stage 2 domain filtering.

**4. Few-shot examples — YES, use them:** Research consistently shows 3-5 examples improve classification accuracy by 15-25%. Include examples covering:
- Direct effect article (RBI rate hike → EMI increase)
- Indirect effect article (El Nino → food prices)
- Multi-domain article (war → energy + food + finance)
- Non-impactful article (celebrity gossip → empty tags)

### Few-Shot Example Template

```json
EXAMPLE 1:
HEADLINE: "OPEC+ agrees to cut oil production by 2 million barrels per day"
{
  "core_event": "OPEC+ production cut of 2M bpd",
  "tags": ["crude oil", "OPEC", "oil production", "oil prices"],
  "indirect_tags": ["petrol prices", "diesel prices", "transport costs",
                     "food logistics", "aviation fuel", "inflation"],
  "domains": ["energy", "food", "financial"],
  "entities": ["OPEC", "Saudi Arabia"],
  "severity": "high"
}

EXAMPLE 2:
HEADLINE: "IMD confirms El Nino conditions likely to persist through 2026 monsoon"
{
  "core_event": "El Nino expected during 2026 Indian monsoon season",
  "tags": ["El Nino", "monsoon", "Indian monsoon forecast"],
  "indirect_tags": ["kharif crops", "rice production", "food inflation",
                     "hydropower generation", "water scarcity", "reservoir levels",
                     "groundwater", "rural employment"],
  "domains": ["food", "energy", "governance"],
  "entities": ["IMD", "India"],
  "severity": "high"
}
```

### Two-Call vs Single-Call

**Single call is sufficient for Stage 1.** The CoT prompt with few-shot examples handles both "what does this cover" and "what does this affect" in one pass. A two-call approach (first extract topics, then map to effects) adds latency and cost without meaningful accuracy gain — the LLM already reasons about effects when given the CoT instruction.

**Exception:** For novel/complex events where Stage 1 flags high uncertainty, a second call with more reasoning budget (Claude Sonnet instead of Gemini Flash) is justified.

### Model Selection for Stage 1

| Model | Cost/1M tokens | Latency | Quality | Recommendation |
|-------|----------------|---------|---------|----------------|
| Gemini 2.0 Flash | $0.10 in / $0.40 out | ~300ms | Good for direct effects, weaker on indirect | **Primary (90% of articles)** |
| GPT-4o-mini | $0.15 in / $0.60 out | ~400ms | Slightly better on indirect effects | Fallback |
| Claude Haiku | $0.25 in / $1.25 out | ~350ms | Good structured output | Alternative |
| Claude Sonnet | $3.00 in / $15.00 out | ~800ms | Best for complex/novel events | **Escalation only** |

**Cost estimate:** 200 articles/day × ~800 tokens/article × Gemini Flash = ~$0.05/day for Stage 1.

---

## 3. Handling the 1,110 Node Vocabulary

### Token Count Estimate

Actual measurement from your graph files:
- **1,110 nodes** across 4 domain graphs
- Each node: `id` (~15 chars) + 3-5 aliases (~60 chars) = ~75 chars average
- 75 chars × 1,110 nodes = ~83,250 characters
- At ~4 chars/token: **~20,800 tokens** for the full vocabulary

For context window fit:
- Gemini Flash: 1M tokens — **fits easily** (2% of context)
- GPT-4o-mini: 128K tokens — **fits** (16% of context)
- Claude Haiku: 200K tokens — **fits** (10% of context)

**Verdict: The full vocabulary CAN fit in a single prompt.** But fitting is not the same as performing well.

### Why Full Vocabulary in Prompt is Still a Bad Idea

Research on LLM classification with large label spaces shows:

1. **Accuracy degrades at scale:** Benchmarks show LLMs struggle to reliably select from >200 options in a single prompt. At 1,000+ labels, accuracy drops 40-60% compared to smaller label sets.

2. **Positional bias:** Labels appearing early/late in the list get disproportionate selection. With 1,110 nodes, this effect is severe.

3. **Cost:** Even if quality were fine, paying ~20K input tokens per article (×200 articles/day) = 4M extra tokens/day = $0.40/day on Flash. Small, but wasteful.

4. **Latency:** 20K extra tokens adds ~200ms processing time per article.

### Recommended: Domain-Filtered Vocabulary

Since Stage 1 already extracts `domains`, use this to filter:

```python
# Stage 1 returns domains: ["food", "energy"]
# Filter vocabulary to those domains only
domain_categories = {
    "food": ["food", "food_policy"],
    "energy": ["energy", "energy_policy"],
    "employment": ["employment", "labor"],
    "financial": ["financial", "monetary", "banking"],
    "governance": ["governance", "regulation", "infrastructure"]
}

relevant_categories = []
for domain in stage1_result["domains"]:
    relevant_categories.extend(domain_categories[domain])

filtered_nodes = [n for n in all_nodes if n.category in relevant_categories]
# "food" + "energy" domains → ~322 nodes (from food_energy_graph.yaml)
# Much more manageable for embedding search
```

### But Don't Use LLM for This Filtering — Use Embeddings

The domain filter narrows the embedding search space. The LLM never needs to see the vocabulary at all. This is why the hybrid approach wins:

```
Article → LLM (no vocabulary, just extract tags) → Embeddings (search against filtered nodes) → Matches
```

---

## 4. Embedding-Based Matching

### Architecture

Pre-embed all 1,110 node aliases into a vector index. At query time, embed the extracted tags and find nearest neighbors.

```python
# ONE-TIME: Build the embedding index
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer('all-MiniLM-L6-v2')  # 384-dim, fast, free

# For each node, embed all aliases
node_embeddings = {}
for node in all_nodes:
    texts = [node.id.replace("_", " ")] + node.aliases
    embeddings = model.encode(texts)
    # Store mean embedding as the node's canonical vector
    node_embeddings[node.id] = {
        "mean": np.mean(embeddings, axis=0),
        "all": embeddings,  # Keep individual alias embeddings for max-similarity
        "texts": texts
    }

# Build FAISS index for fast search
import faiss
dim = 384
index = faiss.IndexFlatIP(dim)  # Inner product (cosine sim on normalized vectors)
node_ids = []
vectors = []
for nid, data in node_embeddings.items():
    for vec in data["all"]:
        vec_norm = vec / np.linalg.norm(vec)
        vectors.append(vec_norm)
        node_ids.append(nid)

index.add(np.array(vectors).astype('float32'))
```

```python
# PER-ARTICLE: Match extracted tags against node index
def match_tags_to_nodes(tags: list[str], top_k: int = 20, threshold: float = 0.60):
    tag_embeddings = model.encode(tags)

    results = {}
    for tag, tag_emb in zip(tags, tag_embeddings):
        tag_emb_norm = tag_emb / np.linalg.norm(tag_emb)
        scores, indices = index.search(
            tag_emb_norm.reshape(1, -1).astype('float32'),
            top_k
        )

        for score, idx in zip(scores[0], indices[0]):
            if score >= threshold:
                nid = node_ids[idx]
                if nid not in results or score > results[nid]:
                    results[nid] = float(score)

    return sorted(results.items(), key=lambda x: -x[1])
```

### Model Selection for Embeddings

| Model | Dimensions | Speed | Quality | Size |
|-------|-----------|-------|---------|------|
| all-MiniLM-L6-v2 | 384 | ~14K sent/sec | Good | 80MB |
| all-mpnet-base-v2 | 768 | ~2.5K sent/sec | Better | 420MB |
| BAAI/bge-small-en-v1.5 | 384 | ~14K sent/sec | Very Good | 130MB |
| text-embedding-3-small (OpenAI) | 1536 | API | Best | API |

**Recommendation:** `BAAI/bge-small-en-v1.5` — best quality-to-speed ratio for local inference. Free, 384-dim, fast enough for real-time.

### Threshold Calibration

The cosine similarity threshold is critical. Too low → noise. Too high → missed matches.

**Recommended starting thresholds:**
- `>= 0.80`: High confidence match → auto-accept
- `0.65 - 0.80`: Medium confidence → accept, but lower weight in scoring
- `0.50 - 0.65`: Low confidence → only accept if LLM Stage 2b confirms
- `< 0.50`: Reject

**Calibrate empirically:** Run 100 articles through the pipeline, manually label the matches, compute precision/recall at each threshold, adjust.

### Pros/Cons vs Pure LLM Extraction

| Dimension | Embedding Match | LLM Selection | Hybrid |
|-----------|----------------|---------------|--------|
| Speed | ~5ms for 1,110 nodes | ~500ms+ | ~305ms |
| Cost | $0 (local) | $0.01-0.05/article | $0.005/article |
| Recall | High (catches fuzzy matches) | Medium (misses at scale) | Highest |
| Precision | Medium (semantic noise) | High (understands context) | Highest |
| Novel concepts | Cannot detect | Detects naturally | Detects via Stage 1 |
| Scales to 10K nodes | Yes (FAISS is O(1) amortized) | No (context window) | Yes |

**The hybrid approach gives the best recall AND precision at the lowest cost.**

---

## 5. Handling Indirect/Implicit Effects

### The Problem

"El Nino confirmed for 2026" does not mention: monsoon, crops, hydropower, water, food prices. But all are affected.

### Three-Layer Solution

#### Layer 1: LLM Chain-of-Thought (Stage 1)

The CoT prompt already handles this for well-known causal chains. With the right few-shot examples, Gemini Flash reliably extracts:
- El Nino → monsoon → crops → food prices
- Hormuz blockade → oil supply → fuel prices → transport costs

**Limitation:** LLMs are unreliable beyond 3 hops and miss domain-specific chains.

#### Layer 2: Graph Edge Traversal (the real power)

This is where your pre-built causal graph shines. Once the embedding matcher identifies `el_nino` or `monsoon` as a matched node, you traverse outgoing edges:

```python
def get_affected_nodes(matched_node_id: str, max_hops: int = 3):
    """BFS traversal from matched node through causal edges."""
    visited = set()
    queue = [(matched_node_id, 0, 1.0)]  # (node, hops, cumulative_strength)
    affected = []

    while queue:
        node_id, hops, strength = queue.pop(0)
        if node_id in visited or hops > max_hops:
            continue
        visited.add(node_id)

        if hops > 0:  # Don't include the seed node itself
            affected.append((node_id, hops, strength))

        for edge in get_outgoing_edges(node_id):
            new_strength = strength * edge.strength  # Multiplicative decay
            if new_strength > 0.1:  # Prune weak paths
                queue.append((edge.target, hops + 1, new_strength))

    return affected
```

Example traversal from `monsoon` in your food_energy_graph:
```
monsoon → [AFFECTS] → india_rice_production (hop 1, strength 0.9)
monsoon → [AFFECTS] → india_wheat_production (hop 1, strength 0.8)
india_rice_production → [PRODUCES] → rice (hop 2, strength 0.81)
india_rice_production → [PRODUCES] → basmati_rice (hop 3, strength 0.73)
rice → [AFFECTS] → food_inflation (hop 3, strength 0.65)
```

**This is the key insight:** The LLM doesn't need to reason about 4-hop causal chains. It just needs to match the trigger concept. The pre-built graph handles the propagation.

#### Layer 3: Causal Templates (from Master Plan)

For known high-impact patterns, pre-built templates fire deterministically:

```python
# If Stage 1 classifies article as matching template "monsoon_failure"
template = load_template("monsoon_failure")
for chain in template.causal_chains:
    # Deterministic: monsoon_failure → crop_loss → food_inflation → ...
    activate_chain(chain, article_probability, article_magnitude)
```

### Handling True Novel Concepts

When Stage 1 extracts a tag that doesn't match any graph node:

1. **Log it** — track unmatched tags for graph expansion
2. **LLM fallback** — ask a stronger model: "Given this concept X, which of these 5 domains does it affect?" Then traverse from domain root nodes
3. **Don't discard** — store the article with its unmatched tags for periodic review

```python
unmatched_tags = [tag for tag in stage1_tags if tag not in matched_nodes]
if unmatched_tags:
    log_novel_concepts(article_id, unmatched_tags)
    # Optionally: broader domain-level matching
    for tag in unmatched_tags:
        domain = classify_tag_domain(tag)  # Simple LLM call
        root_nodes = get_domain_roots(domain)
        # Add weak connections from article to domain roots
```

---

## 6. Graph Traversal Algorithms (Step 3)

### Problem Statement

Given: article matches nodes `{A, B, C}` in the graph.
Find: does any path exist from `{A, B, C}` to user's dependency nodes `{X, Y, Z}`?
Score: how relevant is this article to the user?

### Algorithm Comparison

| Algorithm | Best For | Time Complexity | Your Use Case |
|-----------|---------|-----------------|---------------|
| BFS | Shortest path, unweighted | O(V + E) | Good for hop counting |
| Bidirectional BFS | Finding any path quickly | O(b^{d/2}) | Best for "does path exist?" |
| Dijkstra | Weighted shortest path | O((V+E) log V) | If edge weights vary significantly |
| Personalized PageRank | Relevance scoring from seed set | O(V + E) per iteration | **Best for multi-seed scoring** |
| Spreading Activation | Simulates activation spreading | O(V + E) × iterations | Good, but PPR is more principled |

### Recommended: Precomputed Reachability + PPR for Scoring

#### Step 1: Precompute User Reachability Sets

For each user, precompute all nodes reachable within N hops of their dependency nodes:

```python
def precompute_user_reachability(user_dependencies: list[str], max_hops: int = 3):
    """
    BFS backward from user dependency nodes.
    Returns: {node_id: (min_hops_to_user, closest_user_node)}
    """
    reachable = {}
    queue = []

    for dep_node in user_dependencies:
        queue.append((dep_node, 0, dep_node))
        reachable[dep_node] = (0, dep_node)

    while queue:
        node_id, hops, origin = queue.pop(0)
        if hops >= max_hops:
            continue

        # Traverse INCOMING edges (reverse direction)
        for edge in get_incoming_edges(node_id):
            if edge.source not in reachable or reachable[edge.source][0] > hops + 1:
                reachable[edge.source] = (hops + 1, origin)
                queue.append((edge.source, hops + 1, origin))

    return reachable
```

**Storage:** ~1,110 nodes × 3 ints each = ~13KB per user. Trivial.

**Update frequency:** Only when user's life graph changes (rare — weekly/monthly).

#### Step 2: Fast Article Matching

```python
def score_article_for_user(matched_nodes: list[tuple[str, float]],
                            user_reachability: dict):
    """
    O(K) where K = number of matched nodes (typically 5-20).
    No graph traversal at query time!
    """
    impacts = []
    for node_id, match_confidence in matched_nodes:
        if node_id in user_reachability:
            hops, user_node = user_reachability[node_id]
            impacts.append({
                "node": node_id,
                "user_node": user_node,
                "hops": hops,
                "match_confidence": match_confidence,
                "hop_decay": HOP_DECAY[hops],  # e.g., [1.0, 0.8, 0.5, 0.25]
            })

    return impacts
```

**This is O(K) per article, not O(V+E).** The graph traversal is precomputed.

#### Step 3: PPR for Nuanced Scoring (Optional Enhancement)

For more sophisticated scoring, use Personalized PageRank:

```python
import networkx as nx

def ppr_score(G: nx.DiGraph, seed_nodes: list[str], user_nodes: list[str]):
    """
    Run PPR with article-matched nodes as seeds.
    Check what probability mass lands on user nodes.
    """
    # Build personalization vector: uniform over seed nodes
    personalization = {n: 0.0 for n in G.nodes()}
    for seed in seed_nodes:
        if seed in G:
            personalization[seed] = 1.0 / len(seed_nodes)

    # Run PPR (alpha=0.85 means 15% chance of restart at each step)
    ppr = nx.pagerank(G, alpha=0.85, personalization=personalization)

    # Extract scores for user's dependency nodes
    user_scores = {n: ppr.get(n, 0.0) for n in user_nodes}
    return user_scores
```

**When to use PPR vs precomputed BFS:**
- **Precomputed BFS:** Fast, simple, good enough for MVP. Binary: reachable or not.
- **PPR:** Better scoring when multiple paths exist, considers graph structure globally. Use when you need to rank articles against each other.

### Maximum Hop Distance

Research and practical experience suggest:

| Hops | Confidence | Example |
|------|-----------|---------|
| 0 | Direct match to user node | "TCS quarterly results" → user works at TCS |
| 1 | Very high | "IT spending cuts" → TCS → user |
| 2 | High | "US recession" → IT spending → TCS |
| 3 | Medium | "Fed rate hike" → US recession → IT spending → TCS |
| 4+ | Low — diminishing returns | Too many competing pathways, noise dominates |

**Recommendation: Max 3 hops.** Beyond 3, the number of reachable nodes explodes and signal-to-noise degrades. Your causal templates already encode 4th-order effects where they're validated.

---

## 7. Scoring the Match

### Multi-Factor Scoring Formula

```python
def compute_relevance_score(impacts: list[dict], article_metadata: dict) -> float:
    """
    Aggregate multiple impact paths into a single relevance score.
    """
    if not impacts:
        return 0.0

    # Per-impact score
    impact_scores = []
    for imp in impacts:
        score = (
            imp["match_confidence"]    # How well did the tag match? (0-1)
            * imp["hop_decay"]         # Distance decay (0-1)
            * imp.get("edge_strength", 1.0)  # Edge confidence along path
            * imp.get("user_importance", 0.5) # How important is this to user? (0-1)
        )
        impact_scores.append(score)

    # Aggregation: don't just max — reward multiple impacts
    # Noisy-OR: P(relevant) = 1 - product(1 - p_i)
    noisy_or = 1.0 - np.prod([1.0 - s for s in impact_scores])

    # Article-level modifiers
    severity_mult = {"low": 0.5, "medium": 1.0, "high": 1.5, "critical": 2.0}
    article_severity = severity_mult.get(article_metadata.get("severity", "medium"), 1.0)

    # Source credibility
    source_trust = article_metadata.get("source_credibility", 0.8)

    final_score = noisy_or * article_severity * source_trust
    return min(final_score, 1.0)  # Cap at 1.0
```

### Why Noisy-OR Aggregation

When an article matches 5 different paths to the user, each with probability p_i of being relevant:
- **Max:** Only considers strongest path. Ignores that 5 weak signals together = strong signal.
- **Sum:** Unbounded, hard to normalize, double-counts.
- **Noisy-OR:** `P(relevant) = 1 - ∏(1 - p_i)`. Principled probabilistic combination. 5 paths at 0.3 each → 0.83 combined.

### Hop Decay Function

```python
# Option A: Exponential decay (aggressive, recommended for MVP)
HOP_DECAY = {0: 1.0, 1: 0.7, 2: 0.4, 3: 0.15}

# Option B: Linear decay (gentler)
HOP_DECAY = {0: 1.0, 1: 0.75, 2: 0.50, 3: 0.25}

# Option C: Calibrated from template confidence decay (from Master Plan)
HOP_DECAY = {0: 1.0, 1: 0.85, 2: 0.65, 3: 0.45}  # Matches your template data
```

**Recommendation:** Start with Option C (aligned with your template confidence decay values). Tune based on user feedback.

### Edge Type Weighting

Not all edge types carry equal causal strength:

```python
EDGE_TYPE_WEIGHTS = {
    "AFFECTS": 0.9,       # Strong causal: monsoon AFFECTS rice production
    "PRODUCES": 0.85,     # Direct: TCS PRODUCES IT services
    "DEPENDS_ON": 0.8,    # Dependency: IT sector DEPENDS_ON US clients
    "SUPPLIES": 0.75,     # Supply chain: fertilizer SUPPLIES rice production
    "REGULATES": 0.7,     # Regulatory: RBI REGULATES repo rate
    "DISRUPTS": 0.85,     # Disruption: war DISRUPTS shipping
    "COMPETES_WITH": 0.4, # Weaker: competitive effects are indirect
    "LOCATED_IN": 0.3,    # Geographic: weakest causal link
    "EMPLOYS": 0.6,       # Employment: moderate
    "FUNDS": 0.65,        # Funding: moderate
    "BENCHMARKED_TO": 0.7 # Financial benchmark: repo rate BENCHMARKED_TO policy
}
```

---

## 8. Performance at Scale

### Workload Analysis

```
200 articles/day × pipeline per article:
  Stage 1: LLM extraction       ~400ms, $0.0003
  Stage 2: Embedding match       ~5ms,   $0
  Graph match (precomputed):     ~0.1ms, $0
  Scoring:                       ~0.5ms, $0

Total per article: ~406ms, $0.0003
Total per day: ~81 seconds, $0.06
```

**This is trivially fast.** Even 10,000 articles/day would take 67 minutes and cost $3.

### Precomputed Reachability Sets

For each user, precompute:

```python
# Reachability set: all nodes within 3 hops of user's dependency nodes
# Your graph: 1,110 nodes, 1,771 edges
# Typical user has 20-50 dependency nodes
# 3-hop BFS from 50 nodes covers ~200-400 reachable nodes (graph is sparse)

# Storage: dict of {node_id: (min_hops, closest_user_node)}
# ~400 entries × ~50 bytes each = ~20KB per user
# 1,000 users = 20MB total. Fits in Redis easily.
```

**Update strategy:**
- Recompute when user's life graph changes (event-driven)
- Background recompute nightly (catch graph structure changes)
- Cache in Redis with TTL of 24 hours

### PostgreSQL vs SQLite vs In-Memory

For your graph size (1,110 nodes, 1,771 edges):

| Store | Graph Load Time | 3-hop BFS | Recommendation |
|-------|----------------|-----------|----------------|
| **In-memory (NetworkX)** | ~50ms (one-time) | <1ms | **Best for MVP** |
| SQLite + recursive CTE | N/A | ~5-20ms | Good for persistence |
| PostgreSQL + recursive CTE | N/A | ~10-50ms | Good for multi-user |
| Neo4j | N/A | ~5-15ms | Overkill at this scale |

**Recommendation for MVP:** Load the full graph into NetworkX at startup. It's only ~1,110 nodes and 1,771 edges — fits in <5MB of RAM. All traversals happen in microseconds.

```python
import networkx as nx
import yaml

def load_graph(yaml_files: list[str]) -> nx.DiGraph:
    G = nx.DiGraph()
    for fpath in yaml_files:
        data = yaml.safe_load(open(fpath))
        for node in data["nodes"]:
            G.add_node(node["id"], **{k: v for k, v in node.items() if k != "id"})
        for edge in data["edges"]:
            G.add_edge(edge["from"], edge["to"],
                      type=edge["type"],
                      description=edge.get("description", ""))
    return G

# At startup
G = load_graph([
    "taxonomy/food_energy_graph.yaml",
    "taxonomy/employment_domain_graph.yaml",
    "taxonomy/financial_system_domain_graph.yaml",
    "taxonomy/local_governance_graph.yaml"
])
# G.number_of_nodes() → 1110
# G.number_of_edges() → 1771
```

**Scale trigger:** Move to PostgreSQL when you need persistence across restarts, multi-process access, or >10,000 nodes. Move to Neo4j only at >100K nodes.

### Caching Strategy

```
Layer 1: In-memory graph (NetworkX) — always hot
Layer 2: User reachability sets (Redis) — TTL 24h, recompute on life graph change
Layer 3: Article → matched nodes cache (Redis) — TTL 7 days, dedup key = article URL hash
Layer 4: Article × user scores (Redis) — TTL 24h, invalidated on reachability change
```

---

## 9. Dealing with Noise

### Sources of False Positives

| Source | Example | Frequency | Severity |
|--------|---------|-----------|----------|
| Overly broad tag extraction | "India" matches everything | High | High |
| Embedding near-misses | "cricket bat" matches "bat (animal)" | Medium | Medium |
| Hub node pollution | "economy" connects to everything in graph | High | High |
| Stale edges | Outdated causal link still in graph | Low | Medium |
| LLM hallucinated tags | Extracting "famine" from mild shortage article | Low | High |

### Mitigation Strategies

#### 1. Stop-List for Overly Broad Tags

```python
BROAD_TAG_STOPLIST = {
    "India", "economy", "government", "market", "prices", "growth",
    "policy", "regulation", "industry", "sector", "global",
    "investment", "trade", "development", "technology"
}

def filter_tags(tags: list[str]) -> list[str]:
    return [t for t in tags if t.lower() not in BROAD_TAG_STOPLIST]
```

#### 2. Hub Node Dampening

Nodes with high in-degree (many things connect to them) should be dampened:

```python
def compute_hub_penalty(G: nx.DiGraph, node_id: str) -> float:
    """Nodes connected to everything are less informative."""
    in_degree = G.in_degree(node_id)
    # Log dampening: penalty increases with degree
    # in_degree=5 → penalty=0.85, in_degree=50 → penalty=0.4
    return 1.0 / (1.0 + 0.1 * np.log1p(in_degree))
```

Apply this as a multiplier in the scoring formula.

#### 3. Entity Type Filtering

Don't match geographic entities alone. "India" in an article doesn't mean it affects all Indian nodes:

```python
def filter_matches_by_type(matches, article_tags):
    """
    Geographic matches only count if paired with a topical match.
    """
    has_topical = any(m.category not in ("geography", "geopolitics") for m in matches)
    if not has_topical:
        # Only geographic matches — likely noise
        return [m for m in matches if m.match_confidence > 0.85]
    return matches
```

#### 4. Negative Signals

Add a prompt instruction for negative signals:

```
Also identify if this article is UNLIKELY to affect daily life despite
mentioning relevant topics. Mark severity as "low" for:
- Routine political statements without policy change
- Historical retrospectives
- Opinion pieces without new information
- Celebrity/entertainment news mentioning economic concepts
```

#### 5. Confidence Calibration via Feedback Loop

```python
# Track user feedback: "Was this relevant?"
# Per (article_pattern, user_pattern) → actual relevance
# Use to calibrate thresholds over time

feedback_log = {
    "predicted_score": 0.72,
    "user_feedback": "not_relevant",  # or "relevant", "very_relevant"
    "matched_nodes": ["india_rice_production", "monsoon"],
    "user_nodes": ["food_inflation"],
    "hops": 2
}

# Aggregate: if 2-hop food chain predictions are 60% accurate,
# adjust hop_decay[2] downward
```

#### 6. Cross-Validation Against Multiple Sources

If only one source reports an event, lower the score. If Reuters, Bloomberg, AND Economic Times all report it, boost:

```python
source_count_multiplier = min(1.0, 0.5 + 0.1 * article_metadata["source_count"])
# 1 source → 0.6, 5 sources → 1.0
```

---

## 10. Existing Systems to Study

### Google Knowledge Graph

**How it works:**
- 500B+ facts about 5B+ entities
- Entity linking via surface form matching + context disambiguation
- Uses Freebase (deprecated) → Wikidata as canonical entity IDs
- Key technique: **co-occurrence context** — "Apple" near "iPhone" → Apple Inc., "Apple" near "pie" → fruit

**What to steal:**
- Alias resolution with context: each node should have multiple surface forms
- Wikidata IDs as universal entity identifiers (you should add `wikidata_id` to your nodes)
- Saliency scoring: not just "mentioned" but "is this entity central to the article?"

### Wikipedia Entity Linking (REL, TAGME, WAT)

**How it works:**
- Mention detection → candidate generation → disambiguation
- Candidate generation uses Wikipedia anchor text statistics (what phrases link to which articles)
- Disambiguation uses context similarity between article text and Wikipedia article text

**What to steal:**
- The "candidate generation → disambiguation" two-stage is exactly your hybrid approach
- Anchor text statistics can be approximated by your alias lists
- Context disambiguation is what your embedding similarity does

### GDELT Global Knowledge Graph

**How it works:**
- Processes every news article in 100+ languages every 15 minutes
- Neural entity extraction with disambiguation, sentiment, and saliency
- Global Entity Graph (GEG): 11.3B entity annotations
- Uses Google NLP API for entity resolution (resolves "The Fed", "Federal Reserve Board", "US Federal Reserve" to same entity)

**What to steal:**
- GDELT GKG as a free input feed — it already does entity extraction and provides CAMEO event codes
- GKG themes: 2,231 theme tags extracted per article — you can use these as additional signal
- GKG tone: article-level sentiment scoring for severity estimation
- Consider consuming GDELT's entity extraction output directly rather than re-extracting

**Practical integration:**
```sql
-- GDELT GKG BigQuery: get entities + themes for recent articles
SELECT
  DocumentIdentifier as url,
  V2Themes as themes,        -- SEMICOLON-separated theme list
  V2Locations as locations,  -- geographic entities
  V2Persons as persons,
  V2Organizations as orgs,
  V2Tone as tone_scores
FROM `gdelt-bq.gdeltv2.gkg`
WHERE DATE(_PARTITIONTIME) = CURRENT_DATE()
```

### EventRegistry

**How it works:**
- Clusters articles about the same event
- Extracts: concepts (Wikipedia entities), categories (DMOZ), locations, dates
- Entity linking against Wikipedia/Wikidata
- $89/month for NewsAPI.ai (EventRegistry's API)

**What to steal:**
- Event clustering before processing — don't process 50 articles about the same event
- Their concept taxonomy is hierarchical and maps to Wikidata
- Use their API output (pre-extracted entities) as Stage 1 input when available

### HippoRAG (NeurIPS 2024)

**How it works:**
- LLM extracts Open Information Extraction (OpenIE) triples from text
- Builds a schema-less knowledge graph
- Uses Personalized PageRank with query concepts as seeds
- Retrieves multi-hop paths across documents

**What to steal:**
- The PPR-based retrieval pattern is directly applicable to your scoring
- Their "parahippocampal region" concept = your embedding matcher
- Their "hippocampal indexing" = your graph traversal
- Open-source implementation at `github.com/OSU-NLP-Group/HippoRAG`

### Relevance to Your System

| System | What to Use | What to Skip |
|--------|------------|-------------|
| Google KG | Alias resolution, Wikidata IDs, saliency | Their scale-specific optimizations |
| GDELT | Pre-extracted entities + themes as input | Re-extracting what they already extract |
| EventRegistry | Event clustering, pre-linked concepts | Their relevance scoring (different use case) |
| HippoRAG | PPR scoring pattern, code architecture | Schema-less graph (you have a schema) |
| Wikipedia EL | Two-stage candidate → disambiguate pattern | Wikipedia-specific statistics |

---

## 11. Final Architecture Recommendation

### Complete Pipeline

```
┌─────────────────────────────────────────────────────────┐
│                   ARTICLE INGESTION                      │
│  RSS/GDELT/NewsAPI → dedup → article queue               │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              STAGE 1: TAG EXTRACTION (LLM)               │
│                                                          │
│  Input: article headline + summary (~300 tokens)         │
│  Model: Gemini 2.0 Flash                                 │
│  Prompt: CoT + 5 few-shot examples                       │
│  Output: tags[], indirect_tags[], domains[], entities[]   │
│  Cost: ~$0.0003/article  Latency: ~400ms                 │
│                                                          │
│  ┌─ Filter broad tags (stop-list) ─┐                     │
│  └─ Flag novel concepts (no match) ─┘                    │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│          STAGE 2: NODE MATCHING (Embeddings)             │
│                                                          │
│  Embed tags → cosine similarity against node index       │
│  Model: BAAI/bge-small-en-v1.5 (local, free)            │
│  Index: FAISS over 1,110 nodes × ~4 aliases each        │
│  Threshold: 0.65 (auto-accept), 0.50 (needs LLM confirm)│
│  Domain filter: only search domains from Stage 1         │
│  Cost: $0  Latency: ~5ms                                 │
│                                                          │
│  ┌─ Hub dampening (penalize high-degree nodes) ─┐        │
│  └─ Entity type filter (geo-only = noise)        ─┘      │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│          STAGE 3: GRAPH PROPAGATION                      │
│                                                          │
│  For each matched node:                                  │
│    BFS outward through causal edges (max 3 hops)         │
│    Apply edge_type_weight × edge_strength at each hop    │
│    Collect all reached nodes with cumulative strength     │
│                                                          │
│  OR (if template matches):                               │
│    Fire causal template deterministically                 │
│    Template chains are pre-validated, higher confidence   │
│                                                          │
│  Store: NetworkX in-memory graph                         │
│  Cost: $0  Latency: <1ms                                 │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│          STAGE 4: USER MATCHING (Precomputed)            │
│                                                          │
│  Lookup: matched/propagated nodes ∩ user reachability set│
│  Precomputed: BFS backward from user's dependency nodes  │
│  Stored in: Redis (20KB per user, TTL 24h)               │
│  Cost: $0  Latency: <0.1ms                               │
│                                                          │
│  For each intersection:                                  │
│    Compute per-path score:                               │
│      match_confidence × hop_decay × edge_strength ×      │
│      user_importance × hub_penalty                       │
│    Aggregate via Noisy-OR                                │
│    Apply article severity + source credibility           │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│          STAGE 5: SCORING & DELIVERY                     │
│                                                          │
│  Score > 0.8  → PUSH notification (max 3/day)            │
│  Score 0.3-0.8 → Daily digest (8 AM)                     │
│  Score < 0.3  → Weekly summary / discard                  │
│                                                          │
│  Explanation generation: GPT-4o-mini with causal chain   │
│  Feedback collection: "Was this relevant?" → calibration │
└─────────────────────────────────────────────────────────┘
```

### Implementation Priority

| Component | Priority | Effort | Notes |
|-----------|----------|--------|-------|
| Stage 1 prompt + few-shots | P0 | 1 day | Core quality driver |
| Embedding index (FAISS) | P0 | 1 day | Node alias embeddings |
| Graph loader (NetworkX) | P0 | 0.5 day | Load YAML files |
| BFS propagation | P0 | 0.5 day | 3-hop traversal |
| User reachability precompute | P0 | 0.5 day | Backward BFS |
| Scoring (Noisy-OR) | P0 | 0.5 day | Aggregation formula |
| Hub dampening | P1 | 0.5 day | Noise reduction |
| Stop-list filtering | P1 | 0.25 day | Broad tag filtering |
| Feedback loop | P2 | 1 day | Calibration over time |
| PPR scoring upgrade | P2 | 1 day | Replace BFS scoring |
| GDELT GKG integration | P2 | 1 day | Use pre-extracted entities |
| Stage 2b LLM confirmation | P3 | 0.5 day | Borderline match precision |

**Total MVP (P0): ~4 days of implementation.**

### Key Metrics to Track

```python
metrics = {
    # Quality
    "tag_extraction_recall": "% of relevant nodes identified by Stage 1+2",
    "tag_extraction_precision": "% of identified nodes that are actually relevant",
    "false_positive_rate": "% of scored articles user marks 'not relevant'",
    "false_negative_rate": "% of relevant articles missed (sample manually)",

    # Performance
    "articles_per_day": "throughput",
    "p95_latency_per_article": "end-to-end pipeline latency",
    "llm_cost_per_day": "Stage 1 + explanation generation",

    # Coverage
    "novel_concept_rate": "% of articles with unmatched tags",
    "graph_coverage": "% of extracted tags that match a node",
    "domain_distribution": "which domains are most frequently matched",
}
```

---

## Appendix A: Token Budget Breakdown

```
Per article, Stage 1:
  System prompt + few-shots:  ~1,200 tokens (fixed)
  Article text (headline + summary): ~300 tokens
  Output:                     ~200 tokens
  Total:                      ~1,700 tokens

  At Gemini Flash ($0.10/1M in, $0.40/1M out):
  Cost = (1,500 × $0.10 + 200 × $0.40) / 1M = $0.00023/article

200 articles/day: $0.046/day = $1.38/month

Stage 2b (borderline confirmation, ~20% of articles):
  40 articles × ~500 tokens = ~$0.01/day

Explanation generation (scored articles, ~50/day):
  50 × ~800 tokens × GPT-4o-mini = ~$0.04/day

TOTAL LLM COST: ~$2.50/month
```

## Appendix B: Embedding Index Size

```
1,110 nodes × 4 aliases avg = 4,440 vectors
4,440 × 384 dimensions × 4 bytes = 6.8 MB (FAISS index)
With metadata: ~10 MB total

Easily fits in RAM. No need for external vector DB at this scale.
```

## Appendix C: Research Sources

### Entity Linking & Knowledge Graphs
- [LLM-empowered Knowledge Graph Construction: A Survey](https://arxiv.org/html/2510.20345v1)
- [Knowledge Graphs for Enhancing LLMs in Entity Disambiguation](https://arxiv.org/html/2505.02737v2)
- [Entity Linking with Relik in LlamaIndex (Neo4j)](https://neo4j.com/blog/developer/entity-linking-relationship-extraction-relik-llamaindex/)
- [LELA: LLM-based Entity Linking with Zero-Shot Domain Adaptation](https://hal.science/hal-05445830v1/file/LELA__preprint_.pdf)
- [ARTER: Adaptive Routing and Targeted Reasoning for Entity Linking](https://arxiv.org/html/2510.20098)
- [Entity Quality Enhancement in Knowledge Graphs](https://aclanthology.org/2025.genaik-1.14.pdf)

### Hierarchical Classification at Scale
- [Mercari: LLM-based Large-scale Item Category Classification](https://engineering.mercari.com/en/blog/entry/20240411-large-scale-item-categoraization-using-llm/)
- [TELEClass: Taxonomy Enrichment and LLM-Enhanced Hierarchical Text Classification](https://arxiv.org/html/2403.00165v1)
- [Hierarchical Text Classification with LLM-Refined Taxonomies](https://arxiv.org/html/2601.18375)
- [HierLabelNet: Two-Stage LLMs Framework](https://www.mdpi.com/2220-9964/14/7/268)
- [LLMs for Classification (Prompting Guide)](https://www.promptingguide.ai/prompts/classification)

### Graph Algorithms & Scoring
- [HippoRAG: Neurobiologically Inspired Long-Term Memory for LLMs (NeurIPS 2024)](https://arxiv.org/abs/2405.14831)
- [HippoRAG GitHub](https://github.com/OSU-NLP-Group/HippoRAG)
- [NetworkX PageRank Documentation](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.link_analysis.pagerank_alg.pagerank.html)
- [Personalized PageRank with Edge Weights](https://www.briggsby.com/personalized-pagerank)
- [Efficient Algorithms for Personalized PageRank: A Survey](https://arxiv.org/html/2403.05198v1)
- [Efficient Processing of k-Hop Reachability Queries](https://www.mdpi.com/2076-3417/13/6/3470)
- [Comparing Personalized PageRank and Activation Spreading in Wikipedia](https://www.researchgate.net/publication/357425215)

### Embeddings & Similarity
- [Is Cosine-Similarity of Embeddings Really About Similarity?](https://arxiv.org/html/2403.05440v1)
- [LLM Entity Agreement via Cosine Similarity (GitHub)](https://github.com/bllin001/llm-entities-agreement)

### Hallucination & Noise Reduction
- [Knowledge Graphs, LLMs, and Hallucinations: An NLP Perspective](https://arxiv.org/html/2411.14258v1)
- [Can Knowledge Graphs Reduce Hallucinations in LLMs?](https://arxiv.org/html/2311.07914v2)
- [GraphEval: KG-Based LLM Hallucination Evaluation](https://ceur-ws.org/Vol-3894/paper5.pdf)

### Causal Knowledge Graphs
- [Constructing and Interpreting Causal Knowledge Graphs from News](https://arxiv.org/abs/2305.09359)
- [Causal Inference for Knowledge Graph Completion](https://openreview.net/forum?id=Y1J29OryQg)
- [Causal Graph Extraction from News: Comparative Study](https://pmc.ncbi.nlm.nih.gov/articles/PMC9374167/)

### Structured Output & Constrained Decoding
- [PARSE: LLM-Driven Schema Optimization for Entity Extraction](https://arxiv.org/html/2510.08623v1)
- [SLOT: Structuring the Output of LLMs](https://aclanthology.org/2025.emnlp-industry.32.pdf)
- [Structured Output Generation: JSON Schema and Grammar-Based Decoding](https://medium.com/@emrekaratas-ai/structured-output-generation-in-llms-json-schema-and-grammar-based-decoding-6a5c58b698a6)

### GDELT & News Knowledge Graphs
- [GDELT Neural Entity Extraction and Disambiguation](https://blog.gdeltproject.org/neural-entity-extraction-disambiguation-sentiment-salience-knowledge-graph-linking-and-contextualization-via-web-ngrams-3-0/)
- [GDELT Global Knowledge Graph (GKG 2.0)](https://blog.gdeltproject.org/introducing-gkg-2-0-the-next-generation-of-the-gdelt-global-knowledge-graph/)
- [GDELT Global Entity Graph (11B entities)](https://blog.gdeltproject.org/announcing-the-global-entity-graph-geg-and-a-new-11-billion-entity-dataset/)
- [Talking to GDELT Through Knowledge Graphs](https://arxiv.org/html/2503.07584v1)

### SQLite & Graph Performance
- [SQLite with Graph Databases: Techniques for Hybrid Models](https://www.sqliteforum.com/p/sqlite-and-graph-hybrids)
- [SQLite for GraphRAG](https://stephencollins.tech/newsletters/sqlite-for-graphrag-lightweight-graph-database)
- [Graph Database Guide for AI Architects 2026](https://www.falkordb.com/blog/graph-database-guide/)
