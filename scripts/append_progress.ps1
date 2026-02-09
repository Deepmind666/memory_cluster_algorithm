param(
    [Parameter(Mandatory = $true)]
    [string]$Stage,

    [string[]]$Actions = @(),
    [string[]]$FilesReviewed = @(),
    [string[]]$FilesChanged = @(),
    [string[]]$ReviewChecklist = @(),
    [string]$LogFile = "WORK_PROGRESS.md"
)

function New-LogHeader {
    param([string]$Path)

    @"
# Work Progress Log

> Purpose: Record every meaningful progress update with timestamp, work details, and review checklist.
"@ | Set-Content -Encoding UTF8 $Path
}

function Normalize-List {
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
        } else {
            $normalized.Add($item.Trim())
        }
    }

    return $normalized
}

if (-not (Test-Path $LogFile)) {
    New-LogHeader -Path $LogFile
}

$Actions = Normalize-List -Items $Actions
$FilesReviewed = Normalize-List -Items $FilesReviewed
$FilesChanged = Normalize-List -Items $FilesChanged
$ReviewChecklist = Normalize-List -Items $ReviewChecklist

$raw = Get-Content -Raw -Encoding UTF8 $LogFile
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
} else {
    foreach ($item in $Actions) {
        $lines.Add("  - $item")
    }
}

$lines.Add("- Files Reviewed:")
if ($FilesReviewed.Count -eq 0) {
    $lines.Add("  - (none)")
} else {
    foreach ($item in $FilesReviewed) {
        $lines.Add('  - `' + $item + '`')
    }
}

$lines.Add("- Files Changed:")
if ($FilesChanged.Count -eq 0) {
    $lines.Add("  - (none)")
} else {
    foreach ($item in $FilesChanged) {
        $lines.Add('  - `' + $item + '`')
    }
}

$lines.Add("- Review Checklist:")
if ($ReviewChecklist.Count -eq 0) {
    $lines.Add("  - [ ] (not provided)")
} else {
    foreach ($item in $ReviewChecklist) {
        $lines.Add("  - [x] $item")
    }
}

Add-Content -Encoding UTF8 -Path $LogFile -Value ($lines -join [Environment]::NewLine)
Write-Output "Appended Entry $entryId to $LogFile"
