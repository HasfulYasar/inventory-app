Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$serviceName = "ShowCashApp"
$appUrl = "http://ec2-3-107-71-158.ap-southeast-2.compute.amazonaws.com:8080"

$form = New-Object System.Windows.Forms.Form
$form.Text = "ShowCash Server Control"
$form.Size = New-Object System.Drawing.Size(360, 420)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false

$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Location = New-Object System.Drawing.Point(20, 20)
$statusLabel.Size = New-Object System.Drawing.Size(300, 30)
$statusLabel.Font = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($statusLabel)

$detailsBox = New-Object System.Windows.Forms.TextBox
$detailsBox.Location = New-Object System.Drawing.Point(20, 60)
$detailsBox.Size = New-Object System.Drawing.Size(300, 130)
$detailsBox.Multiline = $true
$detailsBox.ReadOnly = $true
$detailsBox.Font = New-Object System.Drawing.Font("Consolas", 9)
$detailsBox.BackColor = [System.Drawing.Color]::WhiteSmoke
$form.Controls.Add($detailsBox)

function Update-Status {
    $lines = @()
    try {
        $svc = Get-Service -Name $serviceName -ErrorAction Stop
        $statusLabel.Text = "Status: $($svc.Status)"
        if ($svc.Status -eq "Running") {
            $statusLabel.ForeColor = [System.Drawing.Color]::Green
        } else {
            $statusLabel.ForeColor = [System.Drawing.Color]::Red
        }
        $lines += "Service: $serviceName"
        $lines += "Startup type: $($svc.StartType)"
    } catch {
        $statusLabel.Text = "Status: Not found"
        $statusLabel.ForeColor = [System.Drawing.Color]::Gray
        $lines += "Service not found."
    }

    $portCheck = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
    if ($portCheck) {
        $procId = $portCheck[0].OwningProcess
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        $lines += "Port 8080: LISTENING"
        $lines += "Process ID: $procId"
        if ($proc) {
            $memMB = [math]::Round($proc.WorkingSet64 / 1MB, 1)
            $lines += "Memory: $memMB MB"
        }
    } else {
        $lines += "Port 8080: NOT listening"
    }

    $lines += "URL: $appUrl"
    $detailsBox.Text = ($lines -join "`r`n")
}

$startBtn = New-Object System.Windows.Forms.Button
$startBtn.Text = "Start Server"
$startBtn.Location = New-Object System.Drawing.Point(20, 200)
$startBtn.Size = New-Object System.Drawing.Size(300, 40)
$startBtn.BackColor = [System.Drawing.Color]::LightGreen
$startBtn.Add_Click({
    Start-Service -Name $serviceName -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Update-Status
})
$form.Controls.Add($startBtn)

$stopBtn = New-Object System.Windows.Forms.Button
$stopBtn.Text = "Stop Server"
$stopBtn.Location = New-Object System.Drawing.Point(20, 250)
$stopBtn.Size = New-Object System.Drawing.Size(300, 40)
$stopBtn.BackColor = [System.Drawing.Color]::LightCoral
$stopBtn.Add_Click({
    Stop-Service -Name $serviceName -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Update-Status
})
$form.Controls.Add($stopBtn)

$restartBtn = New-Object System.Windows.Forms.Button
$restartBtn.Text = "Restart Server"
$restartBtn.Location = New-Object System.Drawing.Point(20, 300)
$restartBtn.Size = New-Object System.Drawing.Size(300, 40)
$restartBtn.BackColor = [System.Drawing.Color]::LightYellow
$restartBtn.Add_Click({
    Restart-Service -Name $serviceName -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Update-Status
})
$form.Controls.Add($restartBtn)

$refreshBtn = New-Object System.Windows.Forms.Button
$refreshBtn.Text = "Refresh Status"
$refreshBtn.Location = New-Object System.Drawing.Point(20, 350)
$refreshBtn.Size = New-Object System.Drawing.Size(300, 30)
$refreshBtn.Add_Click({ Update-Status })
$form.Controls.Add($refreshBtn)

Update-Status
[System.Windows.Forms.Application]::Run($form)
