$source = "Y:\"
$destinations = @("H:\", "I:\", "J:\")
$thresholdGB = 500
$thresholdBytes = $thresholdGB * 1GB

# Get all source files
$files = Get-ChildItem $source -Recurse -File

foreach ($file in $files) {
    $relative = $file.FullName.Substring($source.Length).TrimStart("\")
    $alreadyCopied = $false

    # Check all destinations to see if this file already exists
    foreach ($dest in $destinations) {
        $targetPath = Join-Path $dest $relative
        if (Test-Path $targetPath) {
            $targetInfo = Get-Item $targetPath
            if ($targetInfo.Length -eq $file.Length) {
                $alreadyCopied = $true
                break
            }
        }
    }

    if ($alreadyCopied) { continue }

    # If not already copied, find the first destination with enough free space
    $copied = $false
    foreach ($dest in $destinations) {
        $drive = Get-PSDrive -Name ($dest.Substring(0,1))
        if ($drive.Free -lt $thresholdBytes) { continue }

        $targetPath = Join-Path $dest $relative
        $targetDir = Split-Path $targetPath -Parent

        if (-not (Test-Path $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }

        Copy-Item $file.FullName $targetPath -Force
        Write-Host "Copied: $($file.FullName) --> $targetPath"
        $copied = $true
        break
    }

    if (-not $copied) {
        Write-Warning "All destinations full. Skipped: $($file.FullName)"
    }
}
