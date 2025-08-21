# === CONFIGURATION ===
$TemplatePath = "C:\Letter Template.msg"
$ExcelPath = "C:\report.xlsx"
$AttachmentFolder = "C:\letters"
$MissingEmailLog = "C:\missing_emails.txt"
$MissingLedgerLog = "C:\missing_ledger.txt"

# === SETUP OUTLOOK ===
$Outlook = New-Object -ComObject Outlook.Application
$Namespace = $Outlook.GetNamespace("MAPI")

# === RESET LOG FILES ===
Set-Content $MissingEmailLog -Value $null
Set-Content $MissingLedgerLog -Value $null

# === OPEN EXCEL ===
$Excel = New-Object -ComObject Excel.Application
$Excel.Visible = $false
$Workbook = $Excel.Workbooks.Open($ExcelPath)
$Sheet = $Workbook.Sheets.Item(1)

# === HEADER MAPPING ===
$row = 2
while ($Sheet.Cells.Item($row, 1).Text -ne "") {
    $ClientName = $Sheet.Cells.Item($row, 1).Text.Trim()
    $ClientEmail = $Sheet.Cells.Item($row, 5).Text.Trim()

    # === Check and log missing email ===
    if ([string]::IsNullOrWhiteSpace($ClientEmail)) {
        $Address = $Sheet.Cells.Item($row, 3).Text.Trim()
        $Phone = $Sheet.Cells.Item($row, 4).Text.Trim()

        $LogEntry = @"
Client Name: $ClientName
Email: 
Address: $Address
Phone: $Phone

"@
        Add-Content -Path $MissingEmailLog -Value $LogEntry

        Write-Host "Skipped $ClientName (no email)"
        $row++
        continue
    }

    # === Check and log missing PDF ===
    $AttachmentPath = Join-Path $AttachmentFolder "$ClientName.pdf"
    if (-not (Test-Path $AttachmentPath)) {
        Write-Host "Skipped $ClientName — Missing ledger ($AttachmentPath)"
        Add-Content -Path $MissingLedgerLog -Value $ClientName
        $row++
        continue
    }

    # === Check if a draft already exists for this client ===
    $DraftsFolder = $Namespace.GetDefaultFolder(16)  # 16 = olFolderDrafts
    $AlreadyExists = $false

    foreach ($item in $DraftsFolder.Items) {
        if ($item.MessageClass -eq "IPM.Note" -and $item.To -eq $ClientEmail) {
            foreach ($att in $item.Attachments) {
                if ($att.FileName -eq "$ClientName.pdf") {
                    $AlreadyExists = $true
                    break
                }
            }
        }
        if ($AlreadyExists) { break }
    }

    if ($AlreadyExists) {
        Write-Host "Skipped $ClientName — Draft already exists"
        $row++
        continue
    }

    # === Create draft only when both email and PDF are present ===
    try {
        $Mail = $Outlook.CreateItemFromTemplate($TemplatePath)
        $Mail.To = $ClientEmail
        $Mail.Attachments.Add($AttachmentPath) | Out-Null
        $Mail.Save()
        Write-Host "Draft created for $ClientName <$ClientEmail>"
    } catch {
        Write-Host "Error creating draft for ${ClientName}: $_"
    }

    $row++
}

# === CLEAN UP ===
$Workbook.Close($false)
$Excel.Quit()
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($Excel) | Out-Null
Remove-Variable Excel, Workbook, Sheet, Namespace, Outlook
[GC]::Collect()
[GC]::WaitForPendingFinalizers()

Write-Host "`nScript complete. Check Drafts folder, $MissingEmailLog and $MissingLedgerLog for issues."
