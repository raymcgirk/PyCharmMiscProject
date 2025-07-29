# === SETUP OUTLOOK ===
$Outlook = New-Object -ComObject Outlook.Application
$Namespace = $Outlook.GetNamespace("MAPI")
$DraftsFolder = $Namespace.GetDefaultFolder([Microsoft.Office.Interop.Outlook.OlDefaultFolders]::olFolderDrafts)

# === MAKE STATIC COPY OF DRAFTS ===
$Drafts = @()
foreach ($item in $DraftsFolder.Items) {
    if ($item -is [Microsoft.Office.Interop.Outlook.MailItem]) {
        $Drafts += $item
    }
}

# === SEND EACH DRAFT WITH DELAY ===
foreach ($Mail in $Drafts) {
    try {
        Write-Host "📤 Sending: $($Mail.Subject)"
        $Mail.Send()
        Start-Sleep -Seconds 5
    } catch {
        Write-Host "⚠️ Failed to send: $($Mail.Subject) — $_"
    }
}

Write-Host "`n✅ All drafts processed."
