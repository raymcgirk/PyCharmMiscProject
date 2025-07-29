# Create Outlook COM object
$Outlook = New-Object -ComObject Outlook.Application
$Namespace = $Outlook.GetNamespace("MAPI")
$Drafts = $Namespace.GetDefaultFolder(16)  # 16 = olFolderDrafts

# Track duplicates
$Seen = @{}
$Duplicates = @()

foreach ($item in $Drafts.Items) {
    if ($item.MessageClass -eq "IPM.Note") {
        $key = "$($item.To)-$($item.Subject)"

        # Optional: include first attachment name
        # if ($item.Attachments.Count -gt 0) {
        #     $key += "-$($item.Attachments.Item(1).FileName)"
        # }

        if ($Seen.ContainsKey($key)) {
            $Duplicates += $item
        } else {
            $Seen[$key] = $true
        }
    }
}

if ($Duplicates.Count -eq 0) {
    Write-Host "✅ No duplicate drafts found."
} else {
    Write-Host "⚠️ Found $($Duplicates.Count) duplicate draft(s):"
    foreach ($dup in $Duplicates) {
        Write-Host "→ To: $($dup.To) | Subject: $($dup.Subject)"
    }

    # To delete them, uncomment:
    # foreach ($dup in $Duplicates) { $dup.Delete() }
}
