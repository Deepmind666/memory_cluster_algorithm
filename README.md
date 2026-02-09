# memory_cluster_algorithm

## 项目背景
本项目聚焦多 Agent 协同场景下的共享记忆治理问题：在长期对话与工具调用中，记忆碎片会快速膨胀并出现重复、冲突和溯源困难。仓库提供一个单机可运行的“语义聚类 + 冲突显式 + 偏好保留 + 可逆回溯”原型，并同步产出中国发明专利草案素材。

## 仓库命名说明
仓库名 `memory_cluster_algorithm` 即当前技术方向（记忆碎片聚类压缩），不再是旧版“运行态反馈代码优化”方向。

## 目标
- 实现可运行的多 Agent 记忆碎片聚类压缩原型。
- 输出可复现测试、基准和示例数据。
- 产出 prior-art 对比与专利交底材料草案。
- 全过程可审计（日志、命令、指标）。

## 环境依赖
- Windows PowerShell 5.1+（或 PowerShell 7+）
- Python 3.10+（当前实测 3.14）
- 依赖安装：
```powershell
python -m pip install -r requirements.txt
```

## 核心目录
- `src/memory_cluster/`：算法与 CLI 实现。
- `tests/`：单元测试。
- `data/examples/`：多 Agent 示例碎片与偏好配置。
- `docs/design/`：算法规格。
- `docs/prior_art/`：检索记录、特征矩阵、绕开策略。
- `docs/patent_kit/`：专利交底草案包。
- `docs/FINAL_REPORT.md`：端到端结果总报告。

## 快速运行
```powershell
python -m src.memory_cluster.cli ingest --input data/examples/multi_agent_memory_fragments.jsonl --store outputs/memory_store.jsonl
python -m src.memory_cluster.cli build --store outputs/memory_store.jsonl --output outputs/cluster_state.json --preferences data/examples/preference_profile.json --similarity-threshold 0.4 --merge-threshold 0.85
python -m src.memory_cluster.cli build --store outputs/memory_store.jsonl --output outputs/cluster_state_l2.json --preferences data/examples/preference_profile.json --similarity-threshold 0.4 --merge-threshold 0.85 --enable-l2-clusters --l2-min-children 2
python -m src.memory_cluster.cli query --state outputs/cluster_state.json --query "alpha 冲突参数" --top-k 3 --offset 0 --expand
python -m src.memory_cluster.cli query --state outputs/cluster_state_l2.json --query "method topic" --top-k 3 --cluster-level l2 --expand
python -m unittest discover -s tests -p "test_*.py" -v
```

## 进展与质量门禁
- 进展日志：`WORK_PROGRESS.md`
- 质量清单：`docs/REVIEW_CHECKLIST.md`
- 日志追加脚本：`scripts/append_progress.ps1`

## 合规说明
- 本仓库提供技术实现与撰写辅助，不构成法律意见。
- 发明人应为自然人，正式申请文本请由专利代理人/律师复核。
