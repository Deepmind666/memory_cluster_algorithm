# 面向 GPT-5.3 Codex 的方向三主任务文档（单一真源）

最后更新：2026-02-09
适用方向：多 Agent 语义记忆碎片聚类压缩（含保留偏好）

> 说明：本文件是当前唯一生效的主任务文档。历史拼接版本已归档至 `docs/archive/gptdeepsearch2_9_merged_20260209.md`。

## 1. 总目标
在单机环境实现并验证以下闭环：
1. 多 Agent 异构记忆碎片采集与持久化
2. 语义向量化 + 增量聚类
3. 簇内去重压缩 + 冲突显式标记
4. 偏好向量驱动保留/降级策略
5. 可逆 backrefs 回溯与检索注入
6. 输出可复现评测指标与专利交底材料

## 2. 强约束
- 必须落代码、落脚本、落文档，不做空泛叙述。
- 每个关键阶段写入 `WORK_PROGRESS.md`。
- 先行技术必须做“检索-对比-绕开”闭环。
- 不宣称绝对新颖性或必然授权。
- 发明人应为自然人，不得将 AI 填为发明人。

## 3. 目录与交付
- 代码：`src/memory_cluster/`
- 测试：`tests/`
- 示例数据：`data/examples/`
- 算法规格：`docs/design/algorithm_spec.md`
- 详细规格：`docs/design/algorithm_spec_detailed.md`
- 检索与绕开：`docs/prior_art/`
- 专利草案：`docs/patent_kit/`
- 总结报告：`docs/FINAL_REPORT.md`

## 4. 当前实现模块映射（以现代码为准）
- `models.py`：Fragment / Cluster / Preference / Conflict 数据结构
- `embed.py`：HashEmbeddingProvider 与相似度函数
- `cluster.py`：增量聚类与簇合并
- `compress.py`：簇内去重、共识抽取、冲突标记、严格分裂建议
- `preference.py`：偏好决策引擎
- `store.py`：JSONL 存储与结果读写
- `retrieve.py`：检索与可选展开
- `eval.py`：指标计算
- `pipeline.py`：端到端编排
- `cli.py`：命令行入口

## 5. 核心算法步骤（S1-S7）
- S1 采集：接收多 Agent 记忆碎片并标准化。
- S2 向量化：计算语义向量，支持本地确定性实现。
- S3 增量聚类：阈值归簇或新建簇。
- S4 融合压缩：簇内去重、结构化槽位抽取、摘要压缩。
- S5 冲突显式：同槽位多值写入 `conflicts`，禁止静默覆盖。
- S6 偏好治理：按类别/来源/时效控制保留强度与预算。
- S7 检索回溯：先返回簇摘要，再按 `backrefs` 展开证据。

## 6. 评测指标（最少）
- Compression Ratio
- Dedup Reduction
- Conflict Coverage / Conflict Cluster Rate
- Query Latency（示例级）
- Backref Coverage

## 7. 优先改进清单（代码继续推进）
- [x] BOM 编码兼容（CLI/benchmark）
- [x] 语义近重复去重（Jaccard）
- [x] 否定冲突识别（flag:true/false）
- [x] 严格冲突分裂（split groups / child clusters）
- [ ] 二级主题层次压缩（L2 clusters）
- [ ] 检索分页与排序策略增强
- [ ] 大规模簇下的近似检索优化（替代 O(n^2) 合并）

## 8. 运行命令
```powershell
python -m src.memory_cluster.cli ingest --input data/examples/multi_agent_memory_fragments.jsonl --store outputs/memory_store.jsonl
python -m src.memory_cluster.cli build --store outputs/memory_store.jsonl --output outputs/cluster_state.json --preferences data/examples/preference_profile.json --similarity-threshold 0.4 --merge-threshold 0.85
python -m src.memory_cluster.cli query --state outputs/cluster_state.json --query "alpha 冲突参数" --top-k 3 --expand
python -m src.memory_cluster.cli eval --state outputs/cluster_state.json --output outputs/perf_metrics.json
python scripts/run_benchmark.py --input data/examples/multi_agent_memory_fragments.jsonl --preferences data/examples/preference_profile.json --output outputs/benchmark.json --runs 5 --similarity-threshold 0.4 --merge-threshold 0.85
python -m unittest discover -s tests -p "test_*.py" -v
```

## 9. 先行技术风险雷达（简版）
- 语义聚类（高）
- 偏好摘要（高）
- 共享向量记忆（高）
- 单会话滚动摘要（中高）
- 分层记忆管理（中）

对应绕开策略见：`docs/prior_art/feature_matrix.md` 与 `docs/prior_art/design_around.md`。

## 10. 非法律声明
本文件用于工程实现与专利草案准备，不构成法律意见。正式申请前应由专利代理人完成检索和审查。
