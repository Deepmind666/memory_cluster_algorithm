# Algorithm Specification: Multi-Agent Semantic Memory Fragment Clustering Compression

最后更新：2026-02-09

## 1. Scope
本规格定义单机可运行的记忆治理算法，目标是将多 Agent 共享记忆池中的碎片化信息进行：
- 增量语义聚类
- 簇内结构化融合与压缩
- 冲突显式标记
- 偏好驱动保留/降级
- 可逆 backref 追溯

## 2. Pipeline
S1. Fragment ingest
- 输入：`MemoryFragment` JSONL
- 输出：本地 append-only 存储

S2. Embedding
- 默认：`HashEmbeddingProvider`（无外部依赖，确定性）
- 可替换：后续接入 sentence-transformers / API embedding

S3. Incremental cluster assign
- 近邻规则：`cosine(centroid, embedding) >= similarity_threshold`
- 不满足阈值时新建簇
- 可选 category strict 模式

S4. Cluster merge
- 对簇中心做二次近邻合并，减少“同主题多簇”

S5. Preference policy decision
- 输入：类别、来源权重、时效策略
- 输出：`strong / weak / discardable` + detail budget

S6. Structured fusion + compression
- 去重同义片段
- 抽取结构化 slot-value
- 生成共识与冲突集合
- 输出压缩摘要

S7. Retrieval service
- 先返回簇摘要
- 按需通过 backrefs 展开原始碎片

S8. Evaluation
- 压缩比、冲突簇率、平均簇大小、去重率等

## 3. Data Schema
### 3.1 MemoryFragment
```json
{
  "id": "f001",
  "agent_id": "planner_agent",
  "timestamp": "2026-02-09T09:00:00+08:00",
  "content": "任务拆分...",
  "type": "decision",
  "tags": {"category": "method", "importance": "high"},
  "provenance": ["plan:phase-1"],
  "meta": {"slots": {"alpha": "0.7"}},
  "version": 1
}
```

### 3.2 MemoryCluster
```json
{
  "cluster_id": "cluster-0001",
  "centroid": [0.0, 0.1, 0.2],
  "fragment_ids": ["f001", "f002"],
  "source_distribution": {"planner_agent": 1, "writer_agent": 1},
  "consensus": {"alpha": "0.7"},
  "conflicts": [
    {
      "slot": "alpha",
      "values": ["0.2", "0.7"],
      "evidences": ["f004", "f005"],
      "last_seen": "2026-02-09T09:06:00+08:00"
    }
  ],
  "summary": "...",
  "backrefs": ["f001", "f002"],
  "version": 2
}
```

### 3.3 PreferenceConfig
```json
{
  "category_strength": {
    "requirement": "strong",
    "method": "strong",
    "evidence": "strong",
    "noise": "discardable"
  },
  "source_weight": {
    "planner_agent": 1.1,
    "writer_agent": 1.0,
    "verifier_agent": 1.6
  },
  "stale_after_hours": 168,
  "detail_budget": {
    "strong": 900,
    "weak": 500,
    "discardable": 180
  },
  "keep_conflicts": true
}
```

### 3.4 optimization_rounds.json schema (for future iterative optimization)
```json
{
  "round": 1,
  "changes": ["lowered similarity threshold from 0.72 to 0.65"],
  "before": {"compression_ratio": 0.74},
  "after": {"compression_ratio": 0.59},
  "decision": "accepted",
  "timestamp": "2026-02-09T16:00:00+08:00"
}
```

## 4. Failure Handling
- Ingest 文件不存在：返回错误码并写入日志，不写入脏数据。
- 无可用碎片：`build` 命令返回 status=error，提示先 ingest。
- 聚类阈值过高导致碎片化：通过 benchmark 与测试建议阈值回调。
- 检索召回过大：先摘要注入，限制 top-k，再按 backrefs 局部展开。

## 5. Technical Effect Mapping (CNIPA-friendly)
- 存储侧：碎片数与摘要层级压缩，降低长期记忆体量。
- 传输侧：上下文注入时优先摘要，降低 token 预算。
- 处理侧：检索从全量扫描转为簇级粗召回 + 细展开，降低延迟。
- 一致性侧：冲突显式化，避免隐式覆盖导致的错误传播。

## 6. Reproducible Commands
```powershell
python -m src.memory_cluster.cli ingest --input data/examples/multi_agent_memory_fragments.jsonl --store outputs/memory_store.jsonl
python -m src.memory_cluster.cli build --store outputs/memory_store.jsonl --output outputs/cluster_state.json --preferences data/examples/preference_profile.json
python -m src.memory_cluster.cli query --state outputs/cluster_state.json --query "alpha 冲突参数" --top-k 3 --expand
python scripts/run_benchmark.py --input data/examples/multi_agent_memory_fragments.jsonl --preferences data/examples/preference_profile.json --output outputs/benchmark.json --runs 5
```
