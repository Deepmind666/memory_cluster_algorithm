# R-010 综合深度评估：Stage 1 + Stage 2

评审人：Claude Opus 4.6
评审时间：2026-02-10
评审范围：9a09e68（Stage 1）→ d5738b6（Stage 2）全量交付
评审依据：代码审查 + 正则验证 + 31/31 测试回归 + 实验数据交叉验证

---

## 一、总体评级

| 维度 | Stage 1 评级 | Stage 2 评级 | 综合评级 | 说明 |
|------|-------------|-------------|---------|------|
| 算法正确性 | A- | B+ | B+ | Stage 2 有 P1 正则 bug |
| 工程可靠性 | A- | A- | A- | 幂等/容错/锁机制稳固 |
| 测试覆盖 | B+ (28/28) | B (31/31) | B | 中文场景测试缺失 |
| 实验证据 | B+ | A- | A- | 3 套消融 + prune 对照，诚实报告负结果 |
| 文档完整性 | B+ | A- | A- | FINAL_REPORT + next_phase_plan 齐全 |
| 专利支撑 | B+ | B+ | B+ | 09 授权潜力未更新 |

**综合评级：B+**（Stage 2 有 1 个 P1 正则 bug 拉低算法正确性分）

---

## 二、Stage 1 回顾（可靠性闸门 · 9a09e68）

### 2.1 交付清单

| 交付项 | 状态 | 验证结果 |
|--------|------|---------|
| 幂等 ingest（`(id, version)` 去重） | 已交付 | `test_idempotent_skip` 通过 |
| 容错 store 加载（双层 try/except） | 已交付 | `test_bad_line_tolerance` 通过 |
| `_FileLock` 原子锁 | 已交付 | `O_CREAT\|O_EXCL` 原子创建确认 |
| `StoreReadStats` / `StoreAppendStats` | 已交付 | 6 字段 / 4 字段统计结构完整 |
| `time_utils.py` 统一时间解析 | 已交付 | `parse_iso_utc` 替代两处 `_parse_iso` |
| CLI `--idempotent` / `--strict-*` 开关 | 已交付 | `BooleanOptionalAction` 用法正确 |
| `test_store_reliability.py` (5 tests) | 已交付 | 全部通过 |
| `test_time_utils.py` (2 tests) | 已交付 | 全部通过 |

### 2.2 Stage 1 遗留问题（已在 R-009 记录）

| ID | 级别 | 描述 | 状态 |
|----|------|------|------|
| P2-NEW-10 | P2 | 幂等 append 全扫描 store | 暂缓（性能轮） |
| P2-3 | P2 | Windows GBK 编码 | 暂缓（仅显示层） |
| P2-1 | P2 | bound_cache 重建冗余 | 暂缓（性能轮） |
| P3-NEW-13 | P3 | CLI/store JSONL 解析逻辑重复 | 待处理 |
| P3-NEW-14 | P3 | 缺 lock 并发竞态测试 | 待处理 |

### 2.3 Stage 1 评价

Stage 1 的核心价值在于为 append-only JSONL store 建立了"写入安全网"：
- `_FileLock` 的 `O_CREAT|O_EXCL` 原子语义 + 30s 陈旧锁检测 = 跨进程安全
- `(id, version)` 幂等去重 = 重复 ingest 不会产生脏数据
- 双层 try/except + `StoreReadStats` = 单行损坏不影响全局加载

**主要风险**：幂等模式下每次 append 都全量读取 store（`store.py:116`），100K+ 行时将成为瓶颈。但当前规模可接受。

---

## 三、Stage 2 深度评估（冲突语义增强 · d5738b6）

### 3.1 变更范围

```
12 files changed, 735 insertions(+), 64 deletions(-)
```

核心变更：
- `compress.py`：+50 行，新增 4 个正则 + masked_spans 架构 + `_clean_value`
- `test_conflict_semantics.py`：新增 46 行，3 个测试方法
- `run_ablation.py`：+174 行，参数化 + 100 样本生成 + 多场景运行
- 4 份实验报告更新/新增
- `FINAL_REPORT.md` + `next_phase_plan.md` 同步

### 3.2 冲突语义增强架构（compress.py）

**新增正则模式：**

| 模式 | 目标 | 示例输入 | 预期输出 |
|------|------|---------|---------|
| `NEGATED_KEY_VALUE_PATTERN` | 中文否定 | "不是 mode=fast" | `(mode, !fast)` |
| `NOT_EQUAL_PATTERN` | 不等式 | "alpha != 0.7" | `(alpha, !0.7)` |
| `CONDITIONAL_SCOPE_PATTERN` | 条件作用域 | "if alpha=0.7 then..." | `(cond:alpha, 0.7)` |
| `COUNTERFACTUAL_SCOPE_PATTERN` | 反事实作用域 | "should have mode=safe" | `(cf:mode, safe)` |

**masked_spans 设计**：
- 条件/反事实作用域内的 KV 对标记为 `cond:`/`cf:` 前缀
- 被否定/条件匹配的文本区域加入 `masked_spans`
- 后续 KEY_VALUE_PATTERN 跳过已遮罩区域，避免重复提取
- 设计理念清晰，可扩展性好

**`_clean_value` 函数**：
- 去除值尾部标点：`.,;:!?，；。！？)]}）】>"'`
- 行为验证通过：`_clean_value("0.7.") = "0.7"`，`_clean_value("safe,") = "safe"`

### 3.3 发现的问题

---

#### P1-1 `NEGATED_KEY_VALUE_PATTERN` 正则 alternation order 错误

- **文件**: `compress.py:13-16`
- **严重性**: P1（核心功能缺陷）
- **现象**:

```python
# 当前代码
NEGATED_KEY_VALUE_PATTERN = re.compile(
    r"(?:不|非|不是|并非)\s*(...)",  # "不" 在 "不是" 之前
)
```

Python 正则 alternation 从左到右尝试，取第一个匹配。当输入 "不是 mode=fast" 时：
1. `"不"` 先匹配（而非 `"不是"`）
2. `"是"` 被捕获为 group(1)（slot name）
3. `"mode=fast"` 被捕获为 group(2)（value）

**实测验证**：
```
输入: "不是 mode=fast"
实际: g1='是', g2='mode=fast'  → slot='是', value='!mode=fast'
期望: g1='mode', g2='fast'    → slot='mode', value='!fast'
```

对比验证 alternation order：
```
re.compile(r'(?:不|非|不是|并非)').match('不是').group()  → '不'  （错误）
re.compile(r'(?:不是|并非|不|非)').match('不是').group()  → '不是'（正确）
```

- **影响范围**: 所有以 "不是"/"并非" 开头的中文否定语句都会产生错误的 slot 提取
- **修复方案**: 将 alternation 改为最长优先：`(?:不是|并非|不|非)`
- **风险评估**: 当前测试 `test_negated_key_value_extracts_not_value` 仅测试英文 `!=`，未覆盖中文否定，故此 bug 未被捕获

---

#### P2-1 Flag 模式不尊重 masked_spans

- **文件**: `compress.py:103-115`
- **严重性**: P2
- **现象**:

输入 `"if alpha != 0.7 then use beta=0.3"` 时，`POSITIVE_FLAG_EN_PATTERN` 匹配 `"use beta"` 产生 `('flag:beta', 'true')`。

但 `"use beta"` 位于条件作用域内，应被遮罩。Flag 模式（`NEGATIVE_FLAG_PATTERN` / `POSITIVE_FLAG_PATTERN` / `*_EN_PATTERN`）4 处均未调用 `_in_masked_spans()` 检查。

- **修复方案**: 在 flag 提取循环中增加 `_in_masked_spans` 守卫

---

#### P2-2 条件作用域内否定语义丢失

- **文件**: `compress.py:65-76`
- **严重性**: P2
- **现象**:

当 `NOT_EQUAL` 出现在条件作用域内时（如 "if alpha != 0.7 then ..."）：
- 条件作用域捕获了 `"alpha != 0.7 then use beta=0.3"`
- 但作用域内仅用 `KEY_VALUE_PATTERN` 二次提取，不运行 `NOT_EQUAL_PATTERN`
- 结果：否定语义 `!0.7` 在作用域内被静默丢弃
- 幸好 `NOT_EQUAL_PATTERN` 在全文级别仍会匹配到，所以 `('alpha', '!0.7')` 最终被保留
- 但语义上它应该是 `('cond:alpha', '!0.7')` 而非事实性否定

- **修复方案**: 在作用域内二次提取时也运行否定模式，产出 `cond:slot` / `cf:slot` + `!value`

---

#### P2-3 中文模式测试覆盖缺失

- **文件**: `test_conflict_semantics.py`
- **严重性**: P2
- **现象**: 3 个测试方法全部使用英文输入，未覆盖：
  - 中文否定："不是"/"非"/"并非"（含 P1-1 bug 场景）
  - 中文条件："如果"/"若"/"假如"/"当"
  - 中文反事实："本应"/"本来"/"本该"/"理应"/"要是当时"/"如果当时"
- **修复方案**: 至少为每个中文触发词各补 1 个测试用例

---

#### P2-4 消融报告 Summary 格式为原始 JSON

- **文件**: `ablation_report_large_cn.md:17`、`ablation_report_stress_cn.md:17`、`ablation_report_cn.md:17`
- **严重性**: P2（文档质量）
- **现象**: Summary 节直接 dump JSON 字符串，不便人类阅读
- **修复方案**: 展开为结构化 markdown 表格

---

#### P3-1 条件作用域正则贪婪捕获

- **文件**: `compress.py:25`
- **严重性**: P3
- **现象**: `[^,;，；。]+` 在长句中可能捕获过多内容
- 示例: `"if alpha=0.7 then increase throughput"` → 条件区域 = `"alpha=0.7 then increase throughput"`（包含了非条件部分）
- **缓解**: 当前靠 `masked_spans` 防止二次提取，功能上不影响正确性；但语义精度有损

---

#### P3-2 synthetic_fragments 生成模式单一

- **文件**: `run_ablation.py:106-207`
- **严重性**: P3
- **现象**: mod-6 固定分配模式，缺少：
  - 连续多条件句
  - 同一 fragment 内多 slot 否定
  - 中英文混合
- **影响**: 实验结论的泛化性受限于生成器多样性

---

### 3.4 实验数据交叉验证

#### 消融实验（3 套）

| 场景 | 片段数 | 阈值 | CEG 增益 | ARB 增益 | DMG 增益 | 评估 |
|------|-------|------|---------|---------|---------|------|
| 小样本 | 9 | 1.1/0.05 | priority_avg +8.8 | budget_avg +68.0 | block +4, mixed -1 | 符合预期 |
| 大样本 realistic | 100 | 0.68/0.82 | priority_avg +2.29 | budget_avg +38.2 | block=0 | DMG 未触发符合参数区间行为 |
| 大样本 stress | 100 | 1.1/0.05 | priority_avg +17.0 | budget_avg +58.0 | block +120, mixed -1 | DMG 在极端合并压力下显著生效 |

**验证结论**：
- CEG 在所有场景均有稳定增益（priority_avg 提升），说明冲突证据图识别有效
- ARB 在所有场景均有 budget 增益，且 stress 场景的 summary chars 增益 +209 说明自适应预算确实分配了更多细节空间
- DMG 的参数敏感性已被诚实记录：realistic 参数下不触发（因 assign 阶段已合并完毕，merge 阶段无候选对），stress 参数下大量触发
- **数据可信度**：3 套实验的 `generated_at` 时间戳一致（同批运行），metrics 与报告对齐

#### Prune 对照实验

| 场景 | 基线 avg_ms | 优化 avg_ms | 加速比 | 剪枝数 | 评估 |
|------|-----------|-----------|--------|--------|------|
| primary (0.82/0.85) | 19.84 | 22.57 | **-13.7%** | 0 | 无剪枝时有开销 |
| realistic (0.68/0.82) | 14.01 | 12.98 | +7.3% | 0 | 轻微加速 |
| sparse (2.0/0.95) | 261.01 | 225.00 | +13.8% | 2519 | 剪枝显著生效 |

**验证结论**：
- primary 负加速是因为 100 fragment + 0.82 阈值仅产生 3 簇、7 次合并尝试、0 次剪枝 — 剪枝的前缀分解开销 > 节省
- sparse 场景 4950 次合并尝试中剪枝 2519 对（50.9%），加速 13.8% — 验证了 Cauchy-Schwarz 上界的有效性
- **负结果诚实记录在 FINAL_REPORT.md 第 3.4 节**：值得肯定，未"吹牛"

---

## 四、综合风险矩阵

| 风险 | 级别 | 当前状态 | 缓解措施 |
|------|------|---------|---------|
| P1-1 中文否定正则 bug | 高 | 未修复 | 重排 alternation 顺序 |
| 幂等全扫描性能 | 中 | 暂缓 | 后续引入索引或增量扫描 |
| O(k^2) 合并复杂度 | 中 | 有 prune 缓解 | 后续 ANN/桶化 |
| 跨句指代/长句嵌套 | 中 | 已识别 | next_phase_plan 已规划 |
| 专利 09 授权潜力过时 | 低 | 未更新 | 需同步 CEG/ARB/DMG 进展 |

---

## 五、对 Codex 的具体建议

### 必须立即修复（Stage 2 补丁）

1. **P1-1**: `compress.py:13` 将 `(?:不|非|不是|并非)` 改为 `(?:不是|并非|不|非)`
2. **P2-3**: `test_conflict_semantics.py` 补充中文否定/条件/反事实测试（至少 3 个用例）

### 建议尽快修复

3. **P2-1**: flag 提取增加 `_in_masked_spans` 守卫
4. **P2-2**: 条件/反事实作用域内运行否定模式，生成带前缀的否定 slot
5. **P2-4**: 消融报告 Summary 改为结构化 markdown

### 后续阶段处理

6. **P3-1**: 条件正则增加 `then`/`那么` 分隔词限制捕获范围
7. **P3-2**: synthetic_fragments 增加中英混合、多否定、连续条件等变体

---

## 六、Stage 1 + Stage 2 综合评价

### 亮点

1. **masked_spans 架构设计出色**：条件/反事实/否定的优先级处理 + 遮罩避免重复提取，思路清晰、可扩展性强
2. **实验诚实性**：prune primary 负加速、realistic 参数下 DMG 不触发 — 均如实记录，未掩饰
3. **参数化消融脚本**：`--fragment-count` / `--similarity-threshold` / `--merge-threshold` / `--dataset-label` 使实验完全可复现
4. **可靠性工程扎实**：`_FileLock` + 幂等 ingest + 容错加载三件套构成完整的写入安全网
5. **文档体系完整**：FINAL_REPORT + next_phase_plan + 4 份实验报告 + review response = 工程交付闭环

### 不足

1. **P1 正则 bug 说明中文场景测试意识不足**：新增 4 个中文正则但无中文测试
2. **flag 模式是"补丁式"追加**：未纳入统一的 masked_spans 框架
3. **消融实验仍依赖合成数据**：缺乏真实多 Agent 对话产生的 fragment 验证

### 总结

Stage 1（可靠性闸门）+ Stage 2（冲突语义增强）的组合交付展现了良好的工程节奏和问题闭环能力。28→31 测试增长、3 套消融实验、诚实的负结果报告、结构化的 next_phase_plan 均值得肯定。

**P1-1 正则 bug 是唯一必须在进入下一阶段前修复的阻塞项**。修复后综合评级可提升至 **A-**。

---

## 七、附录：验证命令记录

```powershell
# 全量测试
python -m unittest discover -s tests -p "test_*.py" -q
# 结果：31/31 OK (0.062s)

# 编译检查
python -m compileall src tests scripts -q
# 结果：PASS

# alternation order 验证
python -c "import re; p=re.compile(r'(?:不|非|不是|并非)'); print(p.match('不是').group())"
# 结果：'不'（错误 — 应为'不是'）

# 组合语义验证
python -c "from src.memory_cluster.compress import _extract_slot_values; ..."
# 多场景验证结果详见正文
```

---

*本评估由 Claude Opus 4.6 于 2026-02-10 执行，基于 commit d5738b6 全量代码审查。*
