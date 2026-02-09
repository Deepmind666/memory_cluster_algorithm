# 多智能体语义记忆碎片聚类压缩算法 — 详细技术规格

> 撰写人: Claude Opus 4.6（评审角色）
> 时间戳: 2026-02-09
> 状态: 初稿，供 Codex 对齐与实现参考
> 非法律意见声明: 本文档为技术规格材料，不构成专利法律意见。

---

## 1. 系统定位与边界

### 1.1 解决的技术问题

在单机多智能体（multi-agent）协同场景中，多个 Agent 并行产出的中间推理、工具输出、局部草稿、验证结论等信息碎片会持续写入共享记忆池。随着任务推进，共享记忆面临三个核心技术问题：

| 问题编号 | 技术问题 | 计算机系统层面表现 |
|---------|---------|------------------|
| TP-1 | 上下文膨胀 | 提示词 token 数超出窗口限制，内存/显存占用线性增长 |
| TP-2 | 跨 Agent 冗余 | 多 Agent 对同一事实的重复描述导致存储浪费、检索噪声增大 |
| TP-3 | 跨 Agent 不一致 | 不同 Agent 对同一参数/结论给出矛盾值，静默覆盖导致下游错误 |

### 1.2 系统边界

- **适用场景**: 单机部署，3-10 个 Agent 协同，碎片量级 10^2 ~ 10^4
- **不适用场景**: 分布式集群、实时流式处理（>10K 碎片/秒）、跨网络多节点
- **依赖约束**: Python 3.10+，零必选外部依赖（stdlib only），可选 sentence-transformers / faiss-cpu

---

## 2. 三层架构

```
┌─────────────────────────────────────────────────┐
│                  服务层 (Service)                 │
│  retrieve.py: 检索注入    cli.py: 命令行接口      │
│  eval.py: 指标计算        pipeline.py: 编排       │
├─────────────────────────────────────────────────┤
│                  整理层 (Processing)              │
│  embed.py: 向量化    cluster.py: 增量聚类         │
│  compress.py: 簇内压缩+冲突检测                   │
│  preference.py: 偏好策略引擎                      │
├─────────────────────────────────────────────────┤
│                  采集层 (Ingestion)               │
│  models.py: 数据结构定义                          │
│  store.py: JSONL 持久化 (append-only)            │
└─────────────────────────────────────────────────┘
```

---

## 3. 核心数据结构

### 3.1 MemoryFragment（记忆碎片）

最小信息单元，由 Agent 或工具执行产生。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | str | 是 | 全局唯一标识（建议 UUID） |
| `agent_id` | str | 是 | 来源 Agent 标识 |
| `timestamp` | str (ISO 8601) | 是 | 产生时间，含时区 |
| `content` | str | 是 | 碎片文本内容 |
| `type` | str | 是 | 类型枚举：`dialog` / `tool_output` / `conclusion` / `evaluation` / `decision` / `draft` / `log` |
| `tags` | dict | 否 | 结构化标签，关键字段：`category`（如 `method` / `evidence` / `requirement` / `noise`） |
| `provenance` | list[str] | 否 | 可追溯引用（文件路径、命令日志、原始碎片 ID 列表） |
| `meta` | dict | 否 | 扩展元数据，如 `slots`（结构化键值对，用于冲突检测） |
| `version` | int | 否 | 版本号，默认 1，用于 append-only 存储的去重 |

**设计要点**:
- `provenance` 保证压缩可逆：即使上层只保留簇摘要，也能定位原始证据并"再水化（rehydrate）"
- `meta.slots` 为冲突检测提供结构化通道，补充正则提取的不足

### 3.2 MemoryCluster（语义簇）

语义相近碎片的集合，是压缩和检索的基本单位。

| 字段 | 类型 | 说明 |
|------|------|------|
| `cluster_id` | str | 簇唯一标识（格式：`cluster-NNNN`） |
| `centroid` | list[float] | 簇代表向量（成员向量的加权滑动平均） |
| `fragment_ids` | list[str] | 归属碎片 ID 列表（含历史，不去重） |
| `source_distribution` | dict[str, int] | 各 Agent 贡献碎片数 |
| `tags` | dict | 簇级标签，含 `category`、`retention_strength` |
| `consensus` | dict[str, str] | 簇内共识参数（单值 slot） |
| `conflicts` | list[ConflictRecord] | 簇内冲突记录（多值 slot） |
| `summary` | str | 压缩后的簇摘要文本 |
| `backrefs` | list[str] | 去重后的碎片 ID 列表（压缩后保留的溯源指针） |
| `last_updated` | str (ISO 8601) | 最后更新时间 |
| `version` | int | 版本号 |

### 3.3 ConflictRecord（冲突记录）

当簇内同一 slot 出现多个不同值时，显式保留冲突而非静默覆盖。

| 字段 | 类型 | 说明 |
|------|------|------|
| `slot` | str | 冲突参数名（如 `alpha`、`threshold`） |
| `values` | list[str] | 所有冲突值（排序后） |
| `evidences` | list[str] | 提供冲突值的碎片 ID 列表 |
| `last_seen` | str (ISO 8601) | 最后一次观测到冲突的时间 |

**设计原则**: 多代理共享记忆的核心风险是"读到不一致版本"。显式冲突标记将不一致从隐式错误转变为显式待处理事项。

### 3.4 PreferenceConfig（偏好配置）

控制压缩行为的系统级策略向量，不是自然语言愿望。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `category_strength` | dict[str, str] | `{}` | 类别 → 保留强度映射（`strong`/`weak`/`discardable`） |
| `source_weight` | dict[str, float] | `{}` | Agent ID → 信任权重（>1.0 提升，<1.0 降级） |
| `stale_after_hours` | int | `72` | 超过此小时数未被引用则视为过期 |
| `detail_budget` | dict[str, int] | `{strong:700, weak:350, discardable:120}` | 各强度级别的摘要字符预算 |
| `keep_conflicts` | bool | `true` | 是否保留冲突记录 |

**四类偏好维度**:
1. **类别偏好**: 按 `tags.category` 决定保留力度
2. **来源偏好**: 按 `agent_id` 的信任权重调整（如 verifier > writer）
3. **时效偏好**: 过期碎片自动降级
4. **预算偏好**: 给定字符预算，控制摘要详细程度

---

## 4. 核心算法流程（S1-S7）

### S1. 碎片采集与持久化

**输入**: Agent 产出的原始信息单元
**输出**: 持久化到 JSONL 存储的 MemoryFragment 序列

```
Agent_A ──┐
Agent_B ──┼──→ FragmentStore.append_fragments() ──→ memory_store.jsonl
Agent_C ──┘
```

- 存储模式: Append-only JSONL，每行一个 JSON 对象
- 版本控制: 同 ID 碎片可多次写入，`load_latest_by_id()` 取最新版本
- 编码: UTF-8，`ensure_ascii=False` 保留中文原文

### S2. 语义向量化

**输入**: 碎片文本 `content`
**输出**: 固定维度浮点向量 `list[float]`

当前实现（MVP）: `HashEmbeddingProvider`
- 分词: 正则 `[A-Za-z0-9_\u4e00-\u9fff]+`，支持中英文混合
- 哈希映射: blake2b(token) → 向量维度索引，累加计数
- L2 归一化: 输出单位向量，便于余弦相似度计算
- 维度: 默认 256，可配置

可选增强:
- `sentence-transformers` 本地模型（如 `all-MiniLM-L6-v2`）
- TF-IDF 退化方案（`TfidfVectorizer`）

**接口抽象**: `EmbeddingProvider(ABC)` → `embed(text) -> list[float]`，支持替换

### S3. 增量聚类

**输入**: 新碎片向量 + 现有簇列表
**输出**: 更新后的簇列表（碎片归入已有簇或创建新簇）

算法: Online Centroid Clustering

```
对每个新碎片 f:
  1. vec = embed(f.content)
  2. 对所有现有簇 c，计算 sim = cosine(vec, c.centroid)
     - 若 category_strict=True，跳过类别不兼容的簇
  3. 取 best_cluster = argmax(sim)
  4. 若 best_sim >= assign_threshold (默认 0.72):
       → 归入 best_cluster
       → 更新 centroid: new = (old * n + vec) / (n + 1)  [滑动平均]
       → 追加 fragment_id, backref, source_distribution
  5. 否则:
       → 创建新簇，centroid = vec
```

**关键参数**:

| 参数 | 默认值 | 作用 |
|------|--------|------|
| `assign_threshold` | 0.72 | 碎片归入已有簇的最低相似度 |
| `merge_threshold` | 0.90 | 簇间合并的最低相似度 |
| `category_strict` | False | 是否强制同类别才能聚类 |

**簇合并**: 聚类完成后，扫描所有簇对，若 centroid 相似度 >= `merge_threshold` 则合并（加权平均 centroid，合并 fragment_ids/backrefs/source_distribution）。

**复杂度**: 归簇 O(n*k)，合并 O(k^2)，其中 n=碎片数，k=簇数。MVP 可接受，大规模场景建议引入 faiss 近邻索引。

### S4. 簇内压缩

**输入**: 簇的成员碎片列表
**输出**: 去重后的摘要文本 + 共识参数 + 冲突记录

分两步执行，避免"摘要吞掉边界条件"：

**Step 4a — 结构化融合**:
1. 文本去重: normalize(content) 精确匹配去重
2. Slot-Value 提取: 正则 + meta.slots 双通道
3. 共识判定: 单值 slot → consensus dict
4. 冲突标记: 多值 slot → ConflictRecord（保留所有值 + 证据碎片 ID）

**Step 4b — 摘要生成**:
1. 根据偏好强度确定 detail_budget（字符数）
2. 构建摘要: 簇元信息 + 共识参数 + 冲突参数 + 代表碎片片段（前 6 条）
3. 若超出预算则截断（当前为硬截断，建议改为按段落截断）

### S5. 冲突检测与标记

**检测通道**:

| 通道 | 方法 | 示例 |
|------|------|------|
| 正则提取 | `KEY_VALUE_PATTERN` 匹配 `key=value` / `key:value` / `key：value` | `alpha=0.7` vs `alpha=0.2` |
| 结构化元数据 | `fragment.meta["slots"]` dict | `{"alpha": "0.7"}` vs `{"alpha": "0.2"}` |

**处理策略**:
- `keep_conflicts=True`（默认）: 保留所有冲突记录，不做投票或覆盖
- `keep_conflicts=False`: 静默跳过冲突（不推荐，仅用于极端压缩场景）

**未来增强（Phase 2）**:
- 否定冲突检测: "不需要X" vs "需要X"
- NLI 模型辅助: 语义级矛盾检测

### S6. 偏好驱动保留策略

**决策流程**（对每个碎片）:

```
1. 查 category_strength[fragment.tags.category]
   → 初始 strength (strong/weak/discardable)

2. 查 source_weight[fragment.agent_id]
   → 若 weight >= 1.5 且 strength=weak → 提升为 strong
   → 若 weight < 0.8 且 strength=strong → 降级为 weak

3. 检查时效: age > stale_after_hours?
   → 若过期且 strong → 降级为 weak
   → 若过期且 weak → 降级为 discardable

4. 输出 PreferenceDecision:
   - strength, detail_budget, source_weight, stale, reasons[]
```

**簇级强度**: 取簇内所有碎片决策的最高强度（max 策略）

**可审计性**: 每个决策附带 `reasons` 列表，记录完整推理链

### S7. 分层压缩与索引（增强版）

当簇数量增长到阈值（建议 > 50），对簇摘要再聚类生成二级摘要树：

```
Level 2:  [主题级章节摘要]
              │
Level 1:  [簇摘要] [簇摘要] [簇摘要] ...
              │         │         │
Level 0:  [碎片]    [碎片]    [碎片] ...
```

- 每个节点保留 `backrefs` 指向下层
- 检索时"先粗后细"：L2 → L1 → L0
- 压缩比与信息保真度由偏好参数和 token 预算控制

**当前状态**: 代码中尚未实现 L2 层，属于 Phase 5+ 增强项。

---

## 5. 检索与上下文注入

### 5.1 检索算法

```
query(text, top_k, expand) → list[ClusterResult]

1. query_vec = embed(text)
2. 对每个簇 c:
   a. score_centroid = cosine(query_vec, c.centroid)
   b. score_summary = cosine(query_vec, embed(c.summary))
   c. score = max(score_centroid, score_summary)
   d. score += keyword_bonus(text, c.summary)  [每命中一个关键词 +0.05]
3. 按 score 降序排列，取 top_k
4. 若 expand=True，展开 backrefs 对应的原始碎片
```

### 5.2 上下文注入策略（建议）

将检索结果注入 Agent 提示词时，建议按以下优先级：
1. 冲突标记（必须注入，防止下游 Agent 基于错误前提推理）
2. 强保留簇摘要
3. 弱保留簇摘要（按 token 预算截断）
4. 可丢弃簇仅在显式请求时展开

---

## 6. 评测指标体系

| 指标 | 计算方式 | 对应技术效果 |
|------|---------|-------------|
| `compression_ratio` | compressed_chars / original_chars | 减少存储占用 |
| `dedup_reduction` | 1 - (unique_texts / total_fragments) | 去除跨 Agent 冗余 |
| `avg_cluster_size` | fragments / clusters | 聚类粒度合理性 |
| `conflict_count` | 所有簇冲突记录总数 | 不一致检测覆盖度 |
| `conflict_cluster_rate` | 含冲突簇数 / 总簇数 | 冲突分布密度 |
| `backref_count` | 所有簇 backrefs 总数 | 溯源完整性 |
| `fragment_type_distribution` | 按 type 分组计数 | 碎片类型分布 |
| `source_distribution` | 按 agent_id 分组计数 | Agent 贡献分布 |

**CNIPA 可认可的技术效果表达**:
- 减少数据存储: compression_ratio < 1.0
- 减少传输/注入: 压缩后 token 数显著低于原始
- 提高检索效率: 簇级检索 vs 全量碎片扫描
- 降低处理时延: 去重后处理碎片数减少

---

## 7. 模块对照表（规格 vs 实现）

| 规格模块 | 实际文件 | 状态 | 备注 |
|---------|---------|------|------|
| 碎片数据模型 | `models.py` | 已实现 | 含 Fragment/Cluster/Conflict/Preference/BuildResult |
| 向量化 | `embed.py` | 已实现 | HashEmbedding MVP，抽象接口已定义 |
| 增量聚类 | `cluster.py` | 已实现 | assign + merge，缺 split |
| 簇内压缩 | `compress.py` | 已实现 | 去重+冲突+摘要，缺语义级去重 |
| 冲突检测 | `compress.py` 内 | 已实现 | 正则+meta 双通道，缺否定冲突 |
| 偏好策略 | `preference.py` | 已实现 | 三级强度+来源+时效 |
| 持久化 | `store.py` | 已实现 | JSONL append-only |
| 检索 | `retrieve.py` | 已实现 | 双通道+keyword bonus |
| 评测 | `eval.py` | 已实现 | 12 项指标 |
| 编排 | `pipeline.py` | 已实现 | 全链路编排 |
| CLI | `cli.py` | 已实现 | 4 子命令 |
| 分层压缩 | — | 未实现 | Phase 5+ 增强项 |
| 簇分裂 | — | 未实现 | 当簇过大时应支持拆分 |
| 语义级去重 | — | 未实现 | 当前仅精确文本匹配 |
| 否定冲突检测 | — | 未实现 | "不需要X" vs "需要X" |

---

## 8. 与现有技术的差异化定位

本方案的创新点不在单一技术，而在**组合差异**：

| 差异维度 | 现有技术典型做法 | 本方案做法 |
|---------|----------------|----------|
| 聚类对象 | 单用户 utterance | 多 Agent 异构碎片（含工具输出/中间结论/评测日志） |
| 压缩单元 | 滚动摘要（线性压缩） | 簇内融合（同类合并）+ 冲突显式标记 + 可逆 backref |
| 偏好控制 | 摘要格式偏好（长度/风格） | 系统级策略向量（写入/合并/降级/再水化全过程控制） |
| 一致性 | 静默覆盖或投票 | 显式冲突标记 + 证据指针保留 |
| 可度量效果 | 主观评价 | 12 项系统指标对齐 CNIPA 技术效果表达 |

**碰撞风险最高的现有专利**（详见 gptdeepsearch2_9.md 碰撞分析）:
- US20110238408A1: 语义聚类 — 绕开点：聚类对象为多 Agent 异构碎片
- US12008332B1: 偏好驱动摘要 — 绕开点：偏好是系统级策略向量而非格式控制
- US20240289863A1: 共享向量记忆 — 绕开点：重点是压缩治理而非共享访问
- EP4657312A1: 分层记忆+管理代理 — 绕开点：语义聚类+冲突保留+偏好驱动的特定算法闭环

---

## 9. 后续增强路线图

| 阶段 | 内容 | 优先级 |
|------|------|--------|
| Phase A | 语义级去重（embedding 相似度阈值去重） | 高 |
| Phase B | 否定冲突检测（规则 + 可选 NLI） | 高 |
| Phase C | 簇分裂（当簇内碎片数 > max_cluster_size 时自动拆分） | 中 |
| Phase D | 分层压缩 L2（簇摘要再聚类） | 中 |
| Phase E | sentence-transformers 集成 | 中 |
| Phase F | faiss-cpu 近邻索引（加速大规模聚类） | 低 |
| Phase G | 并发写入保护（文件锁或 SQLite WAL） | 低 |

---

## 10. 可复现命令

```powershell
# 安装依赖（仅 pytest）
pip install -r requirements.txt

# 运行测试
python -m pytest tests/ -q

# 完整 pipeline 演示
python -m src.memory_cluster.cli ingest --input data/examples/multi_agent_memory_fragments.jsonl --store outputs/memory_store.jsonl
python -m src.memory_cluster.cli build --store outputs/memory_store.jsonl --output outputs/cluster_state.json --preferences data/examples/preference_profile.json
python -m src.memory_cluster.cli query --state outputs/cluster_state.json --query "冲突参数" --top-k 3
python -m src.memory_cluster.cli eval --state outputs/cluster_state.json
```

---

> 本文档由 Claude Opus 4.6 基于代码审读和技术分析撰写，供 Codex 对齐实现与专利材料撰写参考。
> 所有技术判断均为初步分析，不替代专利法律检索与侵权分析。
