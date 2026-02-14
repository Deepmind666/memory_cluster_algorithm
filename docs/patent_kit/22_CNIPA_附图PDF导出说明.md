# 22 CNIPA 附图 PDF 导出说明

## 1. 用途
将 v2 附图批量导出为 PDF，供提交前核对与封版使用。

## 2. 一键命令
在仓库根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/export_cnipa_figures_pdf.ps1
```

## 3. 默认输入图件
- `docs/patent_kit/figures/fig1_v2_system_architecture.svg`
- `docs/patent_kit/figures/fig2_v2_method_flow.svg`
- `docs/patent_kit/figures/fig3_v2_data_structure.svg`
- `docs/patent_kit/figures/fig4_v2_conflict_evidence_graph.svg`
- `docs/patent_kit/figures/fig5_v2_dual_channel_gate.svg`
- `docs/patent_kit/figures/fig6_v2_retrieval_backref.svg`
- `docs/patent_kit/figures/fig_abs_v2_abstract.svg`

## 4. 默认输出目录
- `outputs/cnipa_submission/pdf/`

输出文件：
- 7 个附图 PDF
- `outputs/cnipa_submission/pdf/EXPORT_MANIFEST.txt`

## 5. 可选参数
- 自定义输出目录：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/export_cnipa_figures_pdf.ps1 -OutputDir "outputs/cnipa_submission/pdf_custom"
```

- 自定义 Edge 路径：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/export_cnipa_figures_pdf.ps1 -EdgePath "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
```

## 6. 说明
- 本流程仅导出 PDF，不生成 TIFF。
- TIFF 建议在最终封版时由统一工具链（例如代理人端或专用图像工具）批量转换。
