# Shift-EpisodeNumber.ps1
# Shifts episode numbers in filenames by a configurable amount
# Supports single and multi-episode formats (e.g., S01E13E14)

# CONFIG: Set to 1 to increment, -1 to decrement
$shift = -1

# Prompt for folder
Add-Type -AssemblyName Microsoft.VisualBasic
$folderPath = [Microsoft.VisualBasic.Interaction]::InputBox("Enter full path to folder:", "Select Folder", "K:\TV Shows\Example")

if (-not (Test-Path $folderPath)) {
    Write-Host "Invalid path. Exiting."
    exit
}

# Process each file
Get-ChildItem -Path $folderPath -File | ForEach-Object {
    $file = $_.Name

    # Match SxxExx or SxxExxx, optionally followed by Eyy or Eyyy (multi-episode)
    if ($file -match '(S\d{2}E)(\d{2,3})(E(\d{2,3}))?') {
        $seasonPart = $matches[1]
        $ep1 = [int]$matches[2]
        $ep1Length = $matches[2].Length

        $ep1New = $ep1 + $shift
        if ($ep1New -lt 0) {
            Write-Host "Skipping $file - episode number would go below zero"
            return
        }

        $ep1NewStr = $ep1New.ToString("D$ep1Length")
        $newTag = "$seasonPart$ep1NewStr"

        # If second episode (multi-episode like S01E13E14)
        if ($matches[3]) {
            $ep2 = [int]$matches[4]
            $ep2Length = $matches[4].Length

            $ep2New = $ep2 + $shift
            if ($ep2New -lt 0) {
                Write-Host "Skipping $file - second episode would go below zero"
                return
            }

            $ep2NewStr = $ep2New.ToString("D$ep2Length")
            $newTag += "E$ep2NewStr"
        }

        # Replace the original episode tag with the new one
        $newFile = $file -replace "$seasonPart\d{2,3}(E\d{2,3})?", $newTag

        $oldPath = Join-Path $folderPath $file
        Rename-Item -LiteralPath $oldPath -NewName $newFile
        Write-Host "Renamed: $file → $newFile"
    }
}
