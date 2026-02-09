# memory_cluster_algorithm

面向“基于运行态反馈的代码生成优化”专利交底与工程化验证仓库。

## 目标
- 产出可执行的 Codex Agent 任务规范。
- 形成“运行-监测-反馈-优化”闭环文档模板。
- 持续记录进展与评审清单，便于交接和审计。

## 当前核心文件
- `gptdeepsearch2_9.md`: 主任务说明书（可直接用于 Codex Agent）。
- `.claude.md`: 项目交接与回复规范。
- `WORK_PROGRESS.md`: 全程进展日志（带时间戳+检查清单）。
- `docs/REVIEW_CHECKLIST.md`: 统一质量门禁。
- `scripts/append_progress.ps1`: 追加进展日志的脚本。

## 快速使用
1. 查看主任务说明：
```powershell
Get-Content -Raw gptdeepsearch2_9.md
```
2. 追加一次进展记录：
```powershell
powershell -ExecutionPolicy Bypass -File scripts/append_progress.ps1 `
  -Stage "Draft update" `
  -Actions "重写主文档","完成自查" `
  -FilesReviewed "gptdeepsearch2_9.md" `
  -FilesChanged "gptdeepsearch2_9.md","WORK_PROGRESS.md" `
  -ReviewChecklist "需求覆盖完成","格式检查完成"
```
3. 查看质量门禁：
```powershell
Get-Content -Raw docs/REVIEW_CHECKLIST.md
```

## 说明
- 本仓库提供技术与流程支持，不构成法律意见。
- 任何专利申请文本应由合格专利代理人/律师最终审阅。
