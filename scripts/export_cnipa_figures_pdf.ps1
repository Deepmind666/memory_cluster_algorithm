param(
    [string]$OutputDir = "outputs/cnipa_submission/pdf",
    [string]$EdgePath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $EdgePath)) {
    Write-Error "Edge executable not found: $EdgePath"
    exit 1
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$OutputDir = (Resolve-Path $OutputDir).Path

$figures = @(
    "fig1_v2_system_architecture.svg",
    "fig2_v2_method_flow.svg",
    "fig3_v2_data_structure.svg",
    "fig4_v2_conflict_evidence_graph.svg",
    "fig5_v2_dual_channel_gate.svg",
    "fig6_v2_retrieval_backref.svg",
    "fig_abs_v2_abstract.svg"
)

$exported = @()

foreach ($file in $figures) {
    $src = Resolve-Path (Join-Path "docs/patent_kit/figures" $file)
    $url = "file:///" + ($src.Path -replace "\\", "/")
    $pdf = Join-Path $OutputDir (($file -replace "\.svg$", "") + ".pdf")
    if (Test-Path $pdf) {
        Remove-Item $pdf -Force
    }

    & $EdgePath --headless --disable-gpu --print-to-pdf="$pdf" --no-pdf-header-footer $url *> $null

    $deadline = (Get-Date).AddSeconds(30)
    while ((-not (Test-Path $pdf)) -and ((Get-Date) -lt $deadline)) {
        Start-Sleep -Milliseconds 300
    }

    if (-not (Test-Path $pdf)) {
        Write-Error "Failed to export: $file"
        exit 2
    }

    $exported += $pdf
}

$manifest = Join-Path $OutputDir "EXPORT_MANIFEST.txt"

"CNIPA Figure PDF Export Manifest`nGenerated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')`n" |
    Set-Content -Path $manifest -Encoding UTF8

Get-ChildItem $OutputDir -Filter "*.pdf" | Sort-Object Name | ForEach-Object {
    "{0}`t{1}" -f $_.Name, $_.Length
} | Add-Content -Path $manifest -Encoding UTF8

Write-Output "Export completed."
Write-Output "Output directory: $OutputDir"
Write-Output "Manifest: $manifest"
