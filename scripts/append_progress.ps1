[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Low')]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Stage,

    [string[]]$Actions = @(),
    [string[]]$FilesReviewed = @(),
    [string[]]$FilesChanged = @(),
    [string[]]$ReviewChecklist = @(),

    [ValidateNotNullOrEmpty()]
    [string]$LogFile = "WORK_PROGRESS.md"
)

function New-LogHeader {
    param([string]$Path)

    @"
# Work Progress Log

> Purpose: Record every meaningful progress update with timestamp, work details, and review checklist.
"@ | Set-Content -Encoding UTF8 $Path
}

function ConvertTo-NormalizedList {
    param([string[]]$Items)

    $normalized = New-Object System.Collections.Generic.List[string]
    foreach ($item in $Items) {
        if ([string]::IsNullOrWhiteSpace($item)) {
            continue
        }

        if ($item.Contains(',')) {
            foreach ($part in $item.Split(',')) {
                $trimmed = $part.Trim()
                if (-not [string]::IsNullOrWhiteSpace($trimmed)) {
                    $normalized.Add($trimmed)
                }
            }
        }
        else {
            $normalized.Add($item.Trim())
        }
    }

    return $normalized
}

function ConvertTo-ChecklistLine {
    param([string]$Item)

    $value = if ($null -eq $Item) { '' } else { $Item }
    $trimmed = $value.Trim()
    if ([string]::IsNullOrWhiteSpace($trimmed)) {
        return "  - [ ] (empty)"
    }

    if ($trimmed -match '^\[(x|X| )\]\s+') {
        return "  - $trimmed"
    }

    return "  - [x] $trimmed"
}

$logPath = [System.IO.Path]::GetFullPath($LogFile)
$parent = Split-Path -Parent $logPath
if ($parent -and -not (Test-Path $parent)) {
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
}

if (-not (Test-Path $logPath)) {
    if ($PSCmdlet.ShouldProcess($logPath, "Create progress log header")) {
        New-LogHeader -Path $logPath
    }
}

$Actions = ConvertTo-NormalizedList -Items $Actions
$FilesReviewed = ConvertTo-NormalizedList -Items $FilesReviewed
$FilesChanged = ConvertTo-NormalizedList -Items $FilesChanged
$ReviewChecklist = ConvertTo-NormalizedList -Items $ReviewChecklist

$raw = ""
if (Test-Path $logPath) {
    $raw = Get-Content -Raw -Encoding UTF8 $logPath
}

$entryCount = ([regex]::Matches($raw, '^## Entry\s+\d+', 'Multiline')).Count
$nextEntry = $entryCount + 1
$entryId = $nextEntry.ToString('000')
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss K"

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("")
$lines.Add("## Entry $entryId")
$lines.Add("- Timestamp: $timestamp")
$lines.Add("- Stage: $Stage")
$lines.Add("- Actions:")

if ($Actions.Count -eq 0) {
    $lines.Add("  - (none)")
}
else {
    foreach ($item in $Actions) {
        $lines.Add("  - $item")
    }
}

$lines.Add("- Files Reviewed:")
if ($FilesReviewed.Count -eq 0) {
    $lines.Add("  - (none)")
}
else {
    foreach ($item in $FilesReviewed) {
        $lines.Add('  - `' + $item + '`')
    }
}

$lines.Add("- Files Changed:")
if ($FilesChanged.Count -eq 0) {
    $lines.Add("  - (none)")
}
else {
    foreach ($item in $FilesChanged) {
        $lines.Add('  - `' + $item + '`')
    }
}

$lines.Add("- Review Checklist:")
if ($ReviewChecklist.Count -eq 0) {
    $lines.Add("  - [ ] (not provided)")
}
else {
    foreach ($item in $ReviewChecklist) {
        $lines.Add((ConvertTo-ChecklistLine -Item $item))
    }
}

if ($PSCmdlet.ShouldProcess($logPath, "Append progress entry $entryId")) {
    Add-Content -Encoding UTF8 -Path $logPath -Value ($lines -join [Environment]::NewLine)
    Write-Output "Appended Entry $entryId to $logPath"
}
